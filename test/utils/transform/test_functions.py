import unittest
import numpy as np

from mlprogram.utils import Query, Token, Reference
from mlprogram.utils.data import ListDataset, get_samples
from mlprogram.asts import Node, Leaf, Field
from mlprogram.encoders import ActionSequenceEncoder
from mlprogram.utils.transform import AstToSingleActionSequence
from mlprogram.utils.transform \
    import TransformCode, TransformGroundTruth, RandomChoice, \
    EvaluateGroundTruth
from mlprogram.interpreters import Interpreter


def tokenize_query(query: str):
    return Query(
        list(map(lambda x: Token(None, x), query.split(" "))),
        query.split(" "))


def to_action_sequence(code: str):
    ast = Node("Assign",
               [Field("name", "Name",
                      Node("Name", [Field("id", "str", [Leaf("str", "x")])])),
                Field("value", "expr",
                      Node("Op", [
                           Field("op", "str", [Leaf("str", "+")]),
                           Field("arg0", "expr",
                                 Node("Name", [Field("id", "str",
                                                     [Leaf("str", "y")])])),
                           Field("arg1", "expr",
                                 Node("Number", [Field("value", "number",
                                                       [Leaf("number", "1")])
                                                 ]))]
                           ))])
    return AstToSingleActionSequence()(ast)


class TestTransformCode(unittest.TestCase):
    def test_simple_case(self):
        transform = TransformCode(to_action_sequence)
        action_sequence = \
            transform({"ground_truth": "y = x + 1"})["action_sequence"]
        self.assertEqual(None, action_sequence.head)


class TestTransformGroundTruth(unittest.TestCase):
    def test_simple_case(self):
        entries = [{"input": "foo bar", "ground_truth": "y = x + 1"}]
        dataset = ListDataset(entries)
        d = get_samples(dataset, to_action_sequence)
        aencoder = ActionSequenceEncoder(d, 0)
        input = \
            TransformCode(to_action_sequence)({"ground_truth": "y = x + 1"})
        transform = TransformGroundTruth(aencoder)
        input["reference"] = [Token(None, "foo"), Token(None, "bar")]
        ground_truth = \
            transform(input)["ground_truth_actions"]
        self.assertTrue(np.array_equal(
            [
                [3, -1, -1], [4, -1, -1], [-1, 1, -1], [1, -1, -1],
                [5, -1, -1], [-1, 2, -1], [1, -1, -1], [4, -1, -1],
                [-1, 3, -1], [1, -1, -1], [6, -1, -1], [-1, 4, -1],
                [1, -1, -1]
            ],
            ground_truth.numpy()
        ))

    def test_impossible_case(self):
        entries = [{"input": "foo bar", "ground_truth": "y = x + 1"}]
        dataset = ListDataset(entries)
        d = get_samples(dataset, to_action_sequence)
        d.tokens = ["y", "1"]
        aencoder = ActionSequenceEncoder(d, 0)
        action_sequence = TransformCode(to_action_sequence)({
            "ground_truth": "y = x + 1"
        })["action_sequence"]
        transform = TransformGroundTruth(aencoder)
        ground_truth = transform({
            "action_sequence": action_sequence,
            "reference": [Token(None, "foo"), Token(None, "bar")]
        })
        self.assertEqual(None, ground_truth)


class TestRandomChoice(unittest.TestCase):
    def test_choice(self):
        transform = RandomChoice()
        x = transform({"x": [0, 1], "y": [0, 1]})
        self.assertTrue(isinstance(x["x"], int))
        self.assertTrue(isinstance(x["y"], int))


class MockInterpreter(Interpreter):
    def eval(self, code):
        return int(code)

    def eval_references(self, code):
        return {ref: int(code) for ref, code in code.items()}


class TestEvaluateGroundTruth(unittest.TestCase):
    def test_non_reference(self):
        f = EvaluateGroundTruth(MockInterpreter())
        self.assertTrue(1, f({"ground_truth": "1"})["test_case"])

    def test_reference(self):
        f = EvaluateGroundTruth(MockInterpreter())
        result = f({
            "ground_truth": {
                Reference(0): "1",
                Reference(1): "2"
            },
            "output_reference": Reference(1)
        })
        self.assertTrue(2, result["test_case"])
        self.assertTrue({Reference(0): 1, Reference(1): 2},
                        result["variables"])


if __name__ == "__main__":
    unittest.main()
