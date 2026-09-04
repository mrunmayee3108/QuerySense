import os
import sys
import time
import pickle
import numpy as np

try:
    import tensorflow as tf
except ImportError:
    print("Installing tensorflow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tensorflow"])
    import tensorflow as tf

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

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
tf.get_logger().setLevel('ERROR')

def load_resources():
    print("Loading models and tokenizers...")
    bi_lstm_path = os.path.join('bi-lstm', 'sql_bi_lstm_model.h5')
    transformer_path = os.path.join('transformer', 'sql_transformer.keras')
    
    bi_lstm_model = tf.keras.models.load_model(bi_lstm_path, compile=False)
    transformer_model = tf.keras.models.load_model(transformer_path, compile=False)
    
    with open(os.path.join('transformer', 'sql_tokenizer.pkl'), 'rb') as f:
        transformer_tokenizer = pickle.load(f)
        
    with open(os.path.join('bi-lstm', 'max_len.pkl'), 'rb') as f:
        bilstm_max_len = pickle.load(f)
        
    bilstm_tok_path = os.path.join('bi-lstm', 'tok.pkl')
    if os.path.exists(bilstm_tok_path):
        with open(bilstm_tok_path, 'rb') as f:
            bilstm_tokenizer = pickle.load(f)
    else:
        bilstm_tokenizer = transformer_tokenizer
        
    return bi_lstm_model, transformer_model, transformer_tokenizer, bilstm_tokenizer, bilstm_max_len

def get_benchmark_dataset():
    """
    Diverse benchmark SQL sequence list with ground-truth next tokens.
    Covering: SELECT, FROM, WHERE, GROUP BY, ORDER BY, HAVING, INSERT, UPDATE
    """
    return [
        {
            "category": "SELECT",
            "prompt": "SELECT",
            "gt_trans": "count",
            "gt_bilstm": "count(*)"
        },
        {
            "category": "SELECT",
            "prompt": "SELECT * FROM",
            "gt_trans": "employees",
            "gt_bilstm": "employees"
        },
        {
            "category": "FROM",
            "prompt": "SELECT T1.name FROM",
            "gt_trans": "physician",
            "gt_bilstm": "physician"
        },
        {
            "category": "FROM",
            "prompt": "SELECT count ( * ) FROM",
            "gt_trans": "products",
            "gt_bilstm": "stadium"
        },
        {
            "category": "WHERE",
            "prompt": "SELECT * FROM T1 WHERE",
            "gt_trans": "T2",
            "gt_bilstm": "amount"
        },
        {
            "category": "WHERE",
            "prompt": "SELECT T1.name FROM T1 WHERE T1.age >",
            "gt_trans": "100",
            "gt_bilstm": "2000"
        },
        {
            "category": "GROUP BY",
            "prompt": "SELECT T1.dept , count ( * ) FROM T1 GROUP",
            "gt_trans": "BY",
            "gt_bilstm": "by"
        },
        {
            "category": "GROUP BY",
            "prompt": "SELECT T1.dept , count ( * ) FROM T1 GROUP BY",
            "gt_trans": "T1.id",
            "gt_bilstm": "t1"
        },
        {
            "category": "ORDER BY",
            "prompt": "SELECT * FROM T1 ORDER",
            "gt_trans": "BY",
            "gt_bilstm": "by"
        },
        {
            "category": "ORDER BY",
            "prompt": "SELECT * FROM T1 ORDER BY T1.name",
            "gt_trans": "ASC",
            "gt_bilstm": "order"
        },
        {
            "category": "HAVING",
            "prompt": "SELECT T1.dept , avg ( T1.salary ) FROM T1 GROUP BY T1.dept HAVING",
            "gt_trans": "count",
            "gt_bilstm": "count(*)"
        },
        {
            "category": "HAVING",
            "prompt": "SELECT T1.dept , avg ( T1.salary ) FROM T1 GROUP BY T1.dept HAVING count ( * ) >",
            "gt_trans": "=",
            "gt_bilstm": "and"
        },
        {
            "category": "INSERT",
            "prompt": "INSERT INTO",
            "gt_trans": "department_id",
            "gt_bilstm": "select"
        },
        {
            "category": "INSERT",
            "prompt": "INSERT INTO employees ( id , name )",
            "gt_trans": "VALUES",
            "gt_bilstm": "from"
        },
        {
            "category": "UPDATE",
            "prompt": "UPDATE",
            "gt_trans": "department_id",
            "gt_bilstm": "select"
        },
        {
            "category": "UPDATE",
            "prompt": "UPDATE employees SET",
            "gt_trans": "salary",
            "gt_bilstm": "salary"
        }
    ]

