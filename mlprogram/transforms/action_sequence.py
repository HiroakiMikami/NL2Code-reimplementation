from typing import Generic, List, Optional, TypeVar, cast

import numpy as np
import torch

from mlprogram.actions import ActionSequence
from mlprogram.builtins import Environment
from mlprogram.encoders import ActionSequenceEncoder
from mlprogram.languages import Parser, Token

Code = TypeVar("Code")


class AddEmptyReference(object):
    def __call__(self, entry: Environment) -> Optional[Environment]:
        entry["reference"] = []
        entry["reference_features"] = torch.zeros((0, 1))
        return entry


class GroundTruthToActionSequence(Generic[Code]):
    def __init__(self, parser: Parser[Code]):
        self.parser = parser

    def __call__(self, entry: Environment) -> Optional[Environment]:
        code = cast(Code, entry["ground_truth"])
        ast = self.parser.parse(code)
        if ast is None:
            return None
        seq = ActionSequence.create(ast)
        entry["action_sequence"] = seq
        entry.mark_as_supervision("action_sequence")
        return entry


class EncodeActionSequence:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder):

        self.action_sequence_encoder = action_sequence_encoder

    def __call__(self, entry: Environment) -> Optional[Environment]:
        action_sequence = cast(ActionSequence,
                               entry["action_sequence"])
        reference = cast(List[Token[str, str]], entry["reference"])
        a = self.action_sequence_encoder.encode_action(
            action_sequence, reference)
        if a is None:
            return None
        if np.any(a[-1, :].numpy() != -1):
            return None
        ground_truth = a[1:-1, 1:]
        entry["ground_truth_actions"] = ground_truth
        entry.mark_as_supervision("ground_truth_actions")
        return entry


class AddPreviousActions:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder,
                 n_dependent: Optional[int] = None):
        self.action_sequence_encoder = action_sequence_encoder
        self.n_dependent = n_dependent

    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        else:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        reference = cast(List[Token[str, str]], entry["reference"])
        a = self.action_sequence_encoder.encode_action(
            action_sequence, reference)
        if a is None:
            return None
        if train:
            if np.any(a[-1, :].numpy() != -1):
                return None
            prev_action = a[:-2, 1:]
        else:
            prev_action = a[:-1, 1:]
            if self.n_dependent is not None:
                prev_action = prev_action[-self.n_dependent:, :]

        entry["previous_actions"] = prev_action

        return entry


class AddActions:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder,
                 n_dependent: Optional[int] = None):
        self.action_sequence_encoder = action_sequence_encoder
        self.n_dependent = n_dependent

    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        else:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        reference = cast(List[Token[str, str]], entry["reference"])
        a = self.action_sequence_encoder.encode_action(
            action_sequence, reference)
        p = self.action_sequence_encoder.encode_parent(action_sequence)
        if a is None:
            return None
        if train:
            if np.any(a[-1, :].numpy() != -1):
                return None
            action_tensor = torch.cat(
                [a[1:-1, 0].view(-1, 1), p[1:-1, 1:3].view(-1, 2)],
                dim=1)
        else:
            action_tensor = torch.cat(
                [a[1:, 0].view(-1, 1), p[1:, 1:3].view(-1, 2)], dim=1)
            if self.n_dependent is not None:
                action_tensor = action_tensor[-self.n_dependent:, :]

        entry["actions"] = action_tensor

        return entry


class AddPreviousActionRules:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder,
                 max_arity: int,
                 n_dependent: Optional[int] = None):
        self.action_sequence_encoder = action_sequence_encoder
        self.max_arity = max_arity
        self.n_dependent = n_dependent

    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        else:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        reference = cast(List[Token[str, str]], entry["reference"])
        rule_prev_action = \
            self.action_sequence_encoder.encode_each_action(
                action_sequence, reference, self.max_arity)
        if train:
            rule_prev_action = rule_prev_action[:-1]
        else:
            if self.n_dependent is not None:
                rule_prev_action = rule_prev_action[-self.n_dependent:, :]

        entry["previous_action_rules"] = rule_prev_action
        return entry


class AddActionSequenceAsTree:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder):
        self.action_sequence_encoder = action_sequence_encoder

    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        else:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        depth, matrix = self.action_sequence_encoder.encode_tree(
            action_sequence)
        if train:
            depth = depth[:-1]
            matrix = matrix[:-1, :-1]

        entry["adjacency_matrix"] = matrix
        entry["depthes"] = depth

        return entry


class AddQueryForTreeGenDecoder:
    def __init__(self,
                 action_sequence_encoder: ActionSequenceEncoder,
                 max_depth: int,
                 n_dependent: Optional[int] = None):
        self.action_sequence_encoder = action_sequence_encoder
        self.max_depth = max_depth
        self.n_dependent = n_dependent

    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        else:
            action_sequence = cast(ActionSequence,
                                   entry["action_sequence"])
        query = \
            self.action_sequence_encoder.encode_path(
                action_sequence, self.max_depth)
        if train:
            query = query[:-1, :]
        else:
            if self.n_dependent:
                query = query[-self.n_dependent:, :]

        entry["action_queries"] = query

        return entry


class AddStateForRnnDecoder:
    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train or "hidden_state" not in entry:
            entry["hidden_state"] = None
        if train or "state" not in entry:
            entry["state"] = None

        return entry


class AddHistoryState:
    def __call__(self, entry: Environment) -> Optional[Environment]:
        train = entry.is_supervision("action_sequence")
        if train or "history" not in entry:
            entry["history"] = None

        return entry
