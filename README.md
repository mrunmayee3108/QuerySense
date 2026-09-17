# ⚡ QuerySense: AI-Powered SQL Autocomplete & Multi-Dialect Studio

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.16%2B-FF6F00.svg?logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)
[![SQLGlot](https://img.shields.io/badge/SQLGlot-Transpiler-22c55e.svg)](https://github.com/tobymao/sqlglot)
[![Dataset](https://img.shields.io/badge/Dataset-Spider%20SQL-blue.svg)](https://yale-lily.github.io/spider)
[![Streamlit](https://img.shields.io/badge/Streamlit-Fallback%20UI-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)

**QuerySense** is an end-to-end intelligent SQL development environment featuring **deep-learning-based real-time SQL next-token prediction** and **multi-dialect query transpilation**.

Trained on the comprehensive **Spider SQL dataset**, QuerySense evaluates and benchmarks sequential and attention-based architectures (**LSTM**, **Bi-LSTM**, and **Transformers**) to deliver high-accuracy, sub-100ms keystroke suggestions directly inside an interactive, developer-grade React studio.

---

## 🌟 Key Features

- **⚡ Inline Ghost-Text Autocomplete (<kbd>Tab</kbd> to Accept)**: Copilot/Cursor-style inline ghost text predicted directly ahead of your cursor. Press <kbd>Tab</kbd> or <kbd>→</kbd> to instantly accept.
- **🔤 Context-Aware Case Matching**: Dynamically detects typing casing style. Typing in lowercase (`select student_name `) outputs lowercase suggestions (`from`, `where`), while typing in UPPERCASE (`SELECT student_name `) outputs uppercase suggestions (`FROM`, `WHERE`). Supports Auto, lowercase, and UPPERCASE modes.
- **🖥️ Modern React + Vite Developer Studio**: High-contrast, dark-mode developer UI inspired by modern platforms (Linear, Supabase, Cursor), featuring live latency tracking (~94ms), token categorization chips (`[KW]`, `[VAL]`), and quick presets.
- **🌐 Multi-Dialect Transpiler**: Seamlessly translates and formats queries across 8 major database engines with SQLGlot:
  - PostgreSQL, MySQL, Snowflake, BigQuery, SQLite, DuckDB, Oracle, and T-SQL.
  - Supports keyword casing conversion (`lowercase` / `UPPERCASE` / `preserve`) and helpful syntax recovery hints.
- **🔀 Hybrid Suggestion Engine**: Combines neural Transformer softmax probability distributions with deterministic SQL grammar heuristics (e.g., `INSERT INTO`, `UPDATE SET`, `VALUES ( ... )`) for complete syntactic fluency.
- **🧠 Model Progression & Benchmarking**: Rigorously benchmarked standard LSTM, Bidirectional LSTM, and self-attention Transformer models on Top-1, Top-3, perplexity, and inference latency.

---

## 📊 Model Comparison & Benchmarks

To select the optimal production model, models were evaluated across 16 real-world SQL prompt sequences spanning major clauses (`SELECT`, `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`, `HAVING`, `INSERT`, and `UPDATE`).

| Metric | LSTM | Bi-LSTM | Transformer (Deployed) | Advantage |
| :--- | :---: | :---: | :---: | :--- |
| **Test Accuracy** | ~89.2% | 92.4% | **93.71%** | Highest generalization |
| **Best Val Accuracy**| ~90.1% | 93.1% | **94.14%** | Best validation performance |
| **Top-1 Benchmark** | 56.25% | 62.50% | **62.50%** | Accurate first choice |
| **Top-3 Benchmark** | 81.25% | 87.50% | **87.50%** | 7 out of 8 prompts hit target |
| **Perplexity** | 28.40 | **15.25** | 23.27 | Strong confidence score |
| **Inference Latency**| 118.2 ms | 107.97 ms | **94.69 ms** | **~12.3% faster** parallel inference |

> Detailed metrics, per-prompt evaluation logs, and decision rationale are documented in [`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md).

### Why the Transformer Was Chosen:
1. **Fast Keystroke Latency**: At **94.69 ms/query**, the self-attention mechanism avoids sequential recurrent step bottlenecks, ensuring frictionless typing.
2. **High Top-3 Coverage**: **87.50% Top-3 accuracy** delivers the exact target SQL token in suggestion pill options.
3. **Multi-Clause Attention**: Self-attention captures long-range dependencies across complex `JOIN ... ON` table aliases far better than recurrent models.

---

## 🏗️ System Architecture

```
User Query Input (Keystroke / Text)
                │
                ▼
    ┌───────────────────────────┐
    │  Tokenizer & Normalizer   │
    └─────────────┬─────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
  ┌──────────────┐  ┌──────────────┐
  │ Transformer  │  │  Syntactic   │
  │ Neural Model │  │  Heuristics  │
  └──────┬───────┘  └──────┬───────┘
         │                 │
         └────────┬────────┘
                  ▼
      Hybrid Ranking & Case Adapter
                  │
                  ▼
   Inline Ghost Text (Tab ⇥) & Suggestion Chips
```

---

## 📁 Repository Structure

```
QuerySense/
├── frontend/                  # React + Vite developer studio
│   ├── src/
│   │   ├── components/
│   │   │   ├── SqlEditor.jsx  # Dual-layer ghost editor with Tab completion
│   │   │   └── Transpiler.jsx # SQLGlot multi-dialect transpiler
│   │   ├── App.jsx            # Main app container & tab router
│   │   └── index.css          # Dark-mode developer design system
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Dev server & FastAPI proxy configuration
│
├── server.py                  # High-performance FastAPI model backend
├── app.py                     # Streamlit fallback application
├── benchmark.py               # Empirical benchmarking suite (Accuracy, Latency, Perplexity)
├── BENCHMARK_REPORT.md        # Comprehensive benchmark comparison report
├── requirements.txt           # Python dependencies
├── train_spider.json          # Spider benchmark dataset
│
├── transformer/               # Production Transformer model assets
│   ├── next_word_pred_transformersTF.ipynb
│   ├── sql_transformer.keras
│   ├── sql_tokenizer.pkl
│   ├── sql_transformer_config.json
│   └── transformer_results.json
│
├── bi-lstm/                   # Bidirectional LSTM model assets
│   ├── next_word_pred_bi_lstm.ipynb
│   ├── sql_bi_lstm_model.h5
│   ├── tok.pkl
│   └── max_len.pkl
│
└── lstm/                      # Baseline LSTM model assets
    ├── next_word_predictor_lstm.ipynb
    ├── sql_lstm_model.h5
    ├── tokenizer.pkl
    └── max_len.pkl
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Node.js 18+ & npm
- Git

### 2. Installation
Clone the repository and install Python dependencies:

```bash
git clone https://github.com/mrunmayee3108/QuerySense.git
cd QuerySense
pip install -r requirements.txt
```

### 3. Launch the React + Vite Studio (Recommended)

1. **Start the FastAPI inference backend**:
   ```bash
   python server.py
   ```
   Backend will run at `http://127.0.0.1:8000`.

2. **Start the React frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open your browser at `http://127.0.0.1:5173`.

### 4. Alternative: Launch the Streamlit App
If you prefer running the original Streamlit interface:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 5. Run the Benchmarks
To reproduce the empirical evaluation between models:

```bash
python benchmark.py
```

---

## 🛠️ Tech Stack

- **Frontend**: React 19, Vite, Lucide Icons, Custom CSS Design System
- **Backend**: FastAPI, Uvicorn, Python 3.10+
- **Deep Learning**: TensorFlow, Keras (Multi-Head Self-Attention Transformer, Bi-LSTM, LSTM)
- **Sequence Modeling**: Multi-Head Attention, Tokenizers, Custom Sequence Padding
- **SQL Analysis & AST**: SQLGlot
- **Dataset**: Spider (Yale Lily Lab)
- **Alternative Framework**: Streamlit

---

## 📄 License
This project is licensed under the MIT License.
