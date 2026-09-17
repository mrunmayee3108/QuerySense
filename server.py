import os
import re
import time
import pickle
import numpy as np
import tensorflow as tf
import sqlglot
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Patch keras Operation for compatibility if needed
try:
    from keras.src.ops.operation import Operation
    orig_from_config = Operation.from_config

    @classmethod
    def patched_from_config(cls, config):
        if isinstance(config, dict):
            config = config.copy()
            config.pop('quantization_config', None)
        return orig_from_config.__func__(cls, config)

    Operation.from_config = patched_from_config
except Exception:
    pass

app = FastAPI(
    title="QuerySense API",
    description="High-performance backend for QuerySense SQL Autocomplete & Transpiler",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
tokenizer = None
SEQ_LEN = 63

SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
    "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "INSERT INTO", "VALUES",
    "UPDATE", "SET", "DELETE FROM", "AND", "OR", "NOT", "IN", "BETWEEN",
    "LIKE", "IS NULL", "IS NOT NULL", "AS", "DISTINCT", "UNION", "ALL",
    "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END", "ASC", "DESC",
    "COUNT", "AVG", "SUM", "MIN", "MAX"
]


def load_model_assets():
    global model, tokenizer
    model_path = os.path.join("transformer", "sql_transformer.keras")
    tok_path = os.path.join("transformer", "sql_tokenizer.pkl")

    if not os.path.exists(model_path) or not os.path.exists(tok_path):
        print(f"Warning: Model or tokenizer not found at {model_path} / {tok_path}")
        return False

    print("Loading Transformer model & tokenizer...")
    try:
        model = tf.keras.models.load_model(model_path, compile=False)
        with open(tok_path, "rb") as f:
            tokenizer = pickle.load(f)
        print("Transformer model loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        return False


@app.on_event("startup")
def startup():
    load_model_assets()


class SuggestionItem(BaseModel):
    word: str
    confidence: float
    ghost_suffix: str = ""
    is_keyword: bool = True


class SuggestRequest(BaseModel):
    query: str
    top_k: int = 3
    case_mode: str = "auto"  # "auto", "lower", "upper"


class SuggestResponse(BaseModel):
    suggestions: List[SuggestionItem]
    detected_case: str
    latency_ms: float
    inline_ghost: str = ""


class TranspileRequest(BaseModel):
    query: str
    target_dialect: str = "postgres"
    pretty: bool = True
    keyword_case: str = "preserve"  # "preserve", "lower", "upper"


class TranspileResponse(BaseModel):
    transpiled: str
    target_dialect: str
    success: bool
    error: Optional[str] = None
    friendly_hint: Optional[str] = None


def detect_query_case(query: str, current_prefix: str = "") -> str:
    """
    Detects whether the user is typing predominantly in lowercase or uppercase.
    Prioritizes the active word prefix if being typed, then SQL keywords, then query letters.
    """
    if current_prefix and any(c.isalpha() for c in current_prefix):
        letters = [c for c in current_prefix if c.isalpha()]
        if all(c.islower() for c in letters):
            return "lower"
        elif all(c.isupper() for c in letters):
            return "upper"

    tokens = [t.strip(",()=><;") for t in query.split() if t.strip(",()=><;")]
    if not tokens:
        return "lower"

    kw_set = {k.upper() for k in SQL_KEYWORDS}
    upper_kw = 0
    lower_kw = 0

    for t in tokens:
        if t.upper() in kw_set and any(c.isalpha() for c in t):
            if t.isupper():
                upper_kw += 1
            elif t.islower():
                lower_kw += 1

    if upper_kw > lower_kw:
        return "upper"
    if lower_kw > upper_kw:
        return "lower"

    first_letters = [c for c in tokens[0] if c.isalpha()]
    if first_letters:
        if all(c.isupper() for c in first_letters):
            return "upper"
        elif all(c.islower() for c in first_letters):
            return "lower"

    total_upper = sum(1 for c in query if c.isupper())
    total_lower = sum(1 for c in query if c.islower())
    return "upper" if total_upper > total_lower else "lower"


def apply_casing(text: str, target_case: str) -> str:
    if target_case == "lower":
        return text.lower()
    elif target_case == "upper":
        return text.upper()
    return text


def normalize_text_for_tokenizer(text: str) -> str:
    if not tokenizer:
        return text
    words = text.split()
    normalized = []
    for w in words:
        w_upper = w.upper()
        if w_upper in tokenizer.word_index:
            normalized.append(w_upper)
        else:
            normalized.append(w)
    return " ".join(normalized)


@app.get("/api/health")
def health():
    return {
        "status": "ready" if model is not None else "degraded",
        "model_loaded": model is not None,
        "model_type": "Transformer (Multi-Head Self-Attention)",
        "context_window": SEQ_LEN
    }


@app.get("/api/presets")
def get_presets():
    return [
        {"label": "SELECT * FROM", "query": "select * from "},
        {"label": "SELECT T1.name FROM", "query": "select t1.name from "},
        {"label": "INSERT INTO", "query": "insert into "},
        {"label": "UPDATE", "query": "update "},
        {"label": "SELECT count(*) FROM", "query": "select count(*) from "}
    ]


@app.post("/api/suggest", response_model=SuggestResponse)
def get_suggestions(req: SuggestRequest):
    start_time = time.perf_counter()
    query_text_raw = req.query
    query_text = query_text_raw.strip()

    if not query_text:
        detected_case = req.case_mode if req.case_mode != "auto" else "lower"
        default_starters = [
            ("SELECT", 99.0),
            ("INSERT INTO", 85.0),
            ("UPDATE", 80.0),
            ("DELETE FROM", 75.0)
        ]
        results = [
            SuggestionItem(
                word=apply_casing(w, detected_case),
                confidence=c,
                ghost_suffix=apply_casing(w, detected_case),
                is_keyword=True
            )
            for w, c in default_starters[:req.top_k]
        ]
        inline_ghost = results[0].ghost_suffix if results else ""
        latency = (time.perf_counter() - start_time) * 1000.0
        return SuggestResponse(
            suggestions=results,
            detected_case=detected_case,
            latency_ms=round(latency, 2),
            inline_ghost=inline_ghost
        )

    has_trailing_space = query_text_raw.endswith(" ")
    parts = query_text.split()

    if has_trailing_space:
        prompt = query_text
        prefix = ""
    else:
        prompt = " ".join(parts[:-1]) if len(parts) > 1 else ""
        prefix = parts[-1] if parts else ""

    detected_case = detect_query_case(query_text_raw, current_prefix=prefix)
    target_case = detected_case if req.case_mode == "auto" else req.case_mode

    candidates = []

    if model and tokenizer:
        eval_prompt = prompt if prompt.strip() else query_text
        normalized_prompt = normalize_text_for_tokenizer(eval_prompt)
        seq = tokenizer.texts_to_sequences([normalized_prompt])
        tokens = seq[0] if seq else []

        if tokens and tokens != [1]:
            padded = tf.keras.preprocessing.sequence.pad_sequences(
                [tokens],
                maxlen=SEQ_LEN,
                padding="post",
                truncating="post"
            )
            logits = model.predict(padded, verbose=0)[0]
            pos = min(len(tokens) - 1, SEQ_LEN - 1)
            probs = tf.nn.softmax(logits[pos]).numpy()
            top_ids = np.argsort(probs)[-40:][::-1]

            for idx in top_ids:
                word = tokenizer.index_word.get(idx, "")
                p = float(probs[idx]) * 100.0
                if word and word != "<UNK>":
                    candidates.append((word, p))

    last_word = parts[-1].upper() if parts else ""
    prev_word = parts[-2].upper() if len(parts) > 1 else ""

    if last_word == "INSERT" or (prev_word == "INSERT" and prefix.upper().startswith("I")):
        candidates.insert(0, ("INTO", 98.0))
    elif last_word == "INTO" or prev_word == "INTO":
        candidates.insert(0, ("table_name", 90.0))
        candidates.insert(1, ("VALUES", 85.0))
    elif last_word == "UPDATE" or (prev_word == "UPDATE" and prefix.upper().startswith("U")):
        candidates.insert(0, ("table_name", 90.0))
        candidates.insert(1, ("SET", 85.0))
    elif last_word == "SET":
        candidates.insert(0, ("column_name =", 90.0))
    elif last_word == "VALUES":
        candidates.insert(0, ("( val1, val2 )", 90.0))
    elif last_word == "WHERE":
        candidates.insert(0, ("column_name =", 85.0))

    prefix_upper = prefix.upper()
    prefix_len = len(prefix)

    filtered = []
    seen = set()

    for word, score in candidates:
        w_upper = word.upper()
        if w_upper not in seen:
            seen.add(w_upper)
            if not prefix or w_upper.startswith(prefix_upper):
                cased_word = apply_casing(word, target_case)
                if prefix:
                    ghost_suffix = cased_word[prefix_len:]
                else:
                    ghost_suffix = cased_word

                filtered.append(SuggestionItem(
                    word=cased_word,
                    confidence=round(score, 1),
                    ghost_suffix=ghost_suffix,
                    is_keyword=w_upper in SQL_KEYWORDS
                ))

    if len(filtered) < req.top_k:
        for kw in SQL_KEYWORDS:
            kw_upper = kw.upper()
            if kw_upper not in seen:
                if not prefix or kw_upper.startswith(prefix_upper):
                    cased_kw = apply_casing(kw, target_case)
                    ghost_suffix = cased_kw[prefix_len:] if prefix else cased_kw
                    seen.add(kw_upper)
                    filtered.append(SuggestionItem(
                        word=cased_kw,
                        confidence=20.0,
                        ghost_suffix=ghost_suffix,
                        is_keyword=True
                    ))
                    if len(filtered) >= req.top_k:
                        break

    final_suggestions = filtered[:req.top_k]
    inline_ghost = final_suggestions[0].ghost_suffix if final_suggestions else ""
    latency = (time.perf_counter() - start_time) * 1000.0

    return SuggestResponse(
        suggestions=final_suggestions,
        detected_case=target_case,
        latency_ms=round(latency, 2),
        inline_ghost=inline_ghost
    )


DANGLING_KEYWORDS = ["WHERE", "AND", "OR", "JOIN", "ON", "FROM", "SET", "HAVING", "GROUP BY", "ORDER BY"]


@app.post("/api/transpile", response_model=TranspileResponse)
def transpile_sql(req: TranspileRequest):
    raw_query = req.query.strip()
    if not raw_query:
        return TranspileResponse(
            transpiled="",
            target_dialect=req.target_dialect,
            success=False,
            error="Please enter a SQL query to transpile."
        )

    tokens = raw_query.split()
    last_token_upper = tokens[-1].upper() if tokens else ""
    last_two_tokens = " ".join([t.upper() for t in tokens[-2:]]) if len(tokens) >= 2 else ""

    friendly_hint = None
    if last_two_tokens in DANGLING_KEYWORDS:
        friendly_hint = f"Your query ends with an incomplete '{last_two_tokens}' clause. Add an expression or condition (e.g. '{last_two_tokens} id = 1') to complete the query."
    elif last_token_upper in DANGLING_KEYWORDS:
        friendly_hint = f"Your query ends with an incomplete '{tokens[-1]}' clause. Complete it with a condition (e.g. '{tokens[-1]} id = 1') or column name."

    query_to_transpile = raw_query

    try:
        results = sqlglot.transpile(
            query_to_transpile,
            write=req.target_dialect,
            pretty=req.pretty
        )
        transpiled_text = results[0] if results else ""

        if req.keyword_case == "lower":
            transpiled_text = convert_keywords_casing(transpiled_text, to_upper=False)
        elif req.keyword_case == "upper":
            transpiled_text = convert_keywords_casing(transpiled_text, to_upper=True)

        return TranspileResponse(
            transpiled=transpiled_text,
            target_dialect=req.target_dialect,
            success=True,
            friendly_hint=None
        )
    except Exception as e:
        clean_err = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
        return TranspileResponse(
            transpiled="",
            target_dialect=req.target_dialect,
            success=False,
            error=f"Transpilation Error: {clean_err}",
            friendly_hint=friendly_hint
        )


def convert_keywords_casing(sql_str: str, to_upper: bool = True) -> str:
    for kw in SQL_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        repl = kw.upper() if to_upper else kw.lower()
        sql_str = re.sub(pattern, repl, sql_str, flags=re.IGNORECASE)
    return sql_str


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
