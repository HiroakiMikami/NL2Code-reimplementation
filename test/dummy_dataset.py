from typing import List
from nl2prog.language.ast import AST, Node, Leaf, Field
from nl2prog.utils.data import ListDataset, Entry


# Definition of dummy language
"""
Program := Assign | FunctionCall
Assign := Name = Value
FunctionCall := Name(Value*)
Name := <token(string)>
Number := <token(integer)>
Name and Number are subtypes of Value
"""


def is_subtype(subtype: str, basetype: str) -> bool:
    if subtype == basetype:
        return True
    if subtype in set(["Name", "Number", "List"]) and basetype == "Value":
        return True
    return False


def string(value: str):
    return Leaf("string", value)


def number(value: int):
    return Leaf("number", str(value))


def Name(value: str):
    return Node("Name", [Field("value", "string", string(value))])


def Number(value: int):
    return Node("Number", [Field("value", "number", number(value))])


def Assign(var: str, value: AST):
    return Node("Assign", [Field("var", "Name", Name(var)),
                           Field("value", "Value", value)])


def FunctionCall(name: str, args: List[AST]):
    return Node("FunctionCall", [Field("name", "Name", Name(name)),
                                 Field("args", "Value", args)])


# Dataset
train_dataset = ListDataset[Entry[str, AST], None]([
    [Entry("x is assigned the value of 0", Assign("x", Number(0)))],
    [Entry("dump the value of xy", FunctionCall("print", [Name("xy")]))],
    [Entry("dump the value of xy and x",
           FunctionCall("print", [Name("xy"), Name("x")]))]
])
test_dataset = ListDataset[Entry[str, AST], None]([
    [Entry("x is assigned the value of 4", Assign("x", Number(4)))],
    [Entry("dump the value of xy", FunctionCall("print", [Name("xy")]))],
    [Entry("dump the value of xy and x",
           FunctionCall("print", [Name("xy"), Name("x")]))]
])
