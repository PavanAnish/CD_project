# parser.py
"""
Syntax Analyzer (Parser) for the Variable Declaration Compiler.

Validates token streams against the Context-Free Grammar (CFG) defined in grammar.py
and constructs an Abstract Syntax Tree (AST) for semantic analysis and code generation.

Grammar Rules Supported:
    Program        -> StatementList
    StatementList  -> Statement StatementList | ε
    Statement      -> Declaration | Assignment
    Declaration    -> Type ID ';' | Type ID '=' Value ';'
    Assignment     -> ID '=' Value ';'
    Type           -> 'int' | 'float' | 'double' | 'char' | 'bool'
    Value          -> ID | NUMBER | CHAR_LITERAL | BOOL_LITERAL
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# Token definition (with graceful fallback if lexer.py is not yet populated)
# ---------------------------------------------------------------------------

class Token:
    """Represents a lexical token with type, value, line, and column position."""

    def __init__(self, type: str, value: Any, line: int = 1, column: int = 1):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.value!r}, line={self.line}, col={self.column})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return False
        return (
            self.type == other.type
            and self.value == other.value
            and self.line == other.line
            and self.column == other.column
        )


# Attempt import from lexer if available; otherwise use fallback
try:
    from lexer import Token as LexerToken, tokenize  # type: ignore
except (ImportError, AttributeError):
    LexerToken = Token
    tokenize = None


# Recognized primitive types according to grammar.py
DATA_TYPES = {"int", "float", "double", "char", "bool"}
VALUE_TYPES = {"ID", "NUMBER", "CHAR_LITERAL", "BOOL_LITERAL"}


# ---------------------------------------------------------------------------
# Abstract Syntax Tree (AST) Nodes
# ---------------------------------------------------------------------------

class ASTNode:
    """Base class for all Abstract Syntax Tree nodes."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the AST node into a dictionary (useful for JSON/Flask UI)."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class Program(ASTNode):
    """Root AST node containing a list of statements."""

    def __init__(self, statements: Optional[List[ASTNode]] = None):
        self.statements: List[ASTNode] = statements if statements is not None else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Program",
            "statements": [stmt.to_dict() for stmt in self.statements],
        }

    def __repr__(self) -> str:
        return f"Program(statements={self.statements!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Program) and self.statements == other.statements


class Declaration(ASTNode):
    """AST node for variable declarations (with optional initialization).

    Examples:
        int x;
        float mark = 95.5;
    """

    def __init__(
        self,
        var_type: str,
        identifier: str,
        value: Optional[Value] = None,
        line: int = 1,
        column: int = 1,
    ):
        self.var_type = var_type
        self.identifier = identifier
        self.value = value
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Declaration",
            "var_type": self.var_type,
            "identifier": self.identifier,
            "value": self.value.to_dict() if self.value else None,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return (
            f"Declaration(var_type={self.var_type!r}, identifier={self.identifier!r}, "
            f"value={self.value!r}, line={self.line})"
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Declaration)
            and self.var_type == other.var_type
            and self.identifier == other.identifier
            and self.value == other.value
        )


class Assignment(ASTNode):
    """AST node for variable assignment statements.

    Example:
        age = 20;
    """

    def __init__(
        self,
        identifier: str,
        value: Value,
        line: int = 1,
        column: int = 1,
    ):
        self.identifier = identifier
        self.value = value
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Assignment",
            "identifier": self.identifier,
            "value": self.value.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return (
            f"Assignment(identifier={self.identifier!r}, value={self.value!r}, "
            f"line={self.line})"
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Assignment)
            and self.identifier == other.identifier
            and self.value == other.value
        )


class Value(ASTNode):
    """AST node representing a literal or identifier value.

    Can be: ID, NUMBER, CHAR_LITERAL, BOOL_LITERAL
    """

    def __init__(
        self,
        value_type: str,
        value: Any,
        line: int = 1,
        column: int = 1,
    ):
        self.value_type = value_type
        self.value = value
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Value",
            "value_type": self.value_type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"Value({self.value_type!r}, {self.value!r})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Value)
            and self.value_type == other.value_type
            and str(self.value) == str(other.value)
        )


