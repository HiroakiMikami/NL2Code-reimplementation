import torch
import numpy as np
from typing import Callable, List, Any, Tuple, Union
from nl2prog.language.action import ActionSequence
from nl2prog.language.evaluator import Evaluator
from nl2prog.encoders import Encoder
from nl2prog.utils.data import ListDataset
from nl2prog.utils import Query


def to_train_dataset(dataset: torch.utils.data.Dataset,
                     tokenize_query: Callable[[str], Query],
                     tokenize_token: Callable[[str], List[str]],
                     to_action_sequence: Callable[[Any],
                                                  Union[ActionSequence, None]],
                     encoder: Encoder) \
        -> torch.utils.data.Dataset:
    entries = []
    for group in dataset:
        for entry in group:
            annotation = entry.query
            code = entry.ground_truth
            query = tokenize_query(annotation)
            query_tensor = \
                encoder.annotation_encoder.batch_encode(query.query_for_dnn)
            action_sequence = to_action_sequence(code)
            if action_sequence is None:
                continue
            evaluator = Evaluator()
            for action in action_sequence:
                evaluator.eval(action)
            a = \
                encoder.action_sequence_encoder.encode_action(
                    evaluator, query.query_for_synth)
            p = \
                encoder.action_sequence_encoder.encode_parent(
                    evaluator)
            if a is None:
                continue
            if np.any(a[-1, :].numpy() != -1):
                continue
            action_tensor = torch.cat(
                [a[:-1, 0].view(-1, 1), p[:-1, 1:3].view(-1, 2)],
                dim=1)
            dummy = torch.ones([1, 3]).to(a.dtype).to(a.device)
            prev_action = torch.cat([dummy, a[:-1, 1:]], dim=0)
            entries.append((query_tensor, action_tensor, prev_action))
    return ListDataset(entries)


def collate_train_dataset(data: List[Tuple[torch.LongTensor, torch.LongTensor,
                                           torch.LongTensor]]) \
    -> Tuple[List[torch.LongTensor], List[torch.LongTensor],
             List[torch.LongTensor]]:
    xs = []
    ys = []
    zs = []
    for x, y, z in data:
        xs.append(x)
        ys.append(y)
        zs.append(z)
    return xs, ys, zs
