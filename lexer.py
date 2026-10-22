
        # Line comments are accepted as a convenient source-code feature.
        if source_code.startswith("//", i):
            while i < length and source_code[i] != "\n":
                i += 1
                column += 1
            continue

        start_line, start_column = line, column

        if char.isalpha() or char == "_":
            start = i
            while i < length and (source_code[i].isalnum() or source_code[i] == "_"):
                i += 1
                column += 1
            word = source_code[start:i]
            if word in DATA_TYPES:
                token_type = "TYPE"
            elif word in {"true", "false"}:
                token_type = "BOOL_LITERAL"
            else:
                token_type = "ID"
            tokens.append(Token(token_type, word, start_line, start_column))
            continue

        if char.isdigit():
            start = i
            has_dot = False
            while i < length and source_code[i].isdigit():
                i += 1
                column += 1
            if i < length and source_code[i] == ".":
                has_dot = True
                i += 1
                column += 1
                if i >= length or not source_code[i].isdigit():
                    raise LexerError("a decimal point must be followed by digits", start_line, start_column)
                while i < length and source_code[i].isdigit():
                    i += 1
                    column += 1
            # Optional scientific notation, e.g. 1e3 or 2.5E-2.
            if i < length and source_code[i] in "eE":
                has_dot = True
                i += 1
                column += 1
                if i < length and source_code[i] in "+-":
                    i += 1
                    column += 1
                exponent_start = i
                while i < length and source_code[i].isdigit():
                    i += 1
                    column += 1
                if exponent_start == i:
                    raise LexerError("an exponent must contain digits", start_line, start_column)
            number = source_code[start:i]
            # Parser expects NUMBER and preserves its spelling as a string.
            tokens.append(Token("NUMBER", number, start_line, start_column))
            continue

        if char == "'":
            i += 1
            column += 1
            if i >= length or source_code[i] in "\r\n'":
                raise LexerError("expected one character inside single quotes", start_line, start_column)
            if source_code[i] == "\\":
                i += 1
                column += 1
                if i >= length or source_code[i] in "\r\n":
                    raise LexerError("incomplete escape sequence in character literal", start_line, start_column)
                escapes = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'"}
                value = escapes.get(source_code[i])
                if value is None:
                    raise LexerError(f"unsupported escape sequence \\{source_code[i]}", start_line, start_column)
            else:
                value = source_code[i]
            i += 1
            column += 1
            if i >= length or source_code[i] != "'":
                raise LexerError("character literal must contain exactly one character", start_line, start_column)
            i += 1
            column += 1
            tokens.append(Token("CHAR_LITERAL", value, start_line, start_column))
            continue

        punctuation = {"=": "=", ";": ";"}
        if char in punctuation:
            tokens.append(Token(punctuation[char], char, start_line, start_column))
            i += 1
            column += 1
            continue

        raise LexerError(f"unexpected character {char!r}", line, column)

    tokens.append(Token("END_MARKER", "$", line, column))
    return tokens


if __name__ == "__main__":
    example = """int age = 20;
float mark = 95.5;
char grade = 'A';
bool passed = true;
age = 21;
"""
    for item in tokenize(example):
        print(item)
