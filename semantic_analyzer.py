
"""
Semantic Analyzer for the Variable Declaration Compiler.

Responsibilities:
1. Detect use of undeclared variables.
2. Check data type mismatches during initialization.
3. Check data type mismatches during assignment.
4. Check declaration order.
5. Report semantic errors with line and column numbers.

Compatible with the AST structure defined in parser.py.
"""

from parser import Program, Declaration, Assignment, Value


class SemanticError:
    """Stores information about a semantic error."""

    def __init__(self, message, line=None, column=None):
        self.message = message
        self.line = line
        self.column = column

    def __str__(self):
        location = ""

        if self.line is not None:
            location = f"Line {self.line}"

            if self.column is not None:
                location += f", Column {self.column}"

            location += ": "

        return location + self.message


class SemanticAnalyzer:
    """Checks variable declarations, initialization and assignments."""

    def __init__(self):
        # Variable name -> data type
        self.symbol_table = {}

        # List of semantic errors
        self.errors = []

    def add_error(self, message, node=None):
        """Record an error with its source location."""
        self.errors.append(
            SemanticError(
                message,
                getattr(node, "line", None),
                getattr(node, "column", None)
            )
        )

    def get_value_type(self, value):
        """
        Determine the data type of a Value AST node.

        Supported types:
        int, float, double, char, bool
        """

        if value is None:
            return None

        value_type = value.value_type
        actual_value = value.value

        # An identifier must already be declared.
        if value_type == "ID":
            variable_name = str(actual_value)

            if variable_name not in self.symbol_table:
                self.add_error(
                    f"Variable '{variable_name}' is used "
                    "before declaration.",
                    value
                )
                return None

            return self.symbol_table[variable_name]

        # Numeric literals can be integers or floating-point values.
        if value_type == "NUMBER":
            text = str(actual_value)

            try:
                number = float(text)

                if not number.is_integer() or (
                    "." in text or "e" in text.lower()
                ):
                    return "float"

                return "int"

            except (ValueError, OverflowError):
                self.add_error(
                    f"Invalid numeric literal '{actual_value}'.",
                    value
                )
                return None

        # Character literal, for example 'A' or 'x'.
        if value_type == "CHAR_LITERAL":
            return "char"

        # Boolean literal: true or false.
        if value_type in {"BOOL_LITERAL", "BOOLEAN"}:
            return "bool"

        # Fallback for lexers that classify literals differently.
        text = str(actual_value)

        if text in {"true", "false"}:
            return "bool"

        self.add_error(
            f"Unknown value type '{value_type}'.",
            value
        )
        return None

    def check_type(self, expected_type, actual_type, node, context):
        """Check whether two data types match."""

        if actual_type is None:
            # The value has already produced an error.
            return

        if expected_type != actual_type:
            self.add_error(
                f"Type mismatch in {context}: expected "
                f"'{expected_type}', but got '{actual_type}'.",
                node
            )

    def analyze_declaration(self, node):
        """Check a variable declaration and its initializer."""

        name = node.identifier
        declared_type = node.var_type

        # Check initializer before registering the variable.
        # This also prevents using a variable before declaration.
        if node.value is not None:
            actual_type = self.get_value_type(node.value)

            self.check_type(
                declared_type,
                actual_type,
                node,
                f"initialization of variable '{name}'"
            )

        # Member 4 handles duplicate declarations.
        # Avoid overwriting an existing declaration.
        if name in self.symbol_table:
            self.add_error(
                f"Variable '{name}' has already been declared.",
                node
            )
            return

        self.symbol_table[name] = declared_type

    def analyze_assignment(self, node):
        """Check assignment to an existing variable."""

        name = node.identifier

        # The target variable must be declared first.
        if name not in self.symbol_table:
            self.add_error(
                f"Variable '{name}' is assigned before declaration.",
                node
            )
            return

        expected_type = self.symbol_table[name]
        actual_type = self.get_value_type(node.value)

        self.check_type(
            expected_type,
            actual_type,
            node,
            f"assignment to variable '{name}'"
        )

    def analyze(self, ast):
        """
        Analyze a Program AST.

        Returns:
            List of SemanticError objects.
            An empty list means no semantic errors were found.
        """

        self.symbol_table = {}
        self.errors = []

        if not isinstance(ast, Program):
            raise TypeError(
                "SemanticAnalyzer expects a Program AST from parser.py."
            )

        for statement in ast.statements:

            if isinstance(statement, Declaration):
                self.analyze_declaration(statement)

            elif isinstance(statement, Assignment):
                self.analyze_assignment(statement)

            else:
                self.add_error(
                    f"Unsupported AST statement: "
                    f"{type(statement).__name__}."
                )

        return self.errors


def analyze_ast(ast):
    """Convenience function for use by app.py."""

    analyzer = SemanticAnalyzer()
    errors = analyzer.analyze(ast)

    return {
        "success": len(errors) == 0,
        "errors": [str(error) for error in errors],
        "symbol_table": analyzer.symbol_table
    }


# --------------------------------------------------
# Standalone testing
# --------------------------------------------------

if __name__ == "__main__":
    from parser import parse, Token

    sample_tokens = [
        Token("TYPE", "int", 1, 1),
        Token("ID", "age", 1, 5),
        Token(";", ";", 1, 8),

        Token("TYPE", "float", 2, 1),
        Token("ID", "mark", 2, 7),
        Token("=", "=", 2, 12),
        Token("NUMBER", "95.5", 2, 14),
        Token(";", ";", 2, 18),

        Token("ID", "age", 3, 1),
        Token("=", "=", 3, 5),
        Token("NUMBER", "20", 3, 7),
        Token(";", ";", 3, 9),

        Token("ID", "age", 4, 1),
        Token("=", "=", 4, 5),
        Token("CHAR_LITERAL", "'A'", 4, 7),
        Token(";", ";", 4, 10),

        Token("ID", "unknown", 5, 1),
        Token("=", "=", 5, 9),
        Token("NUMBER", "10", 5, 11),
        Token(";", ";", 5, 13),
    ]

    ast = parse(sample_tokens)

    analyzer = SemanticAnalyzer()
    errors = analyzer.analyze(ast)

    print("SEMANTIC ANALYSIS")
    print("-----------------")

    if errors:
        for error in errors:
            print("ERROR:", error)
    else:
        print("No semantic errors found.")

    print("\nSYMBOL TABLE")
    print(analyzer.symbol_table)

