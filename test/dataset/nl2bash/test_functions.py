import unittest

from mlprogram.languages import Token
from mlprogram.datasets.nl2bash import TokenizeQuery
from mlprogram.datasets.nl2bash import SplitToken
from mlprogram.datasets.nl2bash.functions import get_subtokens


class TestGetSubtokens(unittest.TestCase):
    def test_words(self):
        self.assertEqual([Token(None, "foo", "foo")], get_subtokens("foo"))

    def test_numbers(self):
        self.assertEqual(
            [Token(None, "foo", "foo"), Token(None, "10", "10")],
            get_subtokens("foo10"))

    def test_others(self):
        self.assertEqual(
            [Token(None, "/", "/"), Token(None, "foo", "foo")],
            get_subtokens("/foo"))
        self.assertEqual(
            [Token(None, "$", "$"), Token(None, "{", "{"),
             Token(None, "foo", "foo"), Token(None, "10", "10"),
             Token(None, "}", "}")],
            get_subtokens("${" + "foo10" + "}"))


class TestTokenizeAnnotation(unittest.TestCase):
    def test_simple_case(self):
        reference = TokenizeQuery()("foo bar")
        self.assertEqual([Token(None, "foo", "foo"),
                          Token(None, "bar", "bar")],
                         reference)

    def test_subtokens(self):
        reference = TokenizeQuery()('foo.bar')
        self.assertEqual(
            [Token(None, "SUB_START", ""), Token(None, "foo", "foo"),
             Token(None, ".", "."),
             Token(None, "bar", "bar"), Token(None, "SUB_END", "")],
            reference)


class TestSplitToken(unittest.TestCase):
    def test_simple_case(self):
        self.assertEqual([Token(None, "test", "test")],
                         SplitToken()(Token(None, "test", "test")))

    def test_subtokens(self):
        tokens = SplitToken()(Token(None, "foo.bar", 'foo.bar'))
        self.assertEqual([
            Token(None, "foo", "foo"),
            Token(None, ".", "."),
            Token(None, "bar", "bar")
        ],
            tokens)

    def test_mapped_value(self):
        self.assertEqual([Token(None, "foo.bar", "foo-bar")],
                         SplitToken()(Token(None, "foo.bar", "foo-bar")))


if __name__ == "__main__":
    unittest.main()
