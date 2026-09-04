import os
import time
import pickle
import numpy as np
import streamlit as st
import tensorflow as tf
import sqlglot

try:
    if hasattr(st, "components") and hasattr(st.components, "v2") and hasattr(st.components.v2, "component"):
        orig_comp = st.components.v2.component
        def patched_component(*args, **kwargs):
            kwargs.pop('isolate_styles', None)
            return orig_comp(*args, **kwargs)
        st.components.v2.component = patched_component

    from st_keyup import st_keyup
    HAS_KEYUP = True
except Exception:
    HAS_KEYUP = False


st.set_page_config(
    page_title="QuerySense - SQL Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    /* Main container background */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    /* Header title gradient */
    .gradient-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }

    /* Card style */
    .studio-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }

    /* Suggestion pill button styling */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_querysense_assets():
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

    model_path = os.path.join(
        "transformer",
        "sql_transformer.keras"
    )

    tok_path = os.path.join(
        "transformer",
        "sql_tokenizer.pkl"
    )

    max_len_path = os.path.join(
        "bi-lstm",
        "max_len.pkl"
    )

    model = tf.keras.models.load_model(
        model_path,
        compile=False
    )

    with open(tok_path, "rb") as f:
        tokenizer = pickle.load(f)

    with open(max_len_path, "rb") as f:
        max_len = pickle.load(f)

    return model, tokenizer, max_len


try:
    transformer_model, tokenizer, max_len = load_querysense_assets()

except Exception as e:
    st.error(f"Error loading model resources: {e}")
    st.stop()


SQL_KEYWORDS = [
    "SELECT",
    "FROM",
    "WHERE",
    "GROUP BY",
    "ORDER BY",
    "HAVING",
    "INSERT INTO",
    "UPDATE",
    "SET",
    "DELETE FROM",
    "VALUES",
    "JOIN",
    "ON",
    "AS",
    "AND",
    "OR",
    "LIMIT",
    "COUNT",
    "AVG",
    "SUM",
    "MIN",
    "MAX",
    "ASC",
    "DESC"
]


def normalize_text_for_tokenizer(text):
    """
    Normalizes tokens so case-insensitive SQL keywords
    map to tokenizer vocabulary indices.
    """

    words = text.split()

    normalized_words = []

    for w in words:
        w_upper = w.upper()

        if w_upper in tokenizer.word_index:
            normalized_words.append(w_upper)

        else:
            normalized_words.append(w)

    return " ".join(normalized_words)