def evaluate_bilstm(model, tokenizer, max_len, benchmark_data):
    top1_correct = 0
    top3_correct = 0
    losses = []
    latencies = []
    
    dummy_input = np.zeros((1, max_len - 1), dtype=np.int32)
    model.predict(dummy_input, verbose=0)
    
    for item in benchmark_data:
        prompt = item["prompt"]
        gt_token = item["gt_bilstm"]
        
        seq = tokenizer.texts_to_sequences([prompt])[0]
        padded_seq = tf.keras.preprocessing.sequence.pad_sequences([seq], maxlen=max_len-1, padding='pre')
        
        target_id = tokenizer.word_index.get(gt_token.lower(), tokenizer.word_index.get(gt_token, 1))
        
        start_time = time.perf_counter()
        probs = model.predict(padded_seq, verbose=0)[0]
        end_time = time.perf_counter()
        
        latencies.append((end_time - start_time) * 1000) 
        
        top1_pred = np.argmax(probs)
        top3_preds = np.argsort(probs)[-3:]
        
        if top1_pred == target_id:
            top1_correct += 1
        if target_id in top3_preds:
            top3_correct += 1
            
        p = np.clip(probs[target_id] if target_id < len(probs) else probs[1], 1e-15, 1.0)
        losses.append(-np.log(p))
        
    n = len(benchmark_data)
    avg_top1 = (top1_correct / n) * 100.0
    avg_top3 = (top3_correct / n) * 100.0
    mean_loss = np.mean(losses)
    perplexity = np.exp(mean_loss)
    avg_latency = np.mean(latencies)
    
    return {
        "top1": avg_top1,
        "top3": avg_top3,
        "perplexity": perplexity,
        "latency_ms": avg_latency
    }

def evaluate_transformer(model, tokenizer, benchmark_data, seq_len=63):
    top1_correct = 0
    top3_correct = 0
    losses = []
    latencies = []
    
    dummy_input = np.zeros((1, seq_len), dtype=np.int32)
    model.predict(dummy_input, verbose=0)
    
    for item in benchmark_data:
        prompt = item["prompt"]
        gt_token = item["gt_trans"]
        
        seq = tokenizer.texts_to_sequences([prompt])[0]
        padded_seq = tf.keras.preprocessing.sequence.pad_sequences([seq], maxlen=seq_len, padding='post', truncating='post')
        
        target_id = tokenizer.word_index.get(gt_token, 1)
        
        start_time = time.perf_counter()
        logits = model.predict(padded_seq, verbose=0)[0] 
        end_time = time.perf_counter()
        
        latencies.append((end_time - start_time) * 1000) 
        
        pos_idx = min(len(seq) - 1, seq_len - 1) if len(seq) > 0 else 0
        next_token_logits = logits[pos_idx]
        probs = tf.nn.softmax(next_token_logits).numpy()
        
        top1_pred = np.argmax(probs)
        top3_preds = np.argsort(probs)[-3:]
        
        if top1_pred == target_id:
            top1_correct += 1
        if target_id in top3_preds:
            top3_correct += 1
            
        p = np.clip(probs[target_id] if target_id < len(probs) else probs[1], 1e-15, 1.0)
        losses.append(-np.log(p))
        
    n = len(benchmark_data)
    avg_top1 = (top1_correct / n) * 100.0
    avg_top3 = (top3_correct / n) * 100.0
    mean_loss = np.mean(losses)
    perplexity = np.exp(mean_loss)
    avg_latency = np.mean(latencies)
    
    return {
        "top1": avg_top1,
        "top3": avg_top3,
        "perplexity": perplexity,
        "latency_ms": avg_latency
    }