# ---------------------------------------------------------------------------
# Parser & Error Handling
# ---------------------------------------------------------------------------

class ParserError(Exception):
    """Raised when the input violates context-free grammar rules."""

    def __init__(
        self,
        message: str,
        token: Optional[Token] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        self.token = token
        self.line = line or (token.line if token else None)
        self.column = column or (token.column if token else None)
        self.raw_message = message

        loc_str = ""
        if self.line is not None:
            loc_str = f" at line {self.line}"
            if self.column is not None:
                loc_str += f", column {self.column}"

        super().__init__(f"Syntax Error{loc_str}: {message}")


class Parser:
    """Recursive Descent Parser for Variable Declarations & Assignments."""

    def __init__(self, tokens: List[Token]):
        self.tokens = list(tokens)
        # Ensure the stream terminates with an END_MARKER / EOF
        if not self.tokens or not self._is_end(self.tokens[-1]):
            last_line = self.tokens[-1].line if self.tokens else 1
            last_col = self.tokens[-1].column if self.tokens else 1
            self.tokens.append(Token("END_MARKER", "$", line=last_line, column=last_col))
        self.position = 0

    # ---------- Internal Helpers ----------

    def _current(self) -> Token:
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return self.tokens[-1]

    def _is_end(self, token: Token) -> bool:
        return token.type in {"END_MARKER", "EOF", "$"}

    def _is_type_token(self, token: Token) -> bool:
        """Check if token matches Type non-terminal ('int', 'float', 'double', 'char', 'bool')."""
        return (
            token.type in DATA_TYPES
            or (token.type in {"TYPE", "KEYWORD"} and str(token.value) in DATA_TYPES)
            or str(token.value) in DATA_TYPES
        )

    def _is_semicolon(self, token: Token) -> bool:
        return token.type in {";", "SEMICOLON"} or token.value == ";"

    def _is_assign_op(self, token: Token) -> bool:
        return token.type in {"=", "ASSIGN"} or token.value == "="

    def _consume(self, expected_desc: str) -> Token:
        """Consume current token and advance; raises error if unexpected."""
        token = self._current()
        if self._is_end(token):
            raise ParserError(f"Unexpected end of input; expected {expected_desc}", token)
        self.position += 1
        return token

    # ---------- Grammar Productions ----------

    def parse(self) -> Program:
        """Program -> StatementList END_MARKER"""
        statements = self._statement_list()
        cur = self._current()
        if not self._is_end(cur):
            raise ParserError(
                f"Unexpected token {cur.value!r} ({cur.type}); expected end of input",
                cur,
            )
        return Program(statements)

    def _statement_list(self) -> List[ASTNode]:
        """StatementList -> Statement StatementList | ε"""
        statements: List[ASTNode] = []
        while not self._is_end(self._current()):
            token = self._current()
            # Statement can start with Type (Declaration) or ID (Assignment)
            if self._is_type_token(token) or token.type == "ID":
                statements.append(self._statement())
            else:
                break
        return statements

    def _statement(self) -> ASTNode:
        """Statement -> Declaration | Assignment"""
        token = self._current()
        if self._is_type_token(token):
            return self._declaration()
        elif token.type == "ID":
            return self._assignment()
        else:
            raise ParserError(
                f"Expected declaration (type) or assignment (identifier), got {token.value!r} ({token.type})",
                token,
            )

    def _declaration(self) -> Declaration:
        """Declaration -> Type ID ';' | Type ID '=' Value ';'"""
        type_token = self._current()
        if not self._is_type_token(type_token):
            raise ParserError(f"Expected type keyword, got {type_token.value!r}", type_token)
        self.position += 1
        var_type = str(type_token.value)

        id_token = self._current()
        if id_token.type != "ID":
            raise ParserError(f"Expected identifier after type {var_type!r}, got {id_token.value!r}", id_token)
        self.position += 1
        identifier = str(id_token.value)

        next_tok = self._current()
        if self._is_semicolon(next_tok):
            self.position += 1
            return Declaration(
                var_type=var_type,
                identifier=identifier,
                value=None,
                line=type_token.line,
                column=type_token.column,
            )
        elif self._is_assign_op(next_tok):
            self.position += 1
            val_node = self._value()
            semi_tok = self._current()
            if not self._is_semicolon(semi_tok):
                raise ParserError(f"Expected ';' after assignment value, got {semi_tok.value!r}", semi_tok)
            self.position += 1
            return Declaration(
                var_type=var_type,
                identifier=identifier,
                value=val_node,
                line=type_token.line,
                column=type_token.column,
            )
        else:
            raise ParserError(
                f"Expected ';' or '=' after identifier {identifier!r}, got {next_tok.value!r}",
                next_tok,
            )

    def _assignment(self) -> Assignment:
        """Assignment -> ID '=' Value ';'"""
        id_token = self._current()
        if id_token.type != "ID":
            raise ParserError(f"Expected identifier, got {id_token.value!r}", id_token)
        self.position += 1
        identifier = str(id_token.value)

        assign_tok = self._current()
        if not self._is_assign_op(assign_tok):
            raise ParserError(f"Expected '=' after identifier {identifier!r}, got {assign_tok.value!r}", assign_tok)
        self.position += 1

        val_node = self._value()

        semi_tok = self._current()
        if not self._is_semicolon(semi_tok):
            raise ParserError(f"Expected ';' after assignment value, got {semi_tok.value!r}", semi_tok)
        self.position += 1

        return Assignment(
            identifier=identifier,
            value=val_node,
            line=id_token.line,
            column=id_token.column,
        )

    def _value(self) -> Value:
        """Value -> ID | NUMBER | CHAR_LITERAL | BOOL_LITERAL"""
        token = self._current()
        # Accept recognized value token types or BOOL values
        if token.type in VALUE_TYPES or (token.type in {"KEYWORD", "BOOLEAN"} and str(token.value) in {"true", "false"}):
            self.position += 1
            val_type = "BOOL_LITERAL" if str(token.value) in {"true", "false"} else token.type
            return Value(
                value_type=val_type,
                value=token.value,
                line=token.line,
                column=token.column,
            )
        else:
            raise ParserError(
                f"Expected literal or identifier for value, got {token.value!r} ({token.type})",
                token,
            )


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def parse(tokens: List[Token]) -> Program:
    """Parse a list of tokens into an AST Program node."""
    parser = Parser(tokens)
    return parser.parse()


def parse_source(source_code: str) -> Program:
    """Tokenize and parse source code string into an AST.

    Requires lexer.tokenize to be implemented.
    """
    if tokenize is None:
        raise NotImplementedError(
            "lexer.tokenize is not yet available. Pass a list of Token objects to `parse(tokens)` instead."
        )
    tokens = tokenize(source_code)
    return parse(tokens)


if __name__ == "__main__":
    # Test script: demonstrate parsing sample token sequences
    sample_tokens = [
        Token("TYPE", "int", line=1, column=1),
        Token("ID", "age", line=1, column=5),
        Token(";", ";", line=1, column=8),
        Token("TYPE", "float", line=2, column=1),
        Token("ID", "mark", line=2, column=7),
        Token("=", "=", line=2, column=12),
        Token("NUMBER", "95.5", line=2, column=14),
        Token(";", ";", line=2, column=18),
        Token("ID", "age", line=3, column=1),
        Token("=", "=", line=3, column=5),
        Token("NUMBER", "20", line=3, column=7),
        Token(";", ";", line=3, column=9),
    ]

    print("Running parser verification on sample tokens...")
    ast = parse(sample_tokens)
    print("Parsing succeeded! AST:")
    print(ast)
    print("\nSerialized AST (JSON-ready):")
    import json
    print(json.dumps(ast.to_dict(), indent=2))
