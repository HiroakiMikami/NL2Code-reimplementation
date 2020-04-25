import torch
import numpy as np
from torchnlp.encoders import LabelEncoder
from typing import Callable, List, TypeVar, Generic, Optional, Tuple
from nl2prog.language.evaluator import Evaluator
from nl2prog.encoders import ActionSequenceEncoder
from nl2prog.utils import Query


Input = TypeVar("Input")


class TransformQuery(Generic[Input]):
    def __init__(self, extract_query: Callable[[Input], Query],
                 word_encoder: LabelEncoder):
        self.extract_query = extract_query
        self.word_encoder = word_encoder

    def __call__(self, input: Input) -> Tuple[List[str], torch.Tensor]:
        query = self.extract_query(input)

        return query.query_for_synth, \
            self.word_encoder.batch_encode(query.query_for_dnn)


class TransformEvaluator:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder,
                 train: bool = True):
        self.action_sequence_encoder = action_sequence_encoder
        self.train = train

    def __call__(self, evaluator: Evaluator, query_for_synth: List[str]) \
            -> Optional[Tuple[Tuple[torch.Tensor, torch.Tensor], None]]:
        a = self.action_sequence_encoder.encode_action(evaluator,
                                                       query_for_synth)
        p = self.action_sequence_encoder.encode_parent(evaluator)
        if a is None:
            return None
        if self.train:
            if np.any(a[-1, :].numpy() != -1):
                return None
            action_tensor = torch.cat(
                [a[1:-1, 0].view(-1, 1), p[1:-1, 1:3].view(-1, 2)],
                dim=1)
            prev_action = a[:-2, 1:]
        else:
            action_tensor = torch.cat(
                [a[-1, 0].view(1, -1), p[-1, 1:3].view(1, -1)], dim=1)
            prev_action = a[-2, 1:].view(1, -1)

        return (action_tensor, prev_action), None
