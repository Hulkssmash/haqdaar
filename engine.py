"""Rule-based eligibility engine. Standard library only.

Eligibility is decided here with plain rules, NOT by the LLM. The LLM (if used)
only explains results in simple language.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

STATUS_ORDER = {"likely": 0, "likely_needs_assessment": 1, "need_more_info": 2, "not_eligible": 3}
STATUS_LABELS = {
    "likely": "Likely eligible / غالباً اہل",
    "likely_needs_assessment": "Passes the basic checks; the official office decides / بنیادی شرائط پوری، حتمی فیصلہ سرکاری ادارے کا",
    "need_more_info": "Need more information / مزید معلومات درکار",
    "not_eligible": "Does not seem to match / شرائط پوری نہیں ہوتیں",
}


def load_rules(path=None):
    p = Path(path) if path else DATA_DIR / "rules.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _check(cond, profile):
    """Return 'met', 'failed' or 'unknown' for one condition."""
    field, op, expected = cond["field"], cond["op"], cond["value"]
    val = profile.get(field)
    if val in (None, "", "unknown"):
        return "unknown"
    try:
        if op == "eq":
            ok = str(val).lower() == str(expected).lower()
        elif op == "in":
            ok = str(val).lower() in [str(x).lower() for x in expected]
        elif op == "between":
            ok = float(expected[0]) <= float(val) <= float(expected[1])
        elif op == "gte":
            ok = float(val) >= float(expected)
        elif op == "lte":
            ok = float(val) <= float(expected)
        else:
            return "unknown"
    except (TypeError, ValueError):
        return "unknown"
    return "met" if ok else "failed"


def evaluate(profile, rules=None):
    """Evaluate a profile dict against all schemes. Returns a list of result dicts."""
    rules = rules or load_rules()
    results = []
    for s in rules["schemes"]:
        met, failed, unknown = [], [], []
        for cond in s.get("conditions", []):
            outcome = _check(cond, profile)
            {"met": met, "failed": failed, "unknown": unknown}[outcome].append(cond["note"])
        if failed:
            status = "not_eligible"
        elif unknown:
            status = "need_more_info"
        elif s.get("official_assessment_required"):
            status = "likely_needs_assessment"
        else:
            status = "likely"
        results.append({
            "id": s["id"],
            "name": s["name"],
            "name_ur": s.get("name_ur", ""),
            "status": status,
            "status_label": STATUS_LABELS[status],
            "met": met,
            "failed": failed,
            "unknown": unknown,
            "documents": s.get("documents", []),
            "steps": s.get("steps", []),
            "official_url": s.get("official_url", ""),
            "apply_url": s.get("apply_url", ""),
            "helpline": s.get("helpline", ""),
            "other_criteria": s.get("other_official_criteria", []),
            "verified": bool(s.get("verified", False)),
            "checked_on": s.get("checked_on"),
        })
    results.sort(key=lambda r: STATUS_ORDER[r["status"]])
    return results
