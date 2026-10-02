"""Haqdaar: FastAPI service (the core) with a Gradio demo mounted on top.

Run locally:   python app.py        -> UI at http://localhost:7860, API docs at /docs
"""
import json
import os

import gradio as gr
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

import engine
import linkcheck
import rag
import storage
import texts

api = FastAPI(title="Haqdaar API", description="Urdu-first government scheme guidance")


class Profile(BaseModel):
    province: str | None = None
    age: float | None = None
    occupation: str | None = None
    income_band: str | None = None
    family_size: int | None = None
    district: str | None = None


class AskRequest(BaseModel):
    question: str
    scheme_ids: list[str] | None = None


class LinkRequest(BaseModel):
    url: str


@api.post("/eligibility")
def eligibility(profile: Profile):
    return {"results": engine.evaluate(profile.model_dump()), "disclaimer": texts.DISCLAIMER_EN}


@api.post("/ask")
def ask(req: AskRequest):
    res = rag.answer(req.question, req.scheme_ids)
    res["disclaimer"] = texts.DISCLAIMER_EN
    return res


@api.post("/check-link")
def check(req: LinkRequest):
    return linkcheck.check_link(req.url)


@api.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    import tempfile
    import voice
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        text = voice.transcribe(tmp.name)  # audio is deleted right after transcription
    return {"text": text}


# ---------------------------------------------------------------- UI helpers
PROVINCES = [("Punjab / پنجاب", "punjab"), ("Sindh / سندھ", "sindh"), ("Khyber Pakhtunkhwa / خیبر پختونخوا", "kp"),
             ("Balochistan / بلوچستان", "balochistan"), ("Islamabad / اسلام آباد", "ict"), ("Other / دیگر", "other")]
OCCUPATIONS = [("I own a business / میرا کاروبار ہے", "has_business"),
               ("I plan to start a business / کاروبار شروع کرنا چاہتا ہوں", "planning_business"),
               ("Farmer / کسان", "farmer"), ("Student / طالب علم", "student"),
               ("Employee / ملازم", "employee"), ("Unemployed / بے روزگار", "unemployed"),
               ("Other / دیگر", "other")]
INCOME_BANDS = [("Below Rs 25,000 / 25 ہزار سے کم", "below_25k"), ("Rs 25,000 to 50,000 / 25 سے 50 ہزار", "25k_50k"),
                ("Above Rs 50,000 / 50 ہزار سے زیادہ", "above_50k"), ("Prefer not to say / بتانا نہیں چاہتا", "unknown")]


