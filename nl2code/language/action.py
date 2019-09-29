from dataclasses import dataclass
from typing import Tuple, Union, List, Any
from enum import Enum


class NodeConstraint(Enum):
    Token = 1
    Node = 2
    Variadic = 3


@dataclass
class NodeType:
    """
    The type of the AST node

    Attributes
    ----------
    type_name: str
    constraint: NodeConstraint
        It represents the constraint of this type
    """
    type_name: str
    constraint: NodeConstraint

    def __hash__(self):
        return hash(self.type_name) ^ hash(self.constraint)

    def __eq__(self, rhs: Any):
        if isinstance(rhs, NodeType):
            return self.type_name == rhs.type_name and \
                self.constraint == rhs.constraint
        else:
            return False

    def __str__(self):
        if self.constraint == NodeConstraint.Variadic:
            return "{}*".format(self.type_name)
        elif self.constraint == NodeConstraint.Token:
            return "{}(token)".format(self.type_name)
        else:
            return self.type_name


@dataclass
class ExpandTreeRule:
    """
    Rule that expands AST

    Attributes
    ----------
    parent: NodeType
        The current node type
    children: List[Tuple[str, NodeType]]
        The node types of the fields
    """
    parent: NodeType
    children: List[Tuple[str, NodeType]]

    def __hash__(self):
        return hash(self.parent) ^ hash(tuple(self.children))

    def __eq__(self, rhs: Any):
        if isinstance(rhs, ExpandTreeRule):
            return self.parent == rhs.parent and self.children == rhs.children
        else:
            return False

    def __str__(self):
        children = ", ".join(
            map(lambda x: "{}: {}".format(x[0], x[1]), self.children))
        return "{} -> [{}]".format(self.parent, children)


class CloseVariadicFieldRule:
    """
    The rule that closes the variadic field
    """
    _instance = None

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, rhs: Any):
        return isinstance(rhs, CloseVariadicFieldRule)

    def __str__(self):
        return "<close variadic field>"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


Rule = Union[ExpandTreeRule, CloseVariadicFieldRule]


@dataclass
class ApplyRule:
    """
    The action to apply a rule

    Attributes
    ----------
    rule: Rule
    """
    rule: Rule

    def __str__(self):
        return "Apply ({})".format(self.rule)


class CloseNode:
    """
    The value to stop generating tokens
    """
    _instance = None

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, rhs: Any):
        return isinstance(rhs, CloseNode)

    def __str__(self):
        return "<CLOSE_NODE>"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


@dataclass
class GenerateToken:
    """
    The action to generate a token

    Attributes
    ----------
    token: Union[CloseNode, str]
        The value (token) to be generated
    """
    token: Union[CloseNode, str]

    def __str__(self):
        return "Generate {}".format(self.token)


Action = Union[ApplyRule, GenerateToken]
ActionSequence = List[Action]
