import torch
import numpy as np
from typing import Callable, List, Any, Optional, Dict, TypeVar, Generic, cast
from torchnlp.encoders import LabelEncoder

from mlprogram.actions import ActionSequence
from mlprogram.encoders import ActionSequenceEncoder
from mlprogram.utils import Query
from mlprogram.languages import Token


Input = TypeVar("Input")


class TransformQuery(Generic[Input]):
    def __init__(self, extract_query: Callable[[Input], Query],
                 word_encoder: LabelEncoder, char_encoder: LabelEncoder,
                 max_word_length: int):
        self.extract_query = extract_query
        self.word_encoder = word_encoder
        self.char_encoder = char_encoder
        self.max_word_length = max_word_length

    def __call__(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        input = cast(Input, entry["input"])
        query = self.extract_query(input)

        word_query = self.word_encoder.batch_encode(query.query_for_dnn)
        char_query = \
            torch.ones(len(query.query_for_dnn), self.max_word_length).long() \
            * -1
        for i, word in enumerate(query.query_for_dnn):
            chars = self.char_encoder.batch_encode(word)
            length = min(self.max_word_length, len(chars))
            char_query[i, :length] = \
                self.char_encoder.batch_encode(word)[:length]
        entry["reference"] = query.reference
        entry["word_nl_query"] = word_query
        entry["char_nl_query"] = char_query

        return entry


class TransformActionSequence:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder,
                 max_arity: int, max_depth: int, train: bool = True):
        self.action_sequence_encoder = action_sequence_encoder
        self.max_arity = max_arity
        self.max_depth = max_depth
        self.train = train

    def __call__(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        action_sequence = cast(ActionSequence, entry["action_sequence"])
        reference = cast(List[Token[str, str]], entry["reference"])
        refs = list(map(lambda x: x.value, reference))
        # TODO use type in encoding action sequence
        a = self.action_sequence_encoder.encode_action(
            action_sequence, refs)
        rule_prev_action = \
            self.action_sequence_encoder.encode_each_action(
                action_sequence, refs, self.max_arity)
        path = \
            self.action_sequence_encoder.encode_path(
                action_sequence, self.max_depth)
        depth, matrix = self.action_sequence_encoder.encode_tree(
            action_sequence)
        if a is None:
            return None
        if self.train:
            if np.any(a[-1, :].numpy() != -1):
                return None
            prev_action = a[:-2, 1:]
            query = path[:-1, :]
            rule_prev_action = rule_prev_action[:-1]
            depth = depth[:-1]
            matrix = matrix[:-1, :-1]
        else:
            prev_action = a[:-1, 1:]
            query = path
            rule_prev_action = \
                self.action_sequence_encoder.encode_each_action(
                    action_sequence, refs, self.max_arity)

        entry["previous_actions"] = prev_action
        entry["previous_action_rules"] = rule_prev_action
        entry["depthes"] = depth
        entry["adjacency_matrix"] = matrix
        entry["action_queries"] = query

        return entry
