imports = ["../nl2code/base.py"]
params = {
    "word_threshold": 5,
    "token_threshold": 5,
    "node_type_embedding_size": 64,
    "embedding_size": 128,
    "hidden_size": 256,
    "attr_hidden_size": 50,
    "dropout": 0.2,
    "batch_size": 10,
    "n_epoch": 50,
    "eval_interval": 10,
    "snapshot_interval": 1,
    "beam_size": 15,
    "max_step_size": 100,
    "metric_top_n": [1],
    "metric_threshold": 1.0,
    "metric": "bleu@1",
    "n_evaluate_process": 2,
}
parser = mlprogram.datasets.django.Parser(
    split_value=mlprogram.datasets.django.SplitValue(),
)
extract_reference = mlprogram.datasets.django.TokenizeQuery()
is_subtype = mlprogram.languages.python.IsSubtype()
dataset = mlprogram.datasets.django.download()
metrics = {
    "accuracy": mlprogram.metrics.Accuracy(),
    "bleu": mlprogram.languages.python.metrics.Bleu(),
}
