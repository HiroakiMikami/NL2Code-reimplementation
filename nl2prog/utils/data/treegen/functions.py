import torch
from torchnlp.encoders import LabelEncoder
import numpy as np
from typing import Callable, List, Any, Union, Optional
from nl2prog.language.action import ActionSequence, ActionOptions
from nl2prog.language.evaluator import Evaluator
from nl2prog.encoders import ActionSequenceEncoder
from nl2prog.utils.data import ListDataset
from nl2prog.utils import Query


def to_train_dataset(dataset: torch.utils.data.Dataset,
                     tokenize_query: Callable[[str], Query],
                     tokenize_token: Optional[Callable[[str], List[str]]],
                     to_action_sequence: Callable[[Any],
                                                  Union[ActionSequence, None]],
                     query_encoder: LabelEncoder, char_encoder: LabelEncoder,
                     action_sequence_encoder: ActionSequenceEncoder,
                     max_word_length: int, max_arity: int,
                     options: ActionOptions = ActionOptions(False, False)) \
        -> torch.utils.data.Dataset:
    entries = []
    for group in dataset:
        for entry in group:
            query = entry.query
            code = entry.ground_truth
            query = tokenize_query(query)
            word_query = \
                query_encoder.batch_encode(query.query_for_dnn)
            char_query = \
                torch.ones(len(query.query_for_dnn), max_word_length) * -1
            for i, word in enumerate(query.query_for_dnn):
                char_query[i, :] = \
                    char_encoder.batch_encode(word)[:max_word_length]

            action_sequence = to_action_sequence(code)
            if action_sequence is None:
                continue
            evaluator = Evaluator(options=options)
            for action in action_sequence:
                evaluator.eval(action)

            a = \
                action_sequence_encoder.encode_action(evaluator,
                                                      query.query_for_synth)
            if a is None:
                continue
            if np.any(a[-1, :].numpy() != -1):
                continue
            dummy = torch.ones([1, 3]).to(a.dtype).to(a.device) * -1
            prev_action = torch.cat([dummy, a[:-2, 1:]], dim=0)

            ground_truth = a[:-1, 1:]

            rule_prev_action = \
                action_sequence_encoder.encode_each_action(
                    evaluator, query.query_for_synth, max_arity)
            dummy = \
                torch.ones([1, max_arity + 1, 3])\
                .to(rule_prev_action.dtype)\
                .to(rule_prev_action.device) * -1
            rule_prev_action = torch.cat([dummy, rule_prev_action[:-1]], dim=0)

            depth, matrix = action_sequence_encoder.encode_tree(evaluator)
            dummy = torch.zeros(1, 1, dtype=depth.dtype, device=depth.device)
            depth = torch.cat([dummy, depth[:-1] + 1], dim=0)

            matrix = matrix[:-1, :-1]
            matrix = torch.nn.functional.pad(matrix, (1, 0, 1, 0))

            entries.append(((word_query, char_query, prev_action,
                             rule_prev_action, depth, matrix), ground_truth))
    return ListDataset(entries)


def collate_train_dataset(data):
    trains = []
    gts = []
    n_train_tensor = len(data[0][0])
    for _ in range(n_train_tensor):
        trains.append([])
    for train, gt in data:
        for i, t in enumerate(train):
            trains[i].append(t)
        gts.append(gt)
    return tuple(trains), gts
