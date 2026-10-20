# Variable Declaration Compiler

## About the Project
The Variable Declaration Compiler is a mini compiler project developed to analyze variable declarations and assignment statements. It checks whether the input follows the defined grammar rules and helps identify syntax and semantic errors.

## Features
- Lexical analysis to identify tokens.
- Context-Free Grammar (CFG) for variable declarations and assignments.
- FIRST and FOLLOW sets for grammar analysis.
- Syntax analysis to check the structure of statements.
- Symbol table to store variable information.
- Semantic analysis to check undeclared variables and type mismatches.
- Simple user interface for entering code and viewing results.

## Supported Data Types
- `int`
- `float`
- `double`
- `char`
- `bool`

## Example Input

```c
int age;
float mark = 95.5;
char grade = 'A';
bool isActive = true;
age = 20;
```

## Project Modules

| File / Module | Responsibility |
|---|---|
| `lexer.py` | Identifies tokens in the input |
| `grammar.py` | Defines CFG rules, FIRST sets, and FOLLOW sets |
| `parser.py` | Checks syntax using grammar rules |
| `symbol_table.py` | Stores variable details and checks duplicate declarations |
| `semantic_analyzer.py` | Checks semantic errors |
| `app.py` | Connects the modules and runs the application |
| `test_compiler.py` | Tests compiler functionality |

The frontend files, if included, provide the interface for entering source code and displaying compilation results.

## Technologies Used
- Python
- HTML, CSS and JavaScript (for the frontend)
- Flask (for the web application, if implemented)
- Git and GitHub for version control

## How to Run
1. Clone the repository.
2. Open the project folder in a terminal.
3. Install the required dependencies, if any.
4. Run the application using the instructions agreed upon by the team.

For the grammar module alone, run:

```bash
python grammar.py
```

This displays the CFG production rules and the predefined FIRST and FOLLOW sets.

## Project Team
Developed collaboratively as an academic mini project.

## Note
The compiler is an educational project intended to demonstrate the basic stages of compiler design. Features depend on the modules implemented and integrated by the team.
