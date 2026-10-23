from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass
class Symbol:
    name: str
    data_type: str
    value: Any = None
    declared_line: Optional[int] = None


class SymbolTable:
    def __init__(self) -> None:
        self._symbols: Dict[str, Symbol] = {}

    def declare(self, name: str, data_type: str, line: Optional[int] = None) -> Symbol:
        if name in self._symbols:
            raise ValueError(self._message(f"Variable '{name}' already declared", line))
        symbol = Symbol(name=name, data_type=data_type, declared_line=line)
        self._symbols[name] = symbol
        return symbol

    def lookup(self, name: str, line: Optional[int] = None) -> Symbol:
        if name not in self._symbols:
            raise KeyError(self._message(f"Variable '{name}' not declared", line))
        return self._symbols[name]

    def assign(self, name: str, value: Any, line: Optional[int] = None) -> Symbol:
        symbol = self.lookup(name, line)
        val_type = None
        if getattr(value, "value_type", None) == "ID":
            rhs_symbol = self.lookup(str(value.value), line)
            val_type = rhs_symbol.data_type
            value = rhs_symbol.value
        else:
            val_type = _infer_value_type(value)
        if val_type is not None and not _is_compatible(symbol.data_type, val_type):
            raise TypeError(self._message(f"Cannot assign {val_type} to {symbol.data_type}", line))
        symbol.value = _value_contents(value)
        return symbol

    def symbols(self) -> Iterable[Symbol]:
        return self._symbols.values()

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        """Return a JSON-friendly view of the table."""
        return {
            name: {
                "type": symbol.data_type,
                "value": symbol.value,
                "declared_line": symbol.declared_line,
            }
            for name, symbol in self._symbols.items()
        }

    def display(self) -> None:
        """Print the current table in aligned columns."""
        print(f"{'Name':<16} {'Type':<10} {'Value':<20} {'Line'}")
        print("-" * 58)
        for symbol in self._symbols.values():
            value = "<uninitialized>" if symbol.value is None else str(symbol.value)
            line = "-" if symbol.declared_line is None else str(symbol.declared_line)
            print(f"{symbol.name:<16} {symbol.data_type:<10} {value:<20} {line}")

    @staticmethod
    def _message(message: str, line: Optional[int]) -> str:
        return f"Semantic Error at line {line}: {message}" if line is not None else f"Semantic Error: {message}"


def build_symbol_table(program: Any) -> SymbolTable:
    """Build and return a table from a ``parser.Program`` AST.

    Declarations are processed in source order. Identifier initializers and
    assignments must refer to variables declared earlier.
    """
    table = SymbolTable()
    for statement in program.statements:
        kind = statement.__class__.__name__
        if kind == "Declaration":
            initial_value = getattr(statement, "value", None)
            # Declare before evaluating the initializer, so ``int x = x;`` is
            # recognized as a declared name (its value remains unknown).
            table.declare(
                statement.identifier,
                statement.var_type,
                line=getattr(statement, "line", None),
            )
            if initial_value is not None:
                _check_identifier_reference(table, initial_value)
                table.assign(
                    statement.identifier,
                    initial_value,
                    line=getattr(statement, "line", None),
                )
        elif kind == "Assignment":
            _check_identifier_reference(table, statement.value)
            table.assign(
                statement.identifier,
                statement.value,
                line=getattr(statement, "line", None),
            )
        else:
            raise TypeError(f"Unsupported AST statement: {kind}")
    return table


def _check_identifier_reference(table: SymbolTable, value: Any) -> None:
    if getattr(value, "value_type", None) == "ID":
        table.lookup(str(value.value))


def _value_contents(value: Any) -> Any:
    """Unwrap the parser's Value AST node; leave ordinary Python values alone."""
    return getattr(value, "value", value)


def _infer_value_type(value: Any) -> Optional[str]:
    """Infer a primitive type from a parser Value node or a Python value."""
    value_type = getattr(value, "value_type", None)
    if value_type == "ID":
        # The caller resolves the identifier against the table separately.
        return None
    if value_type == "NUMBER":
        raw = str(getattr(value, "value", ""))
        return "float" if any(mark in raw.lower() for mark in (".", "e")) else "int"
    if value_type == "CHAR_LITERAL":
        return "char"
    if value_type == "BOOL_LITERAL":
        return "bool"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "char" if len(value) == 1 else None
    return None


def _is_compatible(destination: str, source: str) -> bool:
    """Allow exact matches and widening numeric conversions."""
    if destination == source:
        return True
    widening = {"int": {"float", "double"}, "float": {"double"}}
    return source in widening.get(destination, set())


if __name__ == "__main__":
    try:
        from parser import parse_source
    except ImportError as exc:
        raise SystemExit("Place symbol_table.py beside parser.py to run the example.") from exc

    source = "int age = 20; float mark = 95.5; age = 21;"
    try:
        table = build_symbol_table(parse_source(source))
    except NotImplementedError as exc:
        raise SystemExit("The parser needs lexer.tokenize; import build_symbol_table after parsing tokens instead.") from exc
    table.display()
