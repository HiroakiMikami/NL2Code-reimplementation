from typing import Generic, List, TypeVar

from mlprogram import Environment
from mlprogram.languages import BatchedState, Expander, Interpreter, Token

Code = TypeVar("Code")
Input = TypeVar("Input")
Value = TypeVar("Value")
Kind = TypeVar("Kind")


class ToEpisode(Generic[Code, Input, Value]):
    def __init__(self, interpreter: Interpreter[Code, Input, Value, Kind],
                 expander: Expander[Code]):
        self.interpreter = interpreter
        self.expander = expander

    def __call__(self, entry: Environment) -> List[Environment]:
        ground_truth = entry.supervisions["ground_truth"]
        test_cases = entry.inputs["test_cases"]
        inputs = [input for input, _ in test_cases]

        retval: List[Environment] = []
        state = BatchedState[Code, Value, Kind]({}, {}, [])
        for code in self.expander.expand(ground_truth):
            xs = entry.clone()
            xs.states["reference"] = [
                Token(state.type_environment[v], v, v)
                for v in state.environment.keys()
            ]
            xs.states["variables"] = [
                state.environment[token.value]
                for token in xs.states["reference"]
            ]
            xs.supervisions["ground_truth"] = code
            state = self.interpreter.execute(code, inputs, state)
            retval.append(xs)

        return retval