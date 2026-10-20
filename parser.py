# parser.py
"""
Parser for the Variable Declaration Compiler.
It validates input statements according to the CFG defined in grammar.py
and constructs an Abstract Syntax Tree (AST) for further processing.
"""

from __future__ import annotations

import sys
from typing import List, Optional, Union

# We expect a lexer module that provides a `tokenize` function and a `Token` class.
# The lexer should return a list of Token objects with `type` and `value` attributes.
# Token types used by the parser (mirroring the grammar):
#   TYPE, ID, NUMBER, CHAR_LITERAL, BOOL_LITERAL, '=', ';', '$' (end marker)
# The actual lexer implementation is not part of this task – the parser works
# with any compatible token stream.

try:
    from lexer import tokenize, Token
except ImportError as e:  # pragma: no cover
    # If the lexer is not available we raise a clear error so the user knows
    # why the parser cannot be used.
    raise ImportError(
        "lexer module not found. Ensure lexer.py provides `tokenize` and `Token`."
    ) from e

# ---------------------------------------------------------------------------
# AST node definitions
# ---------------------------------------------------------------------------

class ASTNode:
    """Base class for all AST nodes."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class Program(ASTNode):
    def __init__(self, statements: List[ASTNode]):
        self.statements = statements

    def __repr__(self) -> str:
        return f"Program(statements={self.statements})"


class Declaration(ASTNode):
    def __init__(self, var_type: str, identifier: str, value: Optional[ASTNode] = None):
        self.var_type = var_type
        self.identifier = identifier
        self.value = value

    def __repr__(self) -> str:
        return (
            f"Declaration(type={self.var_type}, id={self.identifier}, "
            f"value={self.value})"
        )


class Assignment(ASTNode):
    def __init__(self, identifier: str, value: ASTNode):
        self.identifier = identifier
        self.value = value

    def __repr__(self) -> str:
        return f"Assignment(id={self.identifier}, value={self.value})"


class Value(ASTNode):
    def __init__(self, token: Token):
        self.token = token

    def __repr__(self) -> str:
        return f"Value({self.token.type}:{self.token.value})"


# ---------------------------------------------------------------------------
# Parser implementation (recursive‑descent)
# ---------------------------------------------------------------------------

class ParserError(Exception):
    """Exception raised for syntax errors with a helpful message."""

    def __init__(self, token: Token, message: str):
        super().__init__(f"Syntax error at token {token!r}: {message}")
        self.token = token
        self.message = message


class Parser:
    def __init__(self, tokens: List[Token]):
        # Append the end‑marker token if it is not already present.
        if not tokens or tokens[-1].type != "END_MARKER":
            tokens.append(Token(type="END_MARKER", value="$"))
        self.tokens = tokens
        self.position = 0

    # ---------- Utility helpers ----------
    def _current(self) -> Token:
        return self.tokens[self.position]

    def _consume(self, expected_type: str) -> Token:
        token = self._current()
        if token.type != expected_type:
            raise ParserError(token, f"expected '{expected_type}' but got '{token.type}'")
        self.position += 1
        return token

    def _match(self, *types: str) -> bool:
        return self._current().type in types

    # ---------- Grammar methods ----------
    def parse(self) -> Program:
        """Entry point – parses a complete program and ensures the end marker.

        Grammar:
            Program -> StatementList END_MARKER
        """
        stmt_list = self._statement_list()
        self._consume("END_MARKER")
        return Program(stmt_list)

    def _statement_list(self) -> List[ASTNode]:
        """StatementList -> Statement StatementList | ε"""
        statements: List[ASTNode] = []
        while self._match("TYPE", "ID"):
            statements.append(self._statement())
        return statements

    def _statement(self) -> ASTNode:
        """Statement -> Declaration | Assignment"""
        if self._match("TYPE"):
            return self._declaration()
        elif self._match("ID"):
            return self._assignment()
        else:
            raise ParserError(self._current(), "expected a declaration or assignment")

    def _declaration(self) -> Declaration:
        """Declaration -> TYPE ID ';' | TYPE ID '=' Value ';'"""
        var_type_tok = self._consume("TYPE")
        id_tok = self._consume("ID")
        if self._match(";"):
            self._consume(";")
            return Declaration(var_type_tok.value, id_tok.value)
        elif self._match("="):
            self._consume("=")
            val = self._value()
            self._consume(";")
            return Declaration(var_type_tok.value, id_tok.value, val)
        else:
            raise ParserError(self._current(), "expected ';' or '=' after declaration")

    def _assignment(self) -> Assignment:
        """Assignment -> ID '=' Value ';'"""
        id_tok = self._consume("ID")
        self._consume("=")
        val = self._value()
        self._consume(";")
        return Assignment(id_tok.value, val)

    def _value(self) -> Value:
        """Value -> ID | NUMBER | CHAR_LITERAL | BOOL_LITERAL"""
        if self._match("ID", "NUMBER", "CHAR_LITERAL", "BOOL_LITERAL"):
            token = self._consume(self._current().type)
            return Value(token)
        else:
            raise ParserError(self._current(), "invalid value token")

# ---------------------------------------------------------------------------
# Convenience function for quick usage from the command line
# ---------------------------------------------------------------------------

def parse_source(source: str) -> Program:
    """Tokenize `source` using the lexer and return the parsed AST.

    Example:
        >>> src = "int x = 5;\nfloat y;"
        >>> ast = parse_source(src)
        >>> print(ast)
    """
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()


if __name__ == "__main__":  # pragma: no cover
    # Simple REPL for manual testing – read from stdin or a file passed as the first arg.
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            source_code = f.read()
    else:
        print("Enter source code (terminate with Ctrl‑D):")
        source_code = sys.stdin.read()
    try:
        ast = parse_source(source_code)
        print("AST:")
        print(ast)
    except ParserError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
