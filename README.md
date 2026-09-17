# ⚡ QuerySense: AI-Powered SQL Autocomplete & Multi-Dialect Studio

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.16%2B-FF6F00.svg?logo=tensorflow&logoColor=white)](https://www.tensorflow.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLGlot](https://img.shields.io/badge/SQLGlot-Transpiler-green.svg)](https://github.com/tobymao/sqlglot)
[![Dataset](https://img.shields.io/badge/Dataset-Spider%20SQL-purple.svg)](https://yale-lily.github.io/spider)

**QuerySense** is an end-to-end intelligent SQL development environment featuring **deep-learning-based real-time SQL next-token prediction** and **multi-dialect query transpilation**.

Trained on the comprehensive **Spider SQL dataset**, QuerySense evaluates and benchmarks sequential and attention-based architectures (**LSTM**, **Bi-LSTM**, and **Transformers**) to deliver high-accuracy, sub-100ms keystroke suggestions directly inside an interactive modern web studio.

---

## 🌟 Key Features

- **⚡ Real-Time Live SQL Autocomplete**: Predicts next SQL keywords, clauses, aliases, and table tokens on every keystroke with confidence percentages.
- **🧠 Model Progression & Benchmarking**: Rigorously benchmarked standard LSTM, Bidirectional LSTM, and self-attention Transformer models on Top-1, Top-3, perplexity, and inference latency.
- **🔀 Hybrid Suggestion Engine**: Combines neural model softmax probability distributions with deterministic SQL grammar heuristics (e.g., `INSERT INTO`, `UPDATE SET`, `VALUES ( ... )`) for complete syntactic fluency.
- **🌐 Multi-Dialect Transpiler**: Seamlessly translates and formats queries across 8 major database dialects:
  - PostgreSQL, MySQL, Snowflake, BigQuery, SQLite, DuckDB, Oracle, and T-SQL (via SQLGlot).
- **🎨 Interactive Dark-Mode UI**: Built with Streamlit featuring one-click presets, dynamic token insertions, and interactive Top-K sliders.

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
     Hybrid Ranking & Top-K Filter
                 │
                 ▼
  Real-Time Next-Token Suggestions  ──►  Click to Auto-Complete
```

---

## 📁 Repository Structure

```
QuerySense/
├── app.py                     # Streamlit web application & studio UI
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
- Git

### 2. Installation
Clone the repository and install the dependencies:

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
   Backend will run on `http://127.0.0.1:8000`.

2. **Start the React frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open your browser at `http://127.0.0.1:5173`.

### 4. Alternative: Launch the Streamlit App
If you prefer running via Streamlit:
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

- **Deep Learning**: TensorFlow, Keras
- **NLP / Sequence Modeling**: Multi-Head Self-Attention, Bidirectional LSTM, Tokenizers
- **Application Framework**: Streamlit, Streamlit-Keyup
- **SQL Analysis & AST**: SQLGlot
- **Dataset**: Spider (Yale Lily Lab)

---

## 📄 License
This project is licensed under the MIT License.
