"""Official-link check against an allowlist of government domains. Standard library only.

'Not on the list' does NOT prove a site is fake; it only means Haqdaar cannot confirm it.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(__file__).parent / "data"


def load_domains(path=None):
    p = Path(path) if path else DATA_DIR / "official_domains.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check_link(url, domains=None):
    cfg = domains if domains is not None else load_domains()
    allow = [d.lower() for d in cfg["domains"]]
    raw = (url or "").strip()
    if not raw:
        return {"result": "invalid", "host": "", "message": "Please paste a link."}
    candidate = raw if "://" in raw else "https://" + raw
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or "." not in host:
        return {"result": "invalid", "host": host, "message": "This does not look like a web address."}
    for d in allow:
        # exact match or a true subdomain; 'punjab.gov.pk.evil.com' does NOT match
        if host == d or host.endswith("." + d):
            msg = f"{host} is on the official domain list."
            if parsed.scheme == "http":
                msg += " Note: the link uses http, not https."
            return {"result": "official", "host": host, "message": msg}
    return {
        "result": "not_listed",
        "host": host,
        "message": (
            f"{host} is NOT on the official domain list. I cannot confirm it is official. "
            "Do not enter personal details or pay any fee; open the scheme from an official government page instead."
        ),
    }