def get_hybrid_suggestions(
    query_text,
    top_k=3,
    seq_len=63
):

    query_text_raw = query_text

    query_text = query_text.strip()

    if not query_text:
        return [
            ("SELECT", 99.0),
            ("INSERT INTO", 85.0),
            ("UPDATE", 80.0),
            ("DELETE FROM", 75.0)
        ][:top_k]

    has_trailing_space = query_text_raw.endswith(" ")

    parts = query_text.split()

    if has_trailing_space:
        prompt = query_text
        prefix = ""

    else:
        prompt = (
            " ".join(parts[:-1])
            if len(parts) > 1
            else ""
        )

        prefix = parts[-1].upper()

    candidates = []

    eval_prompt = (
        prompt
        if prompt.strip()
        else query_text
    )

    normalized_prompt = normalize_text_for_tokenizer(
        eval_prompt
    )

    tokens = tokenizer.texts_to_sequences(
        [normalized_prompt]
    )[0]

    if tokens and tokens != [1]:

        padded = tf.keras.preprocessing.sequence.pad_sequences(
            [tokens],
            maxlen=seq_len,
            padding="post",
            truncating="post"
        )

        logits = transformer_model.predict(
            padded,
            verbose=0
        )[0]

        pos = min(
            len(tokens) - 1,
            seq_len - 1
        )

        probs = tf.nn.softmax(
            logits[pos]
        ).numpy()

        top_ids = np.argsort(probs)[-40:][::-1]

        for idx in top_ids:

            word = tokenizer.index_word.get(
                idx,
                ""
            )

            p = float(probs[idx]) * 100.0

            if word and word != "<UNK>":
                candidates.append(
                    (word, p)
                )

    last_word = (
        parts[-1].upper()
        if parts
        else ""
    )

    prev_word = (
        parts[-2].upper()
        if len(parts) > 1
        else ""
    )

    if (
        last_word == "INSERT"
        or (
            prev_word == "INSERT"
            and prefix.startswith("I")
        )
    ):

        candidates.insert(
            0,
            ("INTO", 98.0)
        )

    elif (
        last_word == "INTO"
        or prev_word == "INTO"
    ):

        candidates.insert(
            0,
            ("table_name", 90.0)
        )

        candidates.insert(
            1,
            ("VALUES", 85.0)
        )

    elif (
        last_word == "UPDATE"
        or (
            prev_word == "UPDATE"
            and prefix.startswith("U")
        )
    ):

        candidates.insert(
            0,
            ("table_name", 90.0)
        )

        candidates.insert(
            1,
            ("SET", 85.0)
        )

    elif last_word == "SET":

        candidates.insert(
            0,
            ("column_name =", 90.0)
        )

    elif last_word == "VALUES":

        candidates.insert(
            0,
            ("( val1, val2 )", 90.0)
        )

    elif last_word == "WHERE":

        candidates.insert(
            0,
            ("column_name =", 85.0)
        )

    results = []

    seen = set()

    for word, score in candidates:

        w_upper = word.upper()

        if w_upper not in seen:

            seen.add(w_upper)

            if (
                not prefix
                or w_upper.startswith(prefix)
                or word.lower().startswith(
                    parts[-1].lower()
                )
            ):

                results.append(
                    (word, score)
                )

    if len(results) < top_k:

        for kw in SQL_KEYWORDS:

            kw_upper = kw.upper()

            if kw_upper not in seen:

                if (
                    not prefix
                    or kw_upper.startswith(prefix)
                ):

                    results.append(
                        (kw, 15.0)
                    )

                    seen.add(kw_upper)

    return results[:top_k]


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "query_text" not in st.session_state:
    st.session_state["query_text"] = "SELECT * FROM "

if "input_key_id" not in st.session_state:
    st.session_state["input_key_id"] = 0


def update_query_state(new_text):
    # Main source of truth
    st.session_state["query_text"] = new_text
    # Increment version counter to re-render the input widget with the new value,
    # avoiding Streamlit's "cannot modify widget after instantiation" restriction.
    st.session_state["input_key_id"] += 1


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
        <span style="font-size: 2.2rem;">⚡</span>
        <span style="font-size: 1.4rem; font-weight: 800; color: #f8fafc;">
            QuerySense Studio
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("⚙️ Autocomplete Settings")

    top_k_slider = st.slider(
        "Top-K Suggestions",
        min_value=1,
        max_value=5,
        value=3,
        help="Select number of autocomplete suggestions to display"
    )


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    '<div class="gradient-title">QuerySense SQL Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">AI-Powered Live SQL Autocomplete & Multi-Dialect Transpilation</div>',
    unsafe_allow_html=True
)


tab1, tab2 = st.tabs(
    [
        "Real-Time Live SQL Autocomplete",
        "Multi-Dialect Transpiler"
    ]
)


# =========================================================
# TAB 1 - AUTOCOMPLETE
# =========================================================

