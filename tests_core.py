"""Plain-Python tests for the dependency-free core. Run: python tests_core.py"""
import engine
import linkcheck
import sources

RULES = engine.load_rules()


def status(profile, scheme_id):
    return next(r for r in engine.evaluate(profile, RULES) if r["id"] == scheme_id)["status"]


# --- eligibility engine
A = "apni_chhat_apna_ghar"
assert status({"province": "punjab", "age": 30}, A) == "likely_needs_assessment"
assert status({"province": "punjab", "age": 20}, A) == "not_eligible"
assert status({"province": "punjab", "age": 61}, A) == "not_eligible"
assert status({"province": "sindh", "age": 30}, A) == "not_eligible"
assert status({"province": "punjab"}, A) == "need_more_info"
assert status({}, "apni_chhat_mehfooz_chhat") == "need_more_info"
assert all(r["other_criteria"] for r in engine.evaluate({"province": "punjab", "age": 30}, RULES))

# --- link check
dom = {"domains": ["punjab.gov.pk"]}
assert linkcheck.check_link("https://pser.punjab.gov.pk/login", dom)["result"] == "official"
assert linkcheck.check_link("punjab.gov.pk", dom)["result"] == "official"
assert linkcheck.check_link("https://punjab.gov.pk.evil.com", dom)["result"] == "not_listed"
assert linkcheck.check_link("https://evilpunjab.gov.pk", dom)["result"] == "not_listed"
assert linkcheck.check_link("https://pser.punjab.gov.pk@evil.com/x", dom)["result"] == "not_listed"
assert linkcheck.check_link("http://pser.punjab.gov.pk", dom)["result"] == "official"
assert "http" in linkcheck.check_link("http://pser.punjab.gov.pk", dom)["message"]
assert linkcheck.check_link("", dom)["result"] == "invalid"
assert linkcheck.check_link("hello", dom)["result"] == "invalid"

# --- source loading and chunking
items = sources.load_all()
assert items and all(i["source_url"] and i["scheme_id"] for i in items)
long_text = "\n\n".join(["para " + "x" * 300] * 5)
chunks = sources.chunk_text(long_text, max_chars=700)
assert all(len(c) <= 700 for c in chunks) and len(chunks) >= 2

print("All core tests passed.")
