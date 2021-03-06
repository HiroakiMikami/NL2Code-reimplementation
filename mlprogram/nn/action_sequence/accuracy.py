import torch
import torch.nn as nn

from mlprogram.nn.utils.rnn import PaddedSequenceWithMask


class Accuracy(nn.Module):
    def __init__(self):
        super(Accuracy, self).__init__()

    def forward(self,
                rule_probs: PaddedSequenceWithMask,
                token_probs: PaddedSequenceWithMask,
                reference_probs: PaddedSequenceWithMask,
                ground_truth_actions: PaddedSequenceWithMask
                ) -> torch.Tensor:
        """
        Parameters
        ----------
        rule_probs: PaddedSequenceWithMask
            The probabilities of apply-rule. The shape is (L_a, B, num_rules).
        token_probs: PaddedSequenceWithMask
            The probabilities of gen-token. The shape is (L_a, B, num_tokens).
        reference_probs: PaddedSequenceWithMask
            The probabilities of reference-token. The shape is
            (L_a, B, reference_length).
        ground_truth_actions: PaddedSequenceWithMask
            The input sequence of action. Each action is represented by
            the tuple of (ID of the applied rule, ID of the inserted token,
            the index of the word copied from the reference).
            The padding value should be -1.
        """
        L_a, B, num_rules = rule_probs.data.shape
        _, _, num_tokens = token_probs.data.shape
        _, _, reference_length = reference_probs.data.shape

        gt_rule, gt_token, gt_reference = torch.split(
            ground_truth_actions.data, 1, dim=2)  # (L_a, B, 1)
        gt_rule = gt_rule.reshape([L_a, B])  # (L_a, B)
        gt_token = gt_token.reshape([L_a, B])  # (L_a, B)
        gt_reference = gt_reference.reshape([L_a, B])  # (L_a, B)

        _, rule_pred = torch.max(rule_probs.data, 2)  # (L_a, B)
        _, token_pred = torch.max(token_probs.data, 2)  # (L_a, B)
        if reference_probs.data.shape[2] == 0:
            reference_pred = \
                torch.zeros(L_a, B).to(gt_reference.device)
        else:
            _, reference_pred = torch.max(reference_probs.data, 2)  # (L_a, B)

        n_rule = (gt_rule != -1).long().sum()
        n_token = (gt_token != -1).long().sum()
        n_reference = (gt_reference != -1).long().sum()
        rule_acc = ((rule_pred == gt_rule) * (gt_rule != -1).long()).sum()
        token_acc = ((token_pred == gt_token) * (gt_token != -1).long()).sum()
        reference_acc = \
            ((reference_pred == gt_reference) *
             (gt_reference != -1).long()).sum()

        acc = rule_acc + token_acc + reference_acc
        return acc.to(rule_probs.data.dtype) / (n_rule + n_token + n_reference)
