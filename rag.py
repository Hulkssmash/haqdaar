"""Retrieval and grounded answers.

- Embeddings: multilingual-e5 (sentence-transformers)
- Vector store: Chroma (in-memory, rebuilt at start-up from data/sources)
- LLM: optional. Set USE_LLM=1 to let a small Qwen model explain the retrieved text.
  Without it, the app shows the retrieved official passages directly (always safe).
"""
import os

import sources
import texts

EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
USE_LLM = os.getenv("USE_LLM", "0") == "1"           # local model on this machine (slow on free CPU)
API_MODEL = os.getenv("API_MODEL", "")                # e.g. a model id from the Hugging Face Inference Playground
HF_TOKEN = os.getenv("HF_TOKEN", "")                  # set as a Space SECRET, never in the code
# Cosine distance above this means "not close enough to count as found". Tune with eval/run_eval.py.
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.30"))
TOP_K = int(os.getenv("TOP_K", "3"))

_embedder = None
_collection = None
_llm = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _embed(strings, prefix):
    # e5 models expect "query: " / "passage: " prefixes
    vecs = _get_embedder().encode([prefix + s for s in strings], normalize_embeddings=True)
    return vecs.tolist()


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.Client()
        col = client.get_or_create_collection("schemes", metadata={"hnsw:space": "cosine"})
        items = sources.load_all()
        if items:
            col.add(
                ids=[i["id"] for i in items],
                documents=[i["text"] for i in items],
                embeddings=_embed([i["text"] for i in items], "passage: "),
                metadatas=[{"scheme_id": i["scheme_id"], "source_url": i["source_url"],
                            "checked_on": i["checked_on"]} for i in items],
            )
        _collection = col
    return _collection


_STOP = set("the a an of to in is are for and or on at by with what who how can do does i my me you your it this that be as from".split())


def _words(s):
    import re
    return [w for w in re.findall(r"\w+", s.lower()) if w not in _STOP and len(w) > 1]


def _keyword_retrieve(question, scheme_ids, k):
    """Lightweight search with no ML packages: score chunks by shared words with the question.
    Used when sentence-transformers/chroma are not installed or SEARCH_MODE=keyword."""
    q = set(_words(question))
    if not q:
        return []
    scored = []
    for it in sources.load_all():
        if scheme_ids and it["scheme_id"] not in scheme_ids:
            continue
        frac = len(q & set(_words(it["text"]))) / len(q)
        scored.append((frac, it))
    scored.sort(key=lambda t: -t[0])
    hits = []
    for frac, it in scored[:k]:
        # map to the same "distance" scale the caller uses: pass only if at least 40% of the question words match
        dist = 0.2 if frac >= 0.4 else 1.0
        hits.append({"text": it["text"], "distance": dist, "scheme_id": it["scheme_id"],
                     "source_url": it["source_url"], "checked_on": it["checked_on"]})
    return hits


def retrieve(question, scheme_ids=None, k=TOP_K):
    if os.getenv("SEARCH_MODE", "auto") == "keyword":
        return _keyword_retrieve(question, scheme_ids, k)
    try:
        return _vector_retrieve(question, scheme_ids, k)
    except ImportError:
        return _keyword_retrieve(question, scheme_ids, k)


def _vector_retrieve(question, scheme_ids=None, k=TOP_K):
    col = _get_collection()
    if col.count() == 0:
        return []
    kwargs = {"query_embeddings": _embed([question], "query: "), "n_results": min(k, col.count())}
    if scheme_ids:
        kwargs["where"] = {"scheme_id": {"$in": list(scheme_ids)}}
    res = col.query(**kwargs)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"text": doc, "distance": float(dist), **meta})
    return hits


_SYSTEM = ("You explain government schemes in simple Urdu. Use ONLY the context. "
           "If the context does not answer the question, say you do not know. Do not invent details.")


def _generate_api(question, hits):
    """Hosted model through Hugging Face Inference Providers. Returns None on ANY failure."""
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(api_key=HF_TOKEN, timeout=25)
        context = "\n\n".join(h["text"] for h in hits)
        out = client.chat.completions.create(
            model=API_MODEL, max_tokens=300, temperature=0,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}])
        text = (out.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None  # credits used up, model unavailable, timeout: show the official passages instead


def _generate(question, hits):
    """Optional: an LLM explains the retrieved text only. Returns None if unavailable."""
    global _llm
    if API_MODEL and HF_TOKEN:
        return _generate_api(question, hits)
    if not USE_LLM:
        return None
    try:
        if _llm is None:
            from transformers import pipeline
            _llm = pipeline("text-generation", model=LLM_MODEL)
        context = "\n\n".join(h["text"] for h in hits)
        messages = [
            {"role": "system", "content": (
                "You explain government schemes in simple Urdu. Use ONLY the context. "
                "If the context does not answer the question, say you do not know. Do not invent details.")},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ]
        out = _llm(messages, max_new_tokens=300, do_sample=False)
        return out[0]["generated_text"][-1]["content"].strip()
    except Exception:
        return None  # fall back to showing the official passages


def answer(question, scheme_ids=None):
    """Return {answer, grounded, sources}. Never answers without a retrieved official source."""
    hits = [h for h in retrieve(question, scheme_ids) if h["distance"] <= MAX_DISTANCE]
    if not hits:
        return {"answer": f"{texts.NOT_FOUND_UR}\n\n{texts.NOT_FOUND_EN}", "grounded": False, "sources": []}
    generated = _generate(question, hits)
    body = generated if generated else "\n\n".join(h["text"] for h in hits)
    seen, srcs = set(), []
    for h in hits:
        key = (h["source_url"], h["checked_on"])
        if key not in seen:
            seen.add(key)
            srcs.append({"url": h["source_url"], "checked_on": h["checked_on"], "scheme_id": h["scheme_id"]})
    return {"answer": body, "grounded": True, "sources": srcs}
