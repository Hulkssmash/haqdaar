"""Run the checked question set and print an accuracy report.

Usage:  python eval/run_eval.py
Edit eval/questions.json: add about 30 questions whose answers you have checked against the official pages.
expect_any: at least one of these strings must appear in the answer (leave empty for out-of-scope questions)
expect_grounded: true if the app should answer from a source, false if it should say 'not found'
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import rag  # noqa: E402

questions = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))
passed, failures = 0, []
for item in questions:
    res = rag.answer(item["q"])
    ok = res["grounded"] == item["expect_grounded"]
    if ok and item["expect_grounded"] and item.get("expect_any"):
        ok = any(s.lower() in res["answer"].lower() for s in item["expect_any"])
    if ok:
        passed += 1
    else:
        failures.append(item["q"])
print(f"Passed {passed}/{len(questions)} ({100 * passed / len(questions):.0f}%)")
for q in failures:
    print("FAILED:", q)
