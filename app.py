"""Flask interface for the variable declaration compiler.

Integrates all compiler phases using the dedicated module files:
  - lexer.py          → lexical analysis / tokenisation
  - parser.py         → recursive-descent parser / AST construction
  - semantic_analyzer.py → semantic checks (multiple errors collected)
  - symbol_table.py   → symbol-table construction via SymbolTable class
  - grammar.py        → CFG rules, FIRST / FOLLOW sets (exposed to UI)
"""

from __future__ import annotations

import sys
import os

from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Module imports – each dedicated file is used instead of inline code
# ---------------------------------------------------------------------------
from lexer import tokenize, LexerError                        # lexer.py
from parser import parse, ParserError, Program                # parser.py
from semantic_analyzer import SemanticAnalyzer                # semantic_analyzer.py
from symbol_table import build_symbol_table, SymbolTable      # symbol_table.py
from grammar import GRAMMAR, FIRST, FOLLOW                    # grammar.py

app = Flask(__name__)
MAX_SOURCE_LENGTH = 20_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grammar_payload() -> dict:
    """Serialise GRAMMAR / FIRST / FOLLOW sets into JSON-friendly dicts."""
    rules = {
        non_terminal: [" ".join(prod) for prod in productions]
        for non_terminal, productions in GRAMMAR.items()
    }
    first = {k: sorted(v) for k, v in FIRST.items()}
    follow = {k: sorted(v) for k, v in FOLLOW.items()}
    return {"rules": rules, "first": first, "follow": follow}


def _token_dicts(tokens) -> list[dict]:
    """Convert lexer Token objects to plain dicts (exclude END_MARKER)."""
    result = []
    for tok in tokens:
        if tok.type == "END_MARKER":
            continue
        result.append({
            "type": tok.type,
            "value": tok.value if not isinstance(tok.value, bool) else str(tok.value).lower(),
            "line": tok.line,
            "column": tok.column,
        })
    return result


def _ast_dict(program: Program) -> dict:
    """Use the parser's own to_dict() serialiser."""
    return program.to_dict()


def _symbols_dict(table: SymbolTable) -> dict:
    """Return symbol table as a JSON-friendly dict (name → {type, value, declared_line})."""
    return table.as_dict()


def _semantic_errors_list(errors) -> list[dict]:
    """Convert SemanticError objects to dicts."""
    result = []
    for err in errors:
        result.append({
            "message": err.message,
            "line": err.line,
            "column": err.column,
        })
    return result


# ---------------------------------------------------------------------------
# Core compile pipeline
# ---------------------------------------------------------------------------

def compile_source(source: str) -> dict:
    """Run all compiler phases and return a structured result dict."""

    pipeline: list[dict] = []   # per-phase status log shown in UI

    # ── Phase 1 : Lexical Analysis ──────────────────────────────────────────
    try:
        tokens = tokenize(source)
        token_dicts = _token_dicts(tokens)
        pipeline.append({
            "phase": "lexical",
            "label": "LEX",
            "status": "ok",
            "detail": f"{len(token_dicts)} token(s) produced",
        })
    except LexerError as exc:
        pipeline.append({
            "phase": "lexical",
            "label": "LEX",
            "status": "error",
            "detail": exc.message,
        })
        return {
            "success": False,
            "phase": "lexical",
            "error": {
                "phase": "lexical",
                "message": exc.message,
                "line": exc.line,
                "column": exc.column,
            },
            "pipeline": pipeline,
            "grammar": _grammar_payload(),
        }

    # ── Phase 2 : Syntax Analysis ────────────────────────────────────────────
    try:
        ast = parse(tokens)
        ast_dict = _ast_dict(ast)
        pipeline.append({
            "phase": "syntax",
            "label": "PARSE",
            "status": "ok",
            "detail": f"{len(ast.statements)} statement(s) parsed",
        })
    except ParserError as exc:
        pipeline.append({
            "phase": "syntax",
            "label": "PARSE",
            "status": "error",
            "detail": exc.raw_message,
        })
        return {
            "success": False,
            "phase": "syntax",
            "error": {
                "phase": "syntax",
                "message": exc.raw_message,
                "line": exc.line,
                "column": exc.column,
            },
            "tokens": token_dicts,
            "pipeline": pipeline,
            "grammar": _grammar_payload(),
        }

    # ── Phase 3 : Semantic Analysis ──────────────────────────────────────────
    analyzer = SemanticAnalyzer()
    sem_errors = analyzer.analyze(ast)

    if sem_errors:
        errors_list = _semantic_errors_list(sem_errors)
        first_err = errors_list[0]
        pipeline.append({
            "phase": "semantic",
            "label": "CHECK",
            "status": "error",
            "detail": f"{len(errors_list)} semantic error(s)",
        })
        return {
            "success": False,
            "phase": "semantic",
            "error": {
                "phase": "semantic",
                "message": first_err["message"],
                "line": first_err["line"],
                "column": first_err["column"],
            },
            "semantic_errors": errors_list,   # ← full list for UI
            "tokens": token_dicts,
            "ast": ast_dict,
            "pipeline": pipeline,
            "grammar": _grammar_payload(),
        }

    pipeline.append({
        "phase": "semantic",
        "label": "CHECK",
        "status": "ok",
        "detail": "No semantic errors",
    })

    # ── Phase 4 : Symbol Table Construction ─────────────────────────────────
    try:
        symbol_table = build_symbol_table(ast)
        sym_dict = _symbols_dict(symbol_table)
    except (ValueError, KeyError, TypeError) as exc:
        # symbol_table raises these on semantic violations; shouldn't happen
        # because SemanticAnalyzer already ran, but guard for safety.
        sym_dict = analyzer.symbol_table  # fall back to simpler dict

    # ── Success ──────────────────────────────────────────────────────────────
    return {
        "success": True,
        "phase": "complete",
        "message": "Compilation completed successfully.",
        "tokens": token_dicts,
        "ast": ast_dict,
        "symbols": sym_dict,
        "stats": {
            "token_count": len(token_dicts),
            "statement_count": len(ast.statements),
            "symbol_count": len(sym_dict),
        },
        "pipeline": pipeline,
        "grammar": _grammar_payload(),
    }


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/grammar")
def grammar_endpoint():
    """Standalone endpoint: return grammar / FIRST / FOLLOW sets as JSON."""
    return jsonify(_grammar_payload())


@app.post("/compile")
def compile_endpoint():
    payload = request.get_json(silent=True)
    source = payload.get("source") if isinstance(payload, dict) else request.form.get("source")
    if not isinstance(source, str):
        return jsonify({
            "success": False,
            "error": {"phase": "request", "message": "Provide source code as a string."},
        }), 400
    if len(source) > MAX_SOURCE_LENGTH:
        return jsonify({
            "success": False,
            "error": {"phase": "request", "message": f"Source is limited to {MAX_SOURCE_LENGTH} characters."},
        }), 413
    result = compile_source(source)
    status_code = 200
    return jsonify(result), status_code


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
