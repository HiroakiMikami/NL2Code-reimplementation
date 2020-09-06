import unittest
import ast

from mlprogram.languages.python import to_ast, Parse, Unparse
from mlprogram.asts import Node


class TestParse(unittest.TestCase):
    def test_parse_code(self):
        self.assertEqual(
            to_ast(ast.parse("y = x + 1").body[0], lambda x: [x]),
            Parse(lambda x: [x])("y = x + 1")
        )

    def test_invalid_code(self):
        self.assertEqual(None, Parse(lambda x: [x])("if True"))

    def test_mode(self):
        self.assertEqual(
            to_ast(ast.parse("xs = input().split()\nprint(','.join(xs))"),
                   lambda x: [x]),
            Parse(lambda x: [x], mode="exec")(
                "xs = input().split()\nprint(','.join(xs))")
        )


class TestUnparse(unittest.TestCase):
    def test_Unparse_ast(self):
        self.assertEqual(
            "\ny = (x + 1)\n", Unparse()(Parse(lambda x: [x])("y = x + 1"))
        )

    def test_invalid_ast(self):
        self.assertEqual(None, Unparse()(Node("USub", [])))

    def test_mode(self):
        self.assertEqual(
            "\nxs = input().split()\nprint(','.join(xs))\n",
            Unparse()(Parse(lambda x: [x], mode="exec")(
                "xs = input().split()\nprint(','.join(xs))"))
        )


if __name__ == "__main__":
    unittest.main()