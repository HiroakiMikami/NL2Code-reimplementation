import logging
import os
import random
import sys
import tempfile
from collections import OrderedDict

import numpy as np
import torch
import torch.optim as optim

import mlprogram.nn
import mlprogram.nn.action_sequence as a_s
import mlprogram.samplers
from mlprogram import metrics
from mlprogram.builtins import Div, Flatten, Mul, Pick, Threshold
from mlprogram.encoders import ActionSequenceEncoder
from mlprogram.entrypoint import EvaluateSynthesizer
from mlprogram.entrypoint import evaluate as eval
from mlprogram.entrypoint import train_REINFORCE, train_supervised
from mlprogram.entrypoint.modules.torch import Optimizer, Reshape
from mlprogram.entrypoint.train import Epoch
from mlprogram.functools import Compose, Map, Sequence
from mlprogram.languages.csg import (
    Dataset,
    Expander,
    Interpreter,
    IsSubtype,
    Parser,
    get_samples,
)
from mlprogram.languages.csg.transform import AddTestCases, TransformCanvas
from mlprogram.nn import MLP, AggregatedLoss, Apply, CNN2d
from mlprogram.nn.action_sequence import Loss
from mlprogram.nn.pbe_with_repl import Encoder
from mlprogram.samplers import (
    ActionSequenceSampler,
    FilteredSampler,
    SamplerWithValueNetwork,
    SequentialProgramSampler,
)
from mlprogram.synthesizers import SMC, FilteredSynthesizer, SynthesizerWithTimeout
from mlprogram.utils.data import Collate, CollateOptions, to_map_style_dataset
from mlprogram.utils.data import transform as data_transform
from mlprogram.utils.transform.action_sequence import (
    AddPreviousActions,
    AddStateForRnnDecoder,
    EncodeActionSequence,
    GroundTruthToActionSequence,
)
from mlprogram.utils.transform.pbe import ToEpisode

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)


