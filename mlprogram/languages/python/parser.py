import ast as python_ast
import transpyle
from typing import Optional, Callable, List
from mlprogram.languages.ast import AST
from mlprogram.languages.python.python_ast_to_ast import to_ast
from mlprogram.languages.python.ast_to_python_ast import to_python_ast


class Parser(object):
    def __init__(self, tokenize: Callable[[str], List[str]],
                 mode: str = "single"):
        super().__init__()
        assert mode in set(["single", "eval", "exec"])
        self.mode = mode
        self.tokenize = tokenize

    def parse(self, code: str) -> Optional[AST]:
        try:
            past = python_ast.parse(code)
            if self.mode == "exec":
                return to_ast(
                    past,
                    tokenize=self.tokenize)
            else:
                return to_ast(
                    past.body[0],
                    tokenize=self.tokenize)
        except:  # noqa
            return None

    def unparse(self, ast: AST) -> Optional[str]:
        unparser = transpyle.python.unparser.NativePythonUnparser()

        try:
            return unparser.unparse(to_python_ast(ast))
        except:  # noqa
            return None
