import torch
import numpy as np

from mlprogram.utils.data import ListDataset
from mlprogram.encoders import ActionSequenceEncoder
from mlprogram.actions import ActionSequence
from typing import List, Callable, Tuple, Any, Optional


class TransformCode:
    def __init__(self,
                 to_action_sequence: Callable[[Any],
                                              Optional[ActionSequence]]):
        self.to_action_sequence = to_action_sequence

    def __call__(self, code: Any) -> Optional[ActionSequence]:
        return self.to_action_sequence(code)


class TransformGroundTruth:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder):

        self.action_sequence_encoder = action_sequence_encoder

    def __call__(self, evaluator: ActionSequence, query_for_synth: List[str]) \
            -> Optional[torch.Tensor]:
        a = self.action_sequence_encoder.encode_action(evaluator,
                                                       query_for_synth)
        if a is None:
            return None
        if np.any(a[-1, :].numpy() != -1):
            return None
        ground_truth = a[1:-1, 1:]
        return ground_truth


class TransformDataset:
    def __init__(self,
                 transform_input: Callable[[Any], Tuple[List[str], Any]],
                 transform_code: Callable[[Any], Optional[ActionSequence]],
                 transform_evaluator: Callable[[ActionSequence, List[str]],
                                               Optional[Any]],
                 transform_ground_truth: Callable[[ActionSequence, List[str]],
                                                  Optional[torch.Tensor]]):
        self.transform_input = transform_input
        self.transform_code = transform_code
        self.transform_evaluator = transform_evaluator
        self.transform_ground_truth = transform_ground_truth

    def __call__(self, dataset: torch.utils.data.Dataset) \
            -> torch.utils.data.Dataset:
        entries = []
        for group in dataset:
            for entry in group:
                query_for_synth, input_tensor = \
                    self.transform_input(entry.input)
                evaluator = self.transform_code(entry.ground_truth)
                if evaluator is None:
                    continue
                tmp = self.transform_evaluator(
                    evaluator, query_for_synth)
                ground_truth = self.transform_ground_truth(
                    evaluator, query_for_synth)
                if ground_truth is None or tmp is None:
                    continue
                action_sequence, query = tmp
                entries.append((input_tensor, action_sequence, query,
                                ground_truth))
        return ListDataset(entries)
