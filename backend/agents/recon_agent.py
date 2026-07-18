from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import dns.resolver
import httpx

from agents.state import AgentState, ProgressEvent, ReconData

_SUBDOMAIN_WORDLIST = [
    "www", "api", "dev", "staging", "admin", "mail", "smtp", "ftp",
    "vpn", "portal", "app", "beta", "test", "docs", "cdn", "static",
    "assets", "auth", "login", "dashboard", "internal", "corp",
]

_TECH_HEADERS = {
    "server": "Server",
    "x-powered-by": "X-Powered-By",
    "x-aspnet-version": "ASP.NET",
    "x-generator": "Generator",
    "x-drupal-cache": "Drupal",
    "x-wp-nonce": "WordPress",
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(node: str, status: str, message: str) -> ProgressEvent:
    return ProgressEvent(node=node, status=status, message=message, timestamp=_ts())


async def run(state: AgentState) -> AgentState:
    state["current_node"] = "recon"
    state["progress_events"].append(_event("recon", "started", "Recon agent starting"))

    if state.get("target_type") == "container":
        state["recon_data"] = ReconData()
        state["progress_events"].append(
            _event("recon", "completed", "Recon skipped — container scan")
        )
        return state

    target_url = state["target_url"]
    parsed = urlparse(target_url)
    domain = parsed.hostname or target_url

    recon = ReconData()

    # DNS records
    state["progress_events"].append(_event("recon", "started", f"DNS lookup for {domain}"))
    recon.dns_records = await _dns_lookup(domain)

    # Subdomain enum
    state["progress_events"].append(_event("recon", "started", "Subdomain enumeration"))
    recon.subdomains = await _enum_subdomains(domain)

    # HTTP headers + tech fingerprint
    state["progress_events"].append(_event("recon", "started", "HTTP fingerprinting"))
    headers, techs = await _fingerprint(target_url)
    recon.headers = headers
    recon.technologies = techs

    state["recon_data"] = recon
    state["progress_events"].append(
        _event("recon", "completed",
               f"Recon complete — {len(recon.subdomains)} subdomains, "
               f"{len(recon.technologies)} technologies detected")
    )
    return state


async def _dns_lookup(domain: str) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 5
    loop = asyncio.get_running_loop()

    async def _resolve(rtype: str) -> None:
        try:
            answers = await loop.run_in_executor(None, lambda: resolver.resolve(domain, rtype))
            records[rtype] = [str(r) for r in answers]
        except Exception:
            pass

    await asyncio.gather(*[_resolve(rt) for rt in ("A", "MX", "TXT", "CNAME", "NS")])
    return records


async def _enum_subdomains(domain: str) -> list[str]:
    found: list[str] = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 3

    async def check(sub: str) -> None:
        fqdn = f"{sub}.{domain}"
        try:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: resolver.resolve(fqdn, "A")
            )
            found.append(fqdn)
        except Exception:
            pass

    await asyncio.gather(*[check(s) for s in _SUBDOMAIN_WORDLIST], return_exceptions=True)
    return found


async def _fingerprint(url: str) -> tuple[dict[str, str], list[str]]:
    headers_found: dict[str, str] = {}
    techs: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                     verify=False) as client:
            resp = await client.get(url)
            for h, label in _TECH_HEADERS.items():
                val = resp.headers.get(h)
                if val:
                    headers_found[h] = val
                    techs.append(f"{label}: {val}")

            body = resp.text[:4096]
            if "wp-content" in body or "wp-json" in body:
                techs.append("WordPress")
            if "Drupal" in body or "drupal.js" in body:
                techs.append("Drupal")
            if "__next" in body or "_next/static" in body:
                techs.append("Next.js")
            if "react" in body.lower() and "root" in body:
                techs.append("React")
            if "django" in body.lower() or "csrfmiddlewaretoken" in body:
                techs.append("Django")
    except Exception:
        pass

    return headers_found, list(set(techs))
