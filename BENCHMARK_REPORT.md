# SQL Autocomplete Models: Performance Comparison Report


This report presents a empirical performance benchmark comparing two deep learning models trained for SQL query autocomplete (next-token prediction):
1. **Bi-LSTM Model** (`bi-lstm/sql_bi_lstm_model.h5`)
2. **Transformer Model** (`transformer/sql_transformer.keras`)

Both models were evaluated on a benchmark test suite covering 16 SQL query prompt sequences across 8 major SQL statement keywords: `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`, `HAVING`, `INSERT`, and `UPDATE`.

---

## 📊 Benchmark Performance Results

| Metric | Bi-LSTM Model | Transformer Model | Winner |
| :--- | :--- | :--- | :--- |
| **Top-1 Accuracy (%)** | 62.50% | 62.50% | **Tie** |
| **Top-3 Accuracy (%)** | 87.50% | 87.50% | **Tie** |
| **Perplexity ($\exp(\text{loss})$)** | **15.25** | 23.27 | **Bi-LSTM** |
| **Average Latency (ms/query)** | 107.97 ms | **94.69 ms** | **Transformer** |

---

## 🔬 Performance Metric Breakdown

### 1. Top-1 and Top-3 Accuracy
* **Result**: **Tie (Top-1: 62.50% | Top-3: 87.50%)**
* **Analysis**: Both models correctly predict the exact next SQL token **62.50%** of the time as their top-1 prediction. In real-world IDE autocomplete UI components—where top-3 drop-down suggestions are presented to the user—both models achieve an **87.50% Top-3 accuracy**. This means 7 out of 8 typing prompts offer the ground-truth token in the suggestion menu.

### 2. Perplexity & Model Confidence
* **Result**: **Bi-LSTM: 15.25** vs. **Transformer: 23.27**
* **Analysis**: Perplexity ($\exp(\text{cross-entropy loss})$) measures how uncertain the model is when assigning probabilities to target tokens. Lower perplexity indicates higher probability density assigned to the ground-truth token. The Bi-LSTM model achieves a lower perplexity (**15.25**) due to strong local sequential recurrence over short query prompts.

### 3. Inference Latency (Keystroke Speed)
* **Result**: **Transformer: 94.69 ms/query** vs. **Bi-LSTM: 107.97 ms/query**
* **Analysis**: Inference speed is critical for real-time autocomplete on every keystroke. The Transformer model executes **~12.3% faster** per query than the Bi-LSTM model. The Transformer leverages parallel tensor operations across self-attention heads, avoiding the step-by-step sequential processing bottleneck inherent to LSTM recurrent loops.

### 4. Context Window & Architecture Scalability
* **Transformer Architecture**: Uses Multi-Head Self-Attention over a 63-token sequence context window (`SEQ_LEN=63`), capturing dependencies across distant tokens in complex multi-table `JOIN` queries.
* **Bi-LSTM Architecture**: Uses bidirectional LSTM layers with pre-padded 126-length sequences (`max_len=127`), which unrolls sequentially and can experience information bottlenecks on longer queries.

---

## Final Model Choice for Deployment

### Selected Model: **Transformer Model** (`transformer/sql_transformer.keras`)

### Decision Rationale:
1. **Lower Latency for Real-Time Typing**: At **94.69 ms/query**, the Transformer provides faster response times, minimizing input latency in IDE suggestion menus.
2. **Matching Top Suggestion Quality**: The Transformer matches the Bi-LSTM's high **87.50% Top-3 accuracy**, ensuring top-tier prediction quality for end users.
3. **Scalable Attention Window**: Self-attention handles multi-table alias mappings (`T1`, `T2`) and clause dependencies far more effectively as queries grow in complexity.
