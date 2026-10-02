"""UI-independent helpers shared by the Streamlit app. No Gradio or Streamlit imports here."""
import json

import engine
import linkcheck
import rag
import storage
import texts

PROVINCES = [("Punjab / پنجاب", "punjab"), ("Sindh / سندھ", "sindh"), ("Khyber Pakhtunkhwa / خیبر پختونخوا", "kp"),
             ("Balochistan / بلوچستان", "balochistan"), ("Islamabad / اسلام آباد", "ict"), ("Other / دیگر", "other")]
OCCUPATIONS = [("— choose / منتخب کریں —", None),
               ("I own a business / میرا کاروبار ہے", "has_business"),
               ("I plan to start a business / کاروبار شروع کرنا چاہتا ہوں", "planning_business"),
               ("Farmer / کسان", "farmer"), ("Student / طالب علم", "student"),
               ("Employee / ملازم", "employee"), ("Unemployed / بے روزگار", "unemployed"),
               ("Other / دیگر", "other")]
INCOME_BANDS = [("Prefer not to say / بتانا نہیں چاہتا", "unknown"),
                ("Below Rs 25,000 / 25 ہزار سے کم", "below_25k"),
                ("Rs 25,000 to 50,000 / 25 سے 50 ہزار", "25k_50k"),
                ("Above Rs 50,000 / 50 ہزار سے زیادہ", "above_50k")]


def district_choices(province):
    """[(label, value)] with a blank first option."""
    try:
        data = json.load(open(engine.DATA_DIR / "districts.json", encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return [("— optional / اختیاری —", None)] + [(f"{en} / {ur}", en.lower()) for en, ur in data.get(province, [])]


def official_links(r):
    parts = []
    for label, key in (("🌐 Official website", "official_url"), ("📝 Apply on the official website", "apply_url")):
        url = r.get(key)
        if url and linkcheck.check_link(url)["result"] == "official":
            parts.append(f"[{label}]({url})")
    if r.get("helpline"):
        parts.append(f"📞 Helpline: {r['helpline']}")
    return " | ".join(parts) if parts else "Official link: please check the official government website."


def render_results(results):
    lines = []
    if any(not r["verified"] for r in results):
        lines.append("> ⚠️ **Draft rules:** these scheme rules have not yet been fully verified against the official pages.\n")
    for r in results:
        lines.append(f"### {r['name']}  \n**{r['name_ur']}**")
        lines.append(f"**{r['status_label']}**")
        if r["met"]:
            lines.append("- ✅ " + "\n- ✅ ".join(r["met"]))
        if r["failed"]:
            lines.append("- ❌ " + "\n- ❌ ".join(r["failed"]))
        if r["unknown"]:
            lines.append("- ❓ Need to know: " + "; ".join(r["unknown"]))
        if r["other_criteria"] and r["status"] != "not_eligible":
            lines.append("**You must also meet (the app cannot check these for you):**\n"
                         + "\n".join(f"- ☐ {c}" for c in r["other_criteria"]))
        if r["status"] in ("likely", "likely_needs_assessment", "need_more_info"):
            if r["documents"]:
                lines.append("**Documents:** " + ", ".join(r["documents"]))
            if r["steps"]:
                lines.append("**Steps:**\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(r["steps"], 1)))
        lines.append(official_links(r))
        lines.append(f"Rules checked on: {r['checked_on'] or 'not yet checked'}\n")
    lines.append(f"---\n{texts.DISCLAIMER_UR}\n\n{texts.DISCLAIMER_EN}")
    return "\n\n".join(lines)


def run_eligibility(profile):
    results = engine.evaluate(profile)
    storage.save("eligibility", {**profile, "results": {r["id"]: r["status"] for r in results}})
    return render_results(results)


def run_ask(question):
    if not question or not question.strip():
        return "Please type a question."
    res = rag.answer(question)
    storage.save("questions", {"question": question, "grounded": res["grounded"]})
    out = res["answer"]
    if res["sources"]:
        out += "\n\n**Sources:**\n" + "\n".join(
            f"- {s['url']} (checked on {s['checked_on'] or 'unknown date'})" for s in res["sources"])
    return out + f"\n\n---\n{texts.DISCLAIMER_UR}\n\n{texts.DISCLAIMER_EN}"


def run_link(url):
    r = linkcheck.check_link(url)
    storage.save("links", {"url": url, "result": r["result"]})
    icon = {"official": "✅", "not_listed": "⚠️", "invalid": "❓"}[r["result"]]
    return f"{icon} {r['message']}"