class TestCsgByPbeWithREPL(object):
    def prepare_encoder(self, dataset, parser):
        return ActionSequenceEncoder(get_samples(dataset, parser),
                                     0)

    def prepare_model(self, encoder: ActionSequenceEncoder):
        return torch.nn.Sequential(OrderedDict([
            ("encode_input",
             Apply([("state@test_case_tensor", "x")],
                   "state@test_case_feature",
                   CNN2d(1, 16, 32, 2, 2, 2))),
            ("encoder",
             Encoder(CNN2d(2, 16, 32, 2, 2, 2))),
            ("decoder",
             torch.nn.Sequential(OrderedDict([
                 ("action_sequence_reader",
                  a_s.ActionSequenceReader(encoder._rule_encoder.vocab_size,
                                           encoder._token_encoder.vocab_size,
                                           256)),
                 ("decoder",
                  a_s.RnnDecoder(2 * 16 * 8 * 8, 256, 512, 0.0)),
                 ("predictor",
                  a_s.Predictor(512, 16 * 8 * 8,
                                encoder._rule_encoder.vocab_size,
                                encoder._token_encoder.vocab_size,
                                512))
             ]))),
            ("value",
             Apply([("state@input_feature", "x")], "state@value",
                   MLP(16 * 8 * 8 * 2, 1, 512, 2,
                       activation=torch.nn.Sigmoid()),
                   value_type="tensor"))
        ]))

    def prepare_optimizer(self, model):
        return Optimizer(optim.Adam, model)

    def prepare_synthesizer(self, model, encoder, interpreter, rollout=True):
        collate = Collate(
            torch.device("cpu"),
            test_case_tensor=CollateOptions(False, 0, 0),
            input_feature=CollateOptions(False, 0, 0),
            test_case_feature=CollateOptions(False, 0, 0),
            reference_features=CollateOptions(True, 0, 0),
            variables_tensor=CollateOptions(True, 0, 0),
            previous_actions=CollateOptions(True, 0, -1),
            hidden_state=CollateOptions(False, 0, 0),
            state=CollateOptions(False, 0, 0),
            ground_truth_actions=CollateOptions(True, 0, -1)
        )
        subsampler = ActionSequenceSampler(
            encoder, IsSubtype(),
            Compose(OrderedDict([
                ("tcanvas", TransformCanvas())
            ])),
            Compose(OrderedDict([
                ("add_previous_actions",
                 AddPreviousActions(encoder, n_dependent=1)),
                ("add_state",
                 AddStateForRnnDecoder())
            ])),
            collate, model,
            rng=np.random.RandomState(0))
        subsampler = mlprogram.samplers.transform(
            subsampler,
            Parser().unparse
        )
        subsynthesizer = SMC(
            5, 1,
            subsampler,
            max_try_num=1,
            to_key=Pick("state@action_sequence"),
            rng=np.random.RandomState(0)
        )

        sampler = SequentialProgramSampler(
            subsynthesizer,
            TransformCanvas(),
            collate,
            model.encode_input,
            interpreter=interpreter,
            expander=Expander(),
            rng=np.random.RandomState(0))
        if rollout:
            sampler = FilteredSampler(
                sampler,
                metrics.TestCaseResult(interpreter, metric=metrics.Iou()),
                0.9
            )
            return SMC(4, 20, sampler, rng=np.random.RandomState(0),
                       to_key=Pick("state@interpreter_state"), max_try_num=1)
        else:
            sampler = SamplerWithValueNetwork(
                sampler,
                Compose(OrderedDict([
                    ("tcanvas", TransformCanvas())
                ])),
                collate,
                torch.nn.Sequential(OrderedDict([
                    ("encoder", model.encoder),
                    ("value", model.value),
                    ("pick",
                     mlprogram.nn.Function(
                         Pick("state@value")))
                ])))

            synthesizer = SynthesizerWithTimeout(
                SMC(4, 20, sampler, rng=np.random.RandomState(0),
                    to_key=Pick("state@interpreter_state")),
                1
            )
            return FilteredSynthesizer(
                synthesizer,
                metrics.TestCaseResult(interpreter, metric=metrics.Iou()),
                0.9
            )

    def interpreter(self):
        return Interpreter(2, 2, 8, delete_used_reference=True)

    def to_episode(self, encoder, interpreter):
        return ToEpisode(interpreter, Expander())

    def transform(self, encoder, interpreter, parser):
        tcanvas = TransformCanvas()
        tcode = GroundTruthToActionSequence(parser)
        aaction = AddPreviousActions(encoder, n_dependent=1)
        astate = AddStateForRnnDecoder()
        tgt = EncodeActionSequence(encoder)
        return Sequence(
            OrderedDict([
                ("tcanvas", tcanvas),
                ("tcode", tcode),
                ("aaction", aaction),
                ("astate", astate),
                ("tgt", tgt)
            ])
        )

    def evaluate(self, dataset, encoder, dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = self.interpreter()
            model = self.prepare_model(encoder)
            eval(
                dir, tmpdir, dir,
                dataset,
                model,
                self.prepare_synthesizer(model, encoder, interpreter,
                                         rollout=False),
                {}, top_n=[],
            )
        return torch.load(os.path.join(dir, "result.pt"))

    def pretrain(self, output_dir):
        dataset = Dataset(2, 1, 2, 1, 45, reference=True, seed=1)
        train_dataset = to_map_style_dataset(dataset, 10)

        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = self.interpreter()
            train_dataset = data_transform(
                train_dataset,
                AddTestCases(interpreter))
            encoder = self.prepare_encoder(dataset, Parser())

            collate = Collate(
                torch.device("cpu"),
                test_case_tensor=CollateOptions(False, 0, 0),
                variables_tensor=CollateOptions(True, 0, 0),
                previous_actions=CollateOptions(True, 0, -1),
                hidden_state=CollateOptions(False, 0, 0),
                state=CollateOptions(False, 0, 0),
                ground_truth_actions=CollateOptions(True, 0, -1)
            )
            collate_fn = Sequence(OrderedDict([
                ("to_episode", Map(self.to_episode(encoder,
                                                   interpreter))),
                ("flatten", Flatten()),
                ("transform", Map(self.transform(
                    encoder, interpreter, Parser()))),
                ("collate", collate.collate)
            ]))

            model = self.prepare_model(encoder)
            optimizer = self.prepare_optimizer(model)
            train_supervised(
                tmpdir, output_dir,
                train_dataset, model, optimizer,
                torch.nn.Sequential(OrderedDict([
                    ("loss", Loss(reduction="sum")),
                    ("normalize",  # divided by batch_size
                     Apply(
                         [("output@action_sequence_loss", "lhs")],
                         "output@loss",
                         mlprogram.nn.Function(Div()),
                         constants={"rhs": 1})),
                    ("pick",
                     mlprogram.nn.Function(
                         Pick("output@loss")))
                ])),
                None, "score",
                collate_fn,
                1, Epoch(100), evaluation_interval=Epoch(10),
                snapshot_interval=Epoch(100)
            )
        return encoder, train_dataset

    def reinforce(self, train_dataset, encoder, output_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = self.interpreter()

            collate = Collate(
                torch.device("cpu"),
                test_case_tensor=CollateOptions(False, 0, 0),
                variables_tensor=CollateOptions(True, 0, 0),
                previous_actions=CollateOptions(True, 0, -1),
                hidden_state=CollateOptions(False, 0, 0),
                state=CollateOptions(False, 0, 0),
                ground_truth_actions=CollateOptions(True, 0, -1),
                reward=CollateOptions(False, 0, 0)
            )
            collate_fn = Sequence(OrderedDict([
                ("to_episode", Map(self.to_episode(encoder,
                                                   interpreter))),
                ("flatten", Flatten()),
                ("transform", Map(self.transform(
                    encoder, interpreter, Parser()))),
                ("collate", collate.collate)
            ]))

            model = self.prepare_model(encoder)
            optimizer = self.prepare_optimizer(model)
            train_REINFORCE(
                output_dir, tmpdir, output_dir,
                train_dataset,
                self.prepare_synthesizer(model, encoder, interpreter),
                model, optimizer,
                torch.nn.Sequential(OrderedDict([
                    ("policy",
                     torch.nn.Sequential(OrderedDict([
                         ("loss", Loss(reduction="none")),
                         ("weight_by_reward",
                             Apply(
                                 [("input@reward", "lhs"),
                                  ("output@action_sequence_loss", "rhs")],
                                 "output@action_sequence_loss",
                                 mlprogram.nn.Function(Mul())))
                     ]))),
                    ("value",
                     torch.nn.Sequential(OrderedDict([
                         ("reshape_reward",
                             Apply(
                                 [("input@reward", "x")],
                                 "state@value_loss_target",
                                 Reshape([-1, 1]))),
                         ("BCE",
                             Apply(
                                 [("state@value", "input"),
                                  ("state@value_loss_target", "target")],
                                 "output@value_loss",
                                 torch.nn.BCELoss(reduction='sum')))
                     ]))),
                    ("reweight",
                     Apply(
                         [("output@value_loss", "lhs")],
                         "output@value_loss",
                         mlprogram.nn.Function(Mul()),
                         constants={"rhs": 1e-2})),
                    ("aggregate",
                     Apply(
                         ["output@action_sequence_loss", "output@value_loss"],
                         "output@loss",
                         AggregatedLoss())),
                    ("normalize",
                     Apply(
                         [("output@loss", "lhs")],
                         "output@loss",
                         mlprogram.nn.Function(Div()),
                         constants={"rhs": 1})),
                    ("pick",
                     mlprogram.nn.Function(
                         Pick("output@loss")))
                ])),
                EvaluateSynthesizer(
                    train_dataset,
                    self.prepare_synthesizer(model, encoder, interpreter,
                                             rollout=False),
                    {}, top_n=[]),
                "generation_rate",
                metrics.transform(
                    metrics.TestCaseResult(interpreter, metric=metrics.Iou()),
                    Threshold(0.9, dtype="float")),
                collate_fn,
                1, 1,
                Epoch(10), evaluation_interval=Epoch(10),
                snapshot_interval=Epoch(10),
                use_pretrained_model=True,
                use_pretrained_optimizer=False,
                threshold=1.0)

    def test(self):
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)
        with tempfile.TemporaryDirectory() as tmpdir:
            encoder, dataset = self.pretrain(tmpdir)
            self.reinforce(dataset, encoder, tmpdir)
            result = self.evaluate(dataset, encoder, tmpdir)
        assert 0.9 <= result.generation_rate