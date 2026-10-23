"""Flask interface for the variable declaration compiler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)
MAX_SOURCE_LENGTH = 20000
DATA_TYPES = {"int", "float", "double", "char", "bool"}
CHAR_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'"}


@dataclass
class Token:
	type: str
	value: Any
	line: int
	column: int

	def as_dict(self) -> dict[str, Any]:
		return {"type": self.type, "value": self.value, "line": self.line, "column": self.column}


class CompileError(Exception):
	def __init__(self, phase: str, message: str, line: int, column: int):
		self.phase = phase
		self.message = message
		self.line = line
		self.column = column
		super().__init__(message)

	def as_dict(self) -> dict[str, Any]:
		return {"phase": self.phase, "message": self.message, "line": self.line, "column": self.column}


def tokenize(source: str) -> list[Token]:
	tokens: list[Token] = []
	index = 0
	line = 1
	column = 1

	def advance() -> str:
		nonlocal index, line, column
		char = source[index]
		index += 1
		if char == "\n":
			line += 1
			column = 1
		else:
			column += 1
		return char

	while index < len(source):
		char = source[index]
		if char.isspace():
			advance()
			continue
		if source.startswith("//", index):
			while index < len(source) and source[index] != "\n":
				advance()
			continue

		start_line, start_column = line, column
		if char.isalpha() or char == "_":
			start = index
			while index < len(source) and (source[index].isalnum() or source[index] == "_"):
				advance()
			word = source[start:index]
			token_type = "TYPE" if word in DATA_TYPES else "BOOL_LITERAL" if word in {"true", "false"} else "ID"
			value: Any = word == "true" if token_type == "BOOL_LITERAL" else word
			tokens.append(Token(token_type, value, start_line, start_column))
			continue

		if char.isdigit():
			start = index
			while index < len(source) and source[index].isdigit():
				advance()
			if index < len(source) and source[index] == ".":
				advance()
				if index >= len(source) or not source[index].isdigit():
					raise CompileError("lexical", "A decimal point must be followed by digits.", start_line, start_column)
				while index < len(source) and source[index].isdigit():
					advance()
			if index < len(source) and source[index] in "eE":
				advance()
				if index < len(source) and source[index] in "+-":
					advance()
				exponent_start = index
				while index < len(source) and source[index].isdigit():
					advance()
				if index == exponent_start:
					raise CompileError("lexical", "An exponent must contain digits.", start_line, start_column)
			tokens.append(Token("NUMBER", source[start:index], start_line, start_column))
			continue

		if char == "'":
			advance()
			if index >= len(source) or source[index] in "\r\n'":
				raise CompileError("lexical", "Expected one character inside single quotes.", start_line, start_column)
			if source[index] == "\\":
				advance()
				if index >= len(source) or source[index] in "\r\n":
					raise CompileError("lexical", "Incomplete escape sequence in character literal.", start_line, start_column)
				escaped = advance()
				if escaped not in CHAR_ESCAPES:
					raise CompileError("lexical", f"Unsupported escape sequence \\{escaped}.", start_line, start_column)
				value = CHAR_ESCAPES[escaped]
			else:
				value = advance()
			if index >= len(source) or source[index] != "'":
				raise CompileError("lexical", "Character literal must contain exactly one character.", start_line, start_column)
			advance()
			tokens.append(Token("CHAR_LITERAL", value, start_line, start_column))
			continue

		if char in "=;":
			tokens.append(Token(char, advance(), start_line, start_column))
			continue
		raise CompileError("lexical", f"Unexpected character {char!r}.", line, column)

	tokens.append(Token("END_MARKER", "$", line, column))
	return tokens


class Parser:
	def __init__(self, tokens: list[Token]):
		self.tokens = tokens
		self.position = 0

	def current(self) -> Token:
		return self.tokens[self.position]

	def consume(self, expected: str) -> Token:
		token = self.current()
		if token.type == "END_MARKER":
			raise CompileError("syntax", f"Unexpected end of input; expected {expected}.", token.line, token.column)
		self.position += 1
		return token

	def parse(self) -> dict[str, Any]:
		statements = []
		while self.current().type != "END_MARKER":
			token = self.current()
			if token.type == "TYPE":
				statements.append(self.declaration())
			elif token.type == "ID":
				statements.append(self.assignment())
			else:
				raise CompileError("syntax", f"Expected a declaration or assignment, got {token.value!r}.", token.line, token.column)
		return {"type": "Program", "statements": statements}

	def declaration(self) -> dict[str, Any]:
		type_token = self.consume("a data type")
		identifier = self.current()
		if identifier.type != "ID":
			raise CompileError("syntax", f"Expected an identifier after {type_token.value!r}.", identifier.line, identifier.column)
		self.position += 1
		value = None
		if self.current().type == "=":
			self.position += 1
			value = self.parse_value()
		self.semicolon()
		return {
			"type": "Declaration", "var_type": type_token.value, "identifier": identifier.value,
			"value": value, "line": type_token.line, "column": type_token.column,
		}

	def assignment(self) -> dict[str, Any]:
		identifier = self.consume("an identifier")
		if self.current().type != "=":
			token = self.current()
			raise CompileError("syntax", f"Expected '=' after identifier {identifier.value!r}.", token.line, token.column)
		self.position += 1
		value = self.parse_value()
		self.semicolon()
		return {
			"type": "Assignment", "identifier": identifier.value, "value": value,
			"line": identifier.line, "column": identifier.column,
		}

	def parse_value(self) -> dict[str, Any]:
		token = self.current()
		if token.type not in {"ID", "NUMBER", "CHAR_LITERAL", "BOOL_LITERAL"}:
			raise CompileError("syntax", f"Expected a literal or identifier, got {token.value!r}.", token.line, token.column)
		self.position += 1
		return {
			"type": "Value", "value_type": token.type, "value": token.value,
			"line": token.line, "column": token.column,
		}

	def semicolon(self) -> None:
		token = self.current()
		if token.type != ";":
			raise CompileError("syntax", f"Expected ';', got {token.value!r}.", token.line, token.column)
		self.position += 1


def analyze(program: dict[str, Any]) -> dict[str, dict[str, Any]]:
	symbols: dict[str, dict[str, Any]] = {}

	def value_type(value: dict[str, Any]) -> tuple[str, Any]:
		kind = value["value_type"]
		raw = value["value"]
		if kind == "ID":
			symbol = symbols.get(raw)
			if symbol is None:
				raise CompileError("semantic", f"Variable {raw!r} is not declared.", value["line"], value["column"])
			return symbol["type"], symbol["value"]
		if kind == "NUMBER":
			return ("float", float(raw)) if any(mark in raw.lower() for mark in (".", "e")) else ("int", int(raw))
		if kind == "CHAR_LITERAL":
			return "char", raw
		return "bool", raw

	def assign_value(destination: str, value: dict[str, Any], line: int, column: int) -> Any:
		source_type, resolved = value_type(value)
		compatible = destination == source_type or (destination in {"float", "double"} and source_type == "int") or (destination == "double" and source_type == "float")
		if not compatible:
			raise CompileError("semantic", f"Cannot assign {source_type} to {destination}.", line, column)
		return resolved

	for statement in program["statements"]:
		name = statement["identifier"]
		if statement["type"] == "Declaration":
			if name in symbols:
				raise CompileError("semantic", f"Variable {name!r} is already declared.", statement["line"], statement["column"])
			symbol = {"type": statement["var_type"], "value": None, "declared_line": statement["line"]}
			symbols[name] = symbol
			if statement["value"] is not None:
				symbol["value"] = assign_value(symbol["type"], statement["value"], statement["line"], statement["column"])
		else:
			symbol = symbols.get(name)
			if symbol is None:
				raise CompileError("semantic", f"Variable {name!r} is not declared.", statement["line"], statement["column"])
			symbol["value"] = assign_value(symbol["type"], statement["value"], statement["line"], statement["column"])
	return symbols


def compile_source(source: str) -> dict[str, Any]:
	tokens = tokenize(source)
	program = Parser(tokens).parse()
	symbols = analyze(program)
	return {
		"success": True,
		"phase": "complete",
		"message": "Compilation completed successfully.",
		"tokens": [token.as_dict() for token in tokens if token.type != "END_MARKER"],
		"ast": program,
		"symbols": symbols,
		"stats": {"token_count": len(tokens) - 1, "statement_count": len(program["statements"]), "symbol_count": len(symbols)},
	}


@app.get("/")
def index():
	return render_template("index.html")


@app.post("/compile")
def compile_endpoint():
	payload = request.get_json(silent=True)
	source = payload.get("source") if isinstance(payload, dict) else request.form.get("source")
	if not isinstance(source, str):
		return jsonify({"success": False, "error": {"phase": "request", "message": "Provide source code as a string."}}), 400
	if len(source) > MAX_SOURCE_LENGTH:
		return jsonify({"success": False, "error": {"phase": "request", "message": f"Source is limited to {MAX_SOURCE_LENGTH} characters."}}), 413
	try:
		return jsonify(compile_source(source))
	except CompileError as error:
		return jsonify({"success": False, "phase": error.phase, "error": error.as_dict()})


if __name__ == "__main__":
	import os
	port = int(os.environ.get("PORT", 5001))
	print(f"Starting server on http://localhost:{port}")
	app.run(host="0.0.0.0", port=port, debug=False)