def _district_choices(province):
    """(label, value) pairs for the district dropdown. Empty if the province is not listed yet."""
    try:
        data = json.load(open(engine.DATA_DIR / "districts.json", encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [(f"{en} / {ur}", en.lower()) for en, ur in data.get(province, [])]


def _update_districts(province):
    return gr.Dropdown(choices=_district_choices(province), value=None)


def _official_links(r):
    """Show only links whose domain is on the official allowlist."""
    parts = []
    for label, key in (("🌐 Official website", "official_url"), ("📝 Apply on the official website", "apply_url")):
        url = r.get(key)
        if url and linkcheck.check_link(url)["result"] == "official":
            parts.append(f"[{label}]({url})")
    if r.get("helpline"):
        parts.append(f"📞 Helpline: {r['helpline']}")
    return " | ".join(parts) if parts else "Official link: please check the official government website."


def _render_results(results, rules_meta):
    lines = []
    if any(not r["verified"] for r in results):
        lines.append("> ⚠️ **Draft rules:** these scheme rules have not yet been verified against the official pages.\n")
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
        checked = r["checked_on"] or "not yet checked"
        lines.append(_official_links(r))
        lines.append(f"Rules checked on: {checked}\n")
    lines.append(f"---\n{texts.DISCLAIMER_UR}\n\n{texts.DISCLAIMER_EN}")
    return "\n\n".join(lines)


def ui_eligibility(province, age, occupation, income_band, family_size, district):
    profile = {"province": province, "age": age, "occupation": occupation,
               "income_band": income_band, "family_size": family_size, "district": district}
    rules = engine.load_rules()
    results = engine.evaluate(profile, rules)
    storage.save("eligibility", {**profile, "results": {r["id"]: r["status"] for r in results}})
    return _render_results(results, rules)


def ui_ask(question):
    if not question or not question.strip():
        return "Please type or speak a question."
    res = rag.answer(question)
    storage.save("questions", {"question": question, "grounded": res["grounded"]})
    out = res["answer"]
    if res["sources"]:
        out += "\n\n**Sources:**\n" + "\n".join(
            f"- {s['url']} (checked on {s['checked_on'] or 'unknown date'})" for s in res["sources"])
    return out + f"\n\n---\n{texts.DISCLAIMER_UR}\n\n{texts.DISCLAIMER_EN}"


def ui_transcribe(audio_path):
    try:
        import voice
        return voice.transcribe(audio_path)
    except Exception as e:  # keep the app usable if speech recognition is not available
        return f"(Speech recognition is not available right now: {type(e).__name__}. Please type your question.)"


def ui_link(url):
    r = linkcheck.check_link(url)
    storage.save("links", {"url": url, "result": r["result"]})
    icon = {"official": "✅", "not_listed": "⚠️", "invalid": "❓"}[r["result"]]
    return f"{icon} {r['message']}"


def build_ui():
    with gr.Blocks(title="Haqdaar - حقدار") as demo:
        gr.Markdown("# Haqdaar — حقدار\nFind out which government schemes you may qualify for. "
                    "کون سی سرکاری اسکیمیں آپ کے لیے ہو سکتی ہیں۔\n\n"
                    "*No login needed. Do not enter your CNIC number here. "
                    "Your answers are saved anonymously to improve the tool. / آپ کے جوابات بغیر نام کے محفوظ کیے جاتے ہیں۔*")
        with gr.Tab("Check my eligibility / اہلیت چیک کریں"):
            province = gr.Dropdown(PROVINCES, value="punjab", label="Province / صوبہ")
            age = gr.Number(label="Age / عمر", value=None, precision=0)
            occupation = gr.Dropdown(OCCUPATIONS, label="What do you do? / آپ کیا کرتے ہیں؟")
            income = gr.Dropdown(INCOME_BANDS, value="unknown", label="Monthly household income / ماہانہ آمدنی")
            family = gr.Number(label="Family size / خاندان کے افراد", value=None, precision=0)
            district = gr.Dropdown(_district_choices("punjab"), value=None, label="District / ضلع (optional)")
            province.change(_update_districts, province, district, api_name=False)
            out1 = gr.Markdown()
            gr.Button("Check / چیک کریں", variant="primary").click(
                ui_eligibility, [province, age, occupation, income, family, district], out1, api_name=False)
        with gr.Tab("Ask a question / سوال پوچھیں"):
            mic = gr.Audio(sources=["microphone"], type="filepath", label="Speak in Urdu (optional) / اردو میں بولیں")
            heard = gr.Textbox(label="Your question (check that it is correct) / آپ کا سوال")
            gr.Button("Write what I said / میری بات لکھیں").click(ui_transcribe, mic, heard, api_name=False)
            out2 = gr.Markdown()
            gr.Button("Ask / پوچھیں", variant="primary").click(ui_ask, heard, out2, api_name=False)
        with gr.Tab("Is this link official? / کیا یہ لنک سرکاری ہے؟"):
            url = gr.Textbox(label="Paste a link / لنک یہاں ڈالیں")
            out3 = gr.Markdown()
            gr.Button("Check link / لنک چیک کریں", variant="primary").click(ui_link, url, out3, api_name=False)
    return demo


app = gr.mount_gradio_app(api, build_ui(), path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
