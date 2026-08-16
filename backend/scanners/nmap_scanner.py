import asyncio
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from scanners.base import FindingData, ScannerResult


async def run(target_url: str, config: dict | None = None) -> ScannerResult:
    host = urlparse(target_url).hostname or target_url
    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            "nmap", "-sV", "-T4", "--host-timeout", "90s", "-oX", "-", "--open", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except FileNotFoundError:
        return ScannerResult(error="nmap not installed")
    except asyncio.TimeoutError:
        return ScannerResult(error="nmap timed out after 300s")

    duration = time.monotonic() - start
    raw = stdout.decode()

    if proc.returncode != 0:
        return ScannerResult(raw_output=stderr.decode(), duration_seconds=duration,
                             error=f"nmap exited {proc.returncode}")

    findings = _parse_xml(raw)
    return ScannerResult(findings=findings, raw_output=raw, duration_seconds=duration)


def _parse_xml(xml_output: str) -> list[FindingData]:
    findings: list[FindingData] = []
    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError:
        return findings

    for host in root.findall("host"):
        addr_el = host.find("address")
        addr = addr_el.attrib.get("addr", "unknown") if addr_el is not None else "unknown"

        for port in host.findall(".//port"):
            portid = port.attrib.get("portid", "?")
            protocol = port.attrib.get("protocol", "tcp")
            state_el = port.find("state")
            if state_el is None or state_el.attrib.get("state") != "open":
                continue

            service_el = port.find("service")
            service = service_el.attrib.get("name", "unknown") if service_el is not None else "unknown"
            version = ""
            if service_el is not None:
                version = " ".join(filter(None, [
                    service_el.attrib.get("product"),
                    service_el.attrib.get("version"),
                ])).strip()

            findings.append(FindingData(
                category="network",
                severity="low",
                title=f"Open port {portid}/{protocol} — {service}",
                description=f"Host {addr} has {service} ({version or 'unknown version'}) "
                            f"listening on {portid}/{protocol}.",
                raw={"host": addr, "port": portid, "protocol": protocol,
                     "service": service, "version": version},
            ))

    return findings
