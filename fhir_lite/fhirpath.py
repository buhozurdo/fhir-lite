"""Lightweight, zero-dependency FHIRPath mini-engine for Python.

Supports path traversal, collection functions, and .where() filtering.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence, Union


class FHIRPathError(Exception):
    """Raised when FHIRPath parsing or evaluation fails."""
    pass


# ----------------------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------------------

TOKEN_SPEC = [
    ("NUMBER", r"-?\d+(?:\.\d+)?"),
    ("STRING", r"'(?:\\.|[^'])*'"),
    ("BOOL", r"\b(?:true|false)\b"),
    ("AND", r"\band\b"),
    ("OR", r"\bor\b"),
    ("NOT", r"\bnot\b"),
    ("CONTAINS", r"\bcontains\b"),
    ("OP", r"!=|<=|>=|=|<|>"),
    ("DOT", r"\."),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACKET", r"\["),
    ("RBRACKET", r"\]"),
    ("COMMA", r","),
    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("WS", r"\s+"),
]

TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


class Token:
    __slots__ = ("type", "value", "pos")

    def __init__(self, type_: str, value: str, pos: int):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


def tokenize(expr: str) -> list[Token]:
    tokens: list[Token] = []
    for mo in TOKEN_RE.finditer(expr):
        kind = mo.lastgroup
        val = mo.group()
        if kind == "WS":
            continue
        elif kind is None:
            raise FHIRPathError(f"Unexpected character at {mo.start()}: {expr[mo.start():mo.start()+10]}")
        tokens.append(Token(kind, val, mo.start()))
    tokens.append(Token("EOF", "", len(expr)))
    return tokens


# ----------------------------------------------------------------------
# AST Nodes
# ----------------------------------------------------------------------

class ASTNode:
    pass


class LiteralNode(ASTNode):
    __slots__ = ("value",)

    def __init__(self, value: Any):
        self.value = value


class IdentifierNode(ASTNode):
    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name


class IndexNode(ASTNode):
    __slots__ = ("index",)

    def __init__(self, index: int):
        self.index = index


class FunctionCallNode(ASTNode):
    __slots__ = ("name", "args")

    def __init__(self, name: str, args: list[ASTNode]):
        self.name = name
        self.args = args


class BinaryOpNode(ASTNode):
    __slots__ = ("op", "left", "right")

    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right


class UnaryOpNode(ASTNode):
    __slots__ = ("op", "operand")

    def __init__(self, op: str, operand: ASTNode):
        self.op = op
        self.operand = operand


class PathNode(ASTNode):
    __slots__ = ("steps",)

    def __init__(self, steps: list[ASTNode]):
        self.steps = steps


# ----------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def match(self, *types: str) -> bool:
        if self.current().type in types:
            self.pos += 1
            return True
        return False

    def expect(self, type_: str) -> Token:
        curr = self.current()
        if curr.type != type_:
            raise FHIRPathError(f"Expected {type_} but got {curr.type} ({curr.value!r}) at position {curr.pos}")
        self.pos += 1
        return curr

    def parse(self) -> ASTNode:
        node = self.expr()
        if self.current().type != "EOF":
            curr = self.current()
            raise FHIRPathError(f"Unexpected token {curr.value!r} at position {curr.pos}")
        return node

    def expr(self) -> ASTNode:
        return self.logical_or()

    def logical_or(self) -> ASTNode:
        left = self.logical_and()
        while self.match("OR"):
            right = self.logical_and()
            left = BinaryOpNode("or", left, right)
        return left

    def logical_and(self) -> ASTNode:
        left = self.equality()
        while self.match("AND"):
            right = self.equality()
            left = BinaryOpNode("and", left, right)
        return left

    def equality(self) -> ASTNode:
        left = self.relational()
        while self.current().type in ("OP", "CONTAINS"):
            op = self.current().value
            self.pos += 1
            right = self.relational()
            left = BinaryOpNode(op, left, right)
        return left

    def relational(self) -> ASTNode:
        left = self.path_expr()
        return left

    def path_expr(self) -> ASTNode:
        steps: list[ASTNode] = [self.invocation()]
        while True:
            if self.match("DOT"):
                steps.append(self.invocation())
            elif self.match("LBRACKET"):
                idx_tok = self.expect("NUMBER")
                self.expect("RBRACKET")
                steps.append(IndexNode(int(idx_tok.value)))
            else:
                break

        if len(steps) == 1:
            return steps[0]
        return PathNode(steps)

    def invocation(self) -> ASTNode:
        tok = self.current()
        if tok.type in ("IDENT", "CONTAINS", "NOT", "AND", "OR"):
            self.pos += 1
            name = tok.value
            if self.match("LPAREN"):
                args: list[ASTNode] = []
                if not self.match("RPAREN"):
                    while True:
                        args.append(self.expr())
                        if self.match("COMMA"):
                            continue
                        elif self.match("RPAREN"):
                            break
                        else:
                            raise FHIRPathError(f"Expected ',' or ')' at position {self.current().pos}")
                return FunctionCallNode(name, args)
            return IdentifierNode(name)
        elif tok.type == "STRING":
            self.pos += 1
            # Unescape string
            val = tok.value[1:-1].encode("utf-8").decode("unicode_escape")
            return LiteralNode(val)
        elif tok.type == "NUMBER":
            self.pos += 1
            val_str = tok.value
            val = float(val_str) if "." in val_str else int(val_str)
            return LiteralNode(val)
        elif tok.type == "BOOL":
            self.pos += 1
            return LiteralNode(tok.value == "true")
        elif self.match("LPAREN"):
            node = self.expr()
            self.expect("RPAREN")
            return node
        else:
            raise FHIRPathError(f"Unexpected token {tok.type} ({tok.value!r}) at position {tok.pos}")


# ----------------------------------------------------------------------
# Evaluator
# ----------------------------------------------------------------------

def _get_item_data(item: Any) -> Any:
    """Extract dict data if item is a FHIRResource or similar."""
    if hasattr(item, "data") and isinstance(item.data, dict):
        return item.data
    return item


def _is_truthy(val: Any) -> bool:
    if isinstance(val, list):
        if not val:
            return False
        if len(val) == 1:
            return _is_truthy(val[0])
        return True
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    return bool(val)


class Evaluator:
    def __init__(self, root: Any):
        self.root = root

    def eval(self, node: ASTNode, context: list[Any]) -> list[Any]:
        if isinstance(node, LiteralNode):
            return [node.value]

        elif isinstance(node, IdentifierNode):
            res: list[Any] = []
            for item in context:
                data = _get_item_data(item)
                if isinstance(data, dict):
                    # Check if identifier matches resourceType at root level
                    if node.name == data.get("resourceType") and node.name not in data:
                        res.append(item)
                    elif node.name in data:
                        val = data[node.name]
                        if isinstance(val, list):
                            res.extend(val)
                        elif val is not None:
                            res.append(val)
                elif hasattr(item, node.name):
                    val = getattr(item, node.name)
                    if isinstance(val, list):
                        res.extend(val)
                    elif val is not None:
                        res.append(val)
            return res

        elif isinstance(node, IndexNode):
            if 0 <= node.index < len(context):
                return [context[node.index]]
            return []

        elif isinstance(node, PathNode):
            curr = context
            for step in node.steps:
                curr = self.eval(step, curr)
            return curr

        elif isinstance(node, FunctionCallNode):
            return self._eval_function(node.name, node.args, context)

        elif isinstance(node, BinaryOpNode):
            return self._eval_binary(node.op, node.left, node.right, context)

        raise FHIRPathError(f"Unknown AST node type: {type(node).__name__}")

    def _eval_function(self, name: str, args: list[ASTNode], context: list[Any]) -> list[Any]:
        if name == "where":
            if not args:
                raise FHIRPathError(".where() requires a criteria expression")
            criteria = args[0]
            filtered: list[Any] = []
            for item in context:
                item_ctx = [item]
                res = self.eval(criteria, item_ctx)
                if _is_truthy(res):
                    filtered.append(item)
            return filtered

        elif name == "exists":
            if args:
                # exists(criteria)
                filtered = self._eval_function("where", args, context)
                return [len(filtered) > 0]
            return [len(context) > 0]

        elif name == "empty":
            return [len(context) == 0]

        elif name == "first":
            return [context[0]] if context else []

        elif name == "last":
            return [context[-1]] if context else []

        elif name == "count":
            return [len(context)]

        elif name == "skip":
            if not args:
                raise FHIRPathError(".skip() requires a count argument")
            n_res = self.eval(args[0], context)
            n = int(n_res[0]) if n_res else 0
            return context[n:]

        elif name == "take":
            if not args:
                raise FHIRPathError(".take() requires a count argument")
            n_res = self.eval(args[0], context)
            n = int(n_res[0]) if n_res else 0
            return context[:n]

        elif name == "tail":
            return context[1:] if len(context) > 1 else []

        elif name == "distinct":
            seen: list[Any] = []
            for it in context:
                if it not in seen:
                    seen.append(it)
            return seen

        elif name == "contains":
            if not args:
                raise FHIRPathError(".contains() requires an argument")
            arg_val = self.eval(args[0], context)
            search_val = arg_val[0] if arg_val else ""
            res: list[Any] = []
            for item in context:
                if isinstance(item, str):
                    res.append(str(search_val) in item)
                elif isinstance(item, (list, tuple)):
                    res.append(search_val in item)
            return res if res else [False]

        elif name == "startsWith":
            if not args:
                raise FHIRPathError(".startsWith() requires a prefix argument")
            arg_val = self.eval(args[0], context)
            prefix = str(arg_val[0]) if arg_val else ""
            res = [isinstance(item, str) and item.startswith(prefix) for item in context]
            return [any(res)] if res else [False]

        elif name == "endsWith":
            if not args:
                raise FHIRPathError(".endsWith() requires a suffix argument")
            arg_val = self.eval(args[0], context)
            suffix = str(arg_val[0]) if arg_val else ""
            res = [isinstance(item, str) and item.endswith(suffix) for item in context]
            return [any(res)] if res else [False]

        elif name == "lower":
            return [item.lower() if isinstance(item, str) else item for item in context]

        elif name == "upper":
            return [item.upper() if isinstance(item, str) else item for item in context]

        elif name == "join":
            sep = ""
            if args:
                sep_res = self.eval(args[0], context)
                sep = str(sep_res[0]) if sep_res else ""
            return [sep.join(str(it) for it in context)]

        elif name == "not":
            return [not _is_truthy(context)]

        elif name == "as":
            # Filter by resourceType e.g. .as(Observation)
            if not args:
                raise FHIRPathError(".as() requires a type name")
            target_type = getattr(args[0], "name", None) or getattr(args[0], "value", "")
            return [
                it for it in context
                if (_get_item_data(it).get("resourceType") == target_type)
            ]

        raise FHIRPathError(f"Unsupported FHIRPath function: '{name}'")

    def _eval_binary(self, op: str, left_node: ASTNode, right_node: ASTNode, context: list[Any]) -> list[Any]:
        if op == "and":
            left_val = self.eval(left_node, context)
            if not _is_truthy(left_val):
                return [False]
            right_val = self.eval(right_node, context)
            return [_is_truthy(right_val)]

        elif op == "or":
            left_val = self.eval(left_node, context)
            if _is_truthy(left_val):
                return [True]
            right_val = self.eval(right_node, context)
            return [_is_truthy(right_val)]

        # Relational or equality
        left_val = self.eval(left_node, context)
        right_val = self.eval(right_node, context)

        # Unbox single item collections for comparison
        l = left_val[0] if len(left_val) == 1 else left_val
        r = right_val[0] if len(right_val) == 1 else right_val

        # If left was empty collection, treat as None/empty
        if len(left_val) == 0:
            l = None
        if len(right_val) == 0:
            r = None

        if op == "=":
            return [l == r]
        elif op == "!=":
            return [l != r]
        elif op == "<":
            return [l is not None and r is not None and l < r]
        elif op == "<=":
            return [l is not None and r is not None and l <= r]
        elif op == ">":
            return [l is not None and r is not None and l > r]
        elif op == ">=":
            return [l is not None and r is not None and l >= r]
        elif op == "contains":
            if isinstance(l, str):
                return [str(r) in l]
            elif isinstance(l, (list, tuple)):
                return [r in l]
            return [False]

        raise FHIRPathError(f"Unsupported binary operator: '{op}'")


# ----------------------------------------------------------------------
# Main Public API
# ----------------------------------------------------------------------

def evaluate_fhirpath(
    resource_or_data: Any,
    expression: str,
    first: bool = False,
) -> Any:
    """Evaluate a FHIRPath expression against a FHIR resource, list, or dict.

    Parameters
    ----------
    resource_or_data : Any
        A FHIRResource instance, resource dict, or list of resources.
    expression : str
        FHIRPath expression string (e.g. "name.where(use = 'official').family").
    first : bool, default False
        If True, returns the first result or None instead of a list.

    Returns
    -------
    list[Any] | Any
        The extracted list of results, or single item if `first=True`.
    """
    if not expression or not expression.strip():
        return [] if not first else None

    tokens = tokenize(expression.strip())
    parser = Parser(tokens)
    ast = parser.parse()

    initial_context = (
        resource_or_data if isinstance(resource_or_data, list) else [resource_or_data]
    )
    evaluator = Evaluator(root=resource_or_data)
    results = evaluator.eval(ast, initial_context)

    if first:
        return results[0] if results else None
    return results


__all__ = ["evaluate_fhirpath", "FHIRPathError"]
