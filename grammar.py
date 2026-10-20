# CFG and Grammar Rules for Variable Declaration Compiler
EPSILON = "ε"
END_MARKER = "$"

# Context-Free Grammar (CFG)
GRAMMAR = {
    "Program": [
        ["StatementList"]
    ],

    "StatementList": [
        ["Statement", "StatementList"],
        [EPSILON]
    ],

    "Statement": [
        ["Declaration"],
        ["Assignment"]
    ],

    "Declaration": [
        ["Type", "ID", ";"],
        ["Type", "ID", "=", "Value", ";"]
    ],

    "Assignment": [
        ["ID", "=", "Value", ";"]
    ],

    "Type": [
        ["int"],
        ["float"],
        ["double"],
        ["char"],
        ["bool"]
    ],

    "Value": [
        ["ID"],
        ["NUMBER"],
        ["CHAR_LITERAL"],
        ["BOOL_LITERAL"]
    ]
}


# FIRST Sets
FIRST = {
    "Program": {
        "int", "float", "double", "char", "bool",
        "ID", EPSILON
    },

    "StatementList": {
        "int", "float", "double", "char", "bool",
        "ID", EPSILON
    },

    "Statement": {
        "int", "float", "double", "char", "bool", "ID"
    },

    "Declaration": {
        "int", "float", "double", "char", "bool"
    },

    "Assignment": {"ID"},

    "Type": {"int", "float", "double", "char", "bool"},

    "Value": {"ID", "NUMBER", "CHAR_LITERAL", "BOOL_LITERAL"}
}


# FOLLOW Sets
FOLLOW = {
    "Program": {END_MARKER},

    "StatementList": {END_MARKER},

    "Statement": {
        "int", "float", "double", "char", "bool", "ID",
        END_MARKER
    },

    "Declaration": {
        "int", "float", "double", "char", "bool", "ID",
        END_MARKER
    },

    "Assignment": {
        "int", "float", "double", "char", "bool", "ID",
        END_MARKER
    },

    "Type": {"ID"},

    "Value": {";"}
}


def display_grammar():
    """Display the CFG production rules."""
    print("VARIABLE DECLARATION COMPILER")
    print("\nCONTEXT-FREE GRAMMAR (CFG)\n")

    for non_terminal, productions in GRAMMAR.items():
        rules = [" ".join(p) for p in productions]
        print(f"{non_terminal} -> {' | '.join(rules)}")


def display_first_follow():
    """Display FIRST and FOLLOW sets."""
    print("\nFIRST SETS")

    for symbol, values in FIRST.items():
        print(f"FIRST({symbol}) = {values}")

    print("\nFOLLOW SETS")

    for symbol, values in FOLLOW.items():
        print(f"FOLLOW({symbol}) = {values}")


if __name__ == "__main__":
    display_grammar()
    display_first_follow()
