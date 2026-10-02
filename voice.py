"""Optional Urdu speech-to-text with Whisper. Loaded only when the mic is used."""
import os

ASR_MODEL = os.getenv("ASR_MODEL", "openai/whisper-small")
_asr = None


def transcribe(audio_path):
    """Return the transcribed text. The user must confirm it before it is used."""
    global _asr
    if not audio_path:
        return ""
    if _asr is None:
        from transformers import pipeline
        _asr = pipeline("automatic-speech-recognition", model=ASR_MODEL)
    out = _asr(audio_path, generate_kwargs={"language": "urdu", "task": "transcribe"})
    return out["text"].strip()
