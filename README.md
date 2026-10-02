# Haqdaar

An Urdu-first assistant that helps people find which government schemes they likely qualify for, which documents they need, and how to apply. It works by text or by voice, so people who cannot read well can use it too. Every answer is grounded in official sources and links back to them.

> **Disclaimer:** Haqdaar gives general guidance only and does not submit applications. Scheme rules change. Always confirm eligibility and steps on the official website or at the relevant office before applying.

## Problem

Government support only helps people who can find and understand it. Scheme rules are spread across official pages and PDFs, often hard to read, and many unofficial websites repeat outdated or conflicting details. About 37% of people aged 10 and over in Pakistan cannot read and write (63% literacy, Economic Survey 2025-26), so text-only help leaves many people out. Haqdaar gives one clear answer, in simple Urdu, by text or voice, backed by an official source.

## What it does

1. **Eligibility guidance.** The user answers a few short questions (district, income band, family size, occupation). A rule-based filter shortlists schemes, then a retriever pulls the matching passages from official documents. A local open-source LLM explains the result in simple Urdu using only that text.
2. **Voice in and out.** The user can speak the answers and listen to the result. The app repeats back what it heard and asks the user to confirm before using it.
3. **Official link check.** The user can ask whether a website or link about a scheme is official. It is checked against a list of official government domains.
4. **No guessing.** If no source supports an answer, the app says so and points to the official office instead.

See `haqdaar_architecture.mmd` for the architecture diagram.

## API first

The core is a FastAPI service, and the Gradio page is just one client of it:

- `POST /eligibility` - profile in, shortlisted schemes out
- `POST /ask` - question in, grounded answer with sources out
- `POST /transcribe` - Urdu audio in, text out
- `POST /speak` - text in, Urdu audio out
- `POST /check-link` - URL in, official or not listed out

The same engine could later power a WhatsApp bot, NGO tools, or help desks.

## Tech stack (all open source)

- LLM: Qwen2.5 (small quantized model) via Ollama or llama.cpp
- Speech to text: Whisper (small or fine-tuned Urdu variant)
- Text to speech: an open-source Urdu voice (to be tested for quality)
- Embeddings: multilingual-e5
- Vector store: Chroma
- API: FastAPI; UI: Gradio
- Hosting: Hugging Face Spaces

## Project structure

```
app.py              # FastAPI endpoints (the core) with the Gradio demo mounted on top
engine.py           # rule-based eligibility engine
linkcheck.py        # official-link check against the domain allowlist
sources.py          # loads and chunks official source texts
rag.py              # embeddings, Chroma retrieval, grounded answers (optional LLM)
voice.py            # optional Urdu speech to text (Whisper)
texts.py            # disclaimers and not-found messages (Urdu and English)
data/
  rules.json            # eligibility rules, verified by hand
  official_domains.json # allowlist of official government domains
  sources/              # official text, one file per scheme, with source URL and date checked
eval/
  questions.json    # questions with answers checked against official pages
  run_eval.py       # accuracy report
tests_core.py       # tests for the rules engine, link check and chunking
haqdaar_architecture.mmd
```

## Run locally

```
pip install -r requirements.txt
python tests_core.py        # quick check of the core logic
python app.py               # UI at http://localhost:7860, API docs at /docs
python eval/run_eval.py     # accuracy report
```

By default the app shows the retrieved official passages. Set `USE_LLM=1` to let a small Qwen model (via transformers) explain them in simple Urdu.

## Data and privacy policy

- Only official government sources are used. Each document stores its source URL and the date it was last checked.
- Eligibility rules are verified by hand against the official page, not copied from third-party sites.
- Haqdaar never asks for a CNIC number and does not store audio. Recordings are deleted right after transcription.
- The MVP covers a small set of schemes so that accuracy can be checked end to end.

## Evaluation

`eval/run_eval.py` runs about 30 questions with answers checked against official pages and reports accuracy. Failures are listed openly in this README. A few recorded Urdu questions are used to measure speech recognition errors too.

## Known limitations

- Covers only a few schemes in the MVP.
- Urdu speech recognition is imperfect, especially for conversational speech and accents, so voice is used mainly for the short profile questions, with confirm-back and tap fallbacks.
- Small open-source models can be weaker in Urdu, so answers use templates where needed.
- Scheme rules change; the date checked shown with each answer may be out of date.
- Haqdaar guides people but does not complete applications for them.

## Beyond the MVP (not in scope)

- More schemes and provinces, and a process to re-check sources regularly.
- Delivery through WhatsApp voice notes.
- Punjabi voice support.
- A separate guidance assistant for parents and teachers on children's online safety. This is a possible future direction only. It would need a much higher accuracy and safety bar, review by child-protection experts, careful handling of any data about children, and quality illustrations, so it is out of scope for this project.