with tab1:

    st.subheader(
        "Interactive Real-Time Query Editor"
    )

    st.caption("Quick Presets:")

    p_cols = st.columns(5)

    if p_cols[0].button("SELECT * FROM"):

        update_query_state(
            "SELECT * FROM "
        )

        st.rerun()

    if p_cols[1].button("SELECT T1.name FROM"):

        update_query_state(
            "SELECT T1.name FROM "
        )

        st.rerun()

    if p_cols[2].button("INSERT INTO"):

        update_query_state(
            "INSERT INTO "
        )

        st.rerun()

    if p_cols[3].button("UPDATE"):

        update_query_state(
            "UPDATE "
        )

        st.rerun()

    if p_cols[4].button("SELECT count ( * ) FROM"):

        update_query_state(
            "SELECT count ( * ) FROM "
        )

        st.rerun()


    # -----------------------------------------------------
    # QUERY INPUT
    # -----------------------------------------------------
    input_widget_key = f"query_input_{st.session_state['input_key_id']}"

    if HAS_KEYUP:
        try:
            user_query = st_keyup(
                "Type your SQL Query below (suggestions update LIVE on every keypress):",
                value=st.session_state["query_text"],
                key=input_widget_key
            )
            st.session_state["query_text"] = user_query
        except Exception:
            user_query = st.text_input(
                "Type your SQL Query below (press Enter or defocus to apply):",
                value=st.session_state["query_text"],
                key=input_widget_key
            )
            st.session_state["query_text"] = user_query
    else:
        user_query = st.text_input(
            "Type your SQL Query below (press Enter or defocus to apply):",
            value=st.session_state["query_text"],
            key=input_widget_key
        )
        st.session_state["query_text"] = user_query


    # -----------------------------------------------------
    # GET SUGGESTIONS
    # -----------------------------------------------------

    suggestions = get_hybrid_suggestions(
        st.session_state["query_text"],
        top_k=top_k_slider
    )


    st.subheader(
        "AI Live Next-Word Suggestions"
    )


    if suggestions:

        st.write(
            "Click any suggestion to insert or complete the token in your query:"
        )

        btn_cols = st.columns(
            len(suggestions)
        )


        for i, (word, confidence) in enumerate(
            suggestions
        ):

            btn_label = (
                f"➕ {word} "
                f"({confidence:.1f}%)"
            )

            if btn_cols[i].button(
                btn_label,
                key=f"sug_btn_{i}_{word}"
            ):

                current_raw = (
                    st.session_state["query_text"]
                )

                has_space = (
                    current_raw.endswith(" ")
                )

                parts = (
                    current_raw.strip().split()
                )


                if has_space or not parts:

                    new_text = (
                        f"{current_raw.rstrip()} "
                        f"{word} "
                    )

                else:

                    new_text = (
                        " ".join(
                            parts[:-1] + [word]
                        )
                        + " "
                    )


                # Update main state
                update_query_state(
                    new_text
                )

                # Rerun so the widget receives
                # the updated value BEFORE being
                # instantiated again.
                st.rerun()

    else:

        st.info(
            "Start typing a SQL statement "
            "(e.g. `select`, `insert into`, `update`) "
            "to view live suggestions."
        )


# =========================================================
# TAB 2 - SQLGLOT TRANSPILER
# =========================================================

with tab2:

    st.subheader(
        "SQLGlot Multi-Dialect Transpiler"
    )

    st.caption(
        "Reformat and convert SQL queries across "
        "popular database dialects seamlessly."
    )


    col_input, col_config = st.columns(
        [3, 1]
    )


    with col_config:

        target_dialect = st.selectbox(
            "Select Target Dialect",

            options=[
                "postgres",
                "mysql",
                "snowflake",
                "bigquery",
                "sqlite",
                "duckdb",
                "oracle",
                "tsql"
            ],

            index=0
        )


        pretty_format = st.checkbox(
            "Pretty Format",
            value=True
        )


        transpile_btn = st.button(
            "Transpile Query",
            use_container_width=True
        )


    with col_input:

        transpile_query_input = st.text_area(
            "Source SQL Query to Transpile:",
            value=st.session_state["query_text"],
            height=140,
            key=f"transpile_input_{st.session_state['input_key_id']}"
        )


    if transpile_btn:

        if not transpile_query_input.strip():

            st.warning(
                "Please enter a SQL query to transpile."
            )

        else:

            try:

                transpiled_result = sqlglot.transpile(
                    transpile_query_input,
                    write=target_dialect,
                    pretty=pretty_format
                )[0]


                st.success(
                    f"Transpiled successfully to "
                    f"`{target_dialect}`!"
                )

                st.code(
                    transpiled_result,
                    language="sql"
                )

            except Exception as ex:

                st.error(
                    f"Transpilation Error: {ex}"
                )