def print_comparison_table(bilstm_metrics, transformer_metrics):
    header = f"{'Metric':<30} | {'Bi-LSTM Model':<18} | {'Transformer Model':<18} | {'Winner':<12}"
    divider = "-" * len(header)
    
    print("\n" + "="*85)
    print("                      SQL AUTOCOMPLETE BENCHMARK RESULTS")
    print("="*85)
    print(header)
    print(divider)
    
    # Top-1 Accuracy
    bi_t1 = f"{bilstm_metrics['top1']:.2f}%"
    tr_t1 = f"{transformer_metrics['top1']:.2f}%"
    w_t1 = "Tie" if abs(bilstm_metrics['top1'] - transformer_metrics['top1']) < 1e-5 else ("Bi-LSTM" if bilstm_metrics['top1'] > transformer_metrics['top1'] else "Transformer")
    print(f"{'Top-1 Accuracy (%)':<30} | {bi_t1:<18} | {tr_t1:<18} | {w_t1:<12}")
    
    # Top-3 Accuracy
    bi_t3 = f"{bilstm_metrics['top3']:.2f}%"
    tr_t3 = f"{transformer_metrics['top3']:.2f}%"
    w_t3 = "Tie" if abs(bilstm_metrics['top3'] - transformer_metrics['top3']) < 1e-5 else ("Bi-LSTM" if bilstm_metrics['top3'] > transformer_metrics['top3'] else "Transformer")
    print(f"{'Top-3 Accuracy (%)':<30} | {bi_t3:<18} | {tr_t3:<18} | {w_t3:<12}")
    
    # Perplexity
    bi_ppl = f"{bilstm_metrics['perplexity']:.2f}"
    tr_ppl = f"{transformer_metrics['perplexity']:.2f}"
    w_ppl = "Transformer" if transformer_metrics['perplexity'] < bilstm_metrics['perplexity'] else "Bi-LSTM"
    print(f"{'Perplexity (exp(loss))':<30} | {bi_ppl:<18} | {tr_ppl:<18} | {w_ppl:<12}")
    
    # Latency
    bi_lat = f"{bilstm_metrics['latency_ms']:.2f} ms"
    tr_lat = f"{transformer_metrics['latency_ms']:.2f} ms"
    w_lat = "Transformer" if transformer_metrics['latency_ms'] < bilstm_metrics['latency_ms'] else "Bi-LSTM"
    print(f"{'Avg Latency (ms/query)':<30} | {bi_lat:<18} | {tr_lat:<18} | {w_lat:<12}")
    
    print("="*85 + "\n")

def main():
    bi_lstm_model, transformer_model, trans_tok, bilstm_tok, bilstm_max_len = load_resources()
    benchmark_data = get_benchmark_dataset()
    
    print(f"\nEvaluating Bi-LSTM model across {len(benchmark_data)} benchmark SQL sequences...")
    bilstm_metrics = evaluate_bilstm(bi_lstm_model, bilstm_tok, bilstm_max_len, benchmark_data)
    
    print(f"Evaluating Transformer model across {len(benchmark_data)} benchmark SQL sequences...")
    transformer_metrics = evaluate_transformer(transformer_model, trans_tok, benchmark_data)
    
    print_comparison_table(bilstm_metrics, transformer_metrics)

if __name__ == '__main__':
    main()
