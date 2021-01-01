imports = ["../nl2prog_baseline/base.py", "base.py"]

params = {
    "word_threshold": 3,
    "token_threshold": 0,
    "node_type_embedding_size": 64,
    "embedding_size": 128,
    "hidden_size": 256,
    "attr_hidden_size": 50,
    "dropout": 0.2,
    "batch_size": 1,
    "n_epoch": 50,
    "eval_interval": 10,
    "snapshot_interval": 1,
    "beam_size": 15,
    "max_step_size": 350,
    "metric_top_n": [1],
    "metric_threshold": 1.0,
    "metric": "bleu@1",
    "n_evaluate_process": 2,
}
