"""
Lexical Analyzer for C and C++ source code.
Strips comments and formatting while preserving token types and source locations.
"""
import re
from typing import List, Tuple, Optional
from .token_types import TokenType, SourceLocation, Token, C_CPP_KEYWORDS


class LexerError(Exception):
    """Raised when lexical analysis encounters an unrecoverable syntax error."""
    pass


class CLexer:
    """
    Tokenizer for C and C++ source code.
    Extracts tokens while filtering out comments and whitespace.
    Retains precise source location coordinates for visual match highlighting.
    """

    # Multi-character operators sorted by length descending for greedy matching
    OPERATORS = [
        # 3-char operators
        ">>=", "<<=", "...", "->*",
        # 2-char operators
        "::", "->", "++", "--", "==", "!=", "<=", ">=", "&&", "||",
        "<<", ">>", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
        ".*",
        # 1-char operators
        "+", "-", "*", "/", "%", "=", "<", ">", "!", "~", "&", "|", "^", "?", ":"
    ]

    PUNCTUATORS = {
        "(", ")", "[", "]", "{", "}", ";", ",", "."
    }

    def __init__(self, source_code: str, filename: str = "<source>"):
        self.source = source_code
        self.filename = filename
        self.length = len(source_code)
        self.cursor = 0
        self.line = 1
        self.column = 1
        self.stripped_comments: List[Tuple[str, SourceLocation, SourceLocation]] = []

    def _peek(self, offset: int = 0) -> str:
        idx = self.cursor + offset
        if idx < self.length:
            return self.source[idx]
        return ""

    def _advance(self) -> str:
        if self.cursor >= self.length:
            return ""
        ch = self.source[self.cursor]
        self.cursor += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _get_current_location(self) -> SourceLocation:
        return SourceLocation(line=self.line, column=self.column, offset=self.cursor)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.cursor < self.length:
            ch = self._peek()

            # 1. Whitespace (spaces, tabs, newlines, carriage returns) - ignore
            if ch in (" ", "\t", "\r", "\n", "\v", "\f"):
                self._advance()
                continue

            # 2. Single-line comment: // ...
            if ch == "/" and self._peek(1) == "/":
                start_loc = self._get_current_location()
                comment_text = []
                self._advance()  # /
                self._advance()  # /
                while self.cursor < self.length and self._peek() != "\n":
                    comment_text.append(self._advance())
                end_loc = self._get_current_location()
                self.stripped_comments.append(("".join(comment_text).strip(), start_loc, end_loc))
                continue

            # 3. Multi-line comment: /* ... */
            if ch == "/" and self._peek(1) == "*":
                start_loc = self._get_current_location()
                comment_text = []
                self._advance()  # /
                self._advance()  # *
                while self.cursor < self.length:
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()  # *
                        self._advance()  # /
                        break
                    comment_text.append(self._advance())
                end_loc = self._get_current_location()
                self.stripped_comments.append(("".join(comment_text).strip(), start_loc, end_loc))
                continue

            # 4. Preprocessor directives: #include, #define, etc.
            if ch == "#":
                start_loc = self._get_current_location()
                prep_line = []
                while self.cursor < self.length:
                    curr = self._peek()
                    if curr == "\n":
                        # Check for line continuation with \
                        if prep_line and prep_line[-1] == "\\":
                            prep_line.pop()
                            self._advance()
                            continue
                        break
                    prep_line.append(self._advance())
                end_loc = self._get_current_location()
                content = "".join(prep_line).strip()
                tokens.append(Token(
                    type=TokenType.PREPROCESSOR,
                    value=content,
                    location=start_loc,
                    end_location=end_loc
                ))
                continue

            # 5. String literals: " ... " or R"( ... )"
            if ch == '"':
                tokens.append(self._lex_string_literal())
                continue
            if ch == "R" and self._peek(1) == '"' and self._peek(2) == "(":
                tokens.append(self._lex_raw_string_literal())
                continue

            # 6. Character literals: ' ... '
            if ch == "'":
                tokens.append(self._lex_char_literal())
                continue

            # 7. Numbers (integers, floats, hex, binary)
            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                tokens.append(self._lex_number_literal())
                continue

            # 8. Identifiers and Keywords: [a-zA-Z_][a-zA-Z0-9_]*
            if ch.isalpha() or ch == "_":
                tokens.append(self._lex_identifier_or_keyword())
                continue

            # 9. Multi-character and single-character Operators
            matched_op = self._match_operator()
            if matched_op:
                tokens.append(matched_op)
                continue

            # 10. Punctuators: (, ), {, }, [, ], ;, ,, .
            if ch in self.PUNCTUATORS:
                start_loc = self._get_current_location()
                val = self._advance()
                end_loc = self._get_current_location()
                tokens.append(Token(
                    type=TokenType.PUNCTUATOR,
                    value=val,
                    location=start_loc,
                    end_location=end_loc
                ))
                continue

            # 11. Unknown / unexpected character fallback
            start_loc = self._get_current_location()
            val = self._advance()
            end_loc = self._get_current_location()
            tokens.append(Token(
                type=TokenType.UNKNOWN,
                value=val,
                location=start_loc,
                end_location=end_loc
            ))

        return tokens

    def _lex_string_literal(self) -> Token:
        start_loc = self._get_current_location()
        chars = [self._advance()]  # opening "
        escaped = False

        while self.cursor < self.length:
            ch = self._advance()
            chars.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                break

        end_loc = self._get_current_location()
        return Token(
            type=TokenType.LITERAL_STRING,
            value="".join(chars),
            location=start_loc,
            end_location=end_loc
        )

    def _lex_raw_string_literal(self) -> Token:
        start_loc = self._get_current_location()
        chars = [self._advance(), self._advance(), self._advance()]  # R ( "
        while self.cursor < self.length:
            if self._peek() == ")" and self._peek(1) == '"':
                chars.append(self._advance())
                chars.append(self._advance())
                break
            chars.append(self._advance())
        end_loc = self._get_current_location()
        return Token(
            type=TokenType.LITERAL_STRING,
            value="".join(chars),
            location=start_loc,
            end_location=end_loc
        )

    def _lex_char_literal(self) -> Token:
        start_loc = self._get_current_location()
        chars = [self._advance()]  # opening '
        escaped = False

        while self.cursor < self.length:
            ch = self._advance()
            chars.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                break

        end_loc = self._get_current_location()
        return Token(
            type=TokenType.LITERAL_CHAR,
            value="".join(chars),
            location=start_loc,
            end_location=end_loc
        )

    def _lex_number_literal(self) -> Token:
        start_loc = self._get_current_location()
        chars = []

        # Hexadecimal (0x...) or Binary (0b...)
        if self._peek() == "0" and self._peek(1) in ("x", "X"):
            chars.append(self._advance())
            chars.append(self._advance())
            while self._peek().isalnum() or self._peek() == ".":
                chars.append(self._advance())
        elif self._peek() == "0" and self._peek(1) in ("b", "B"):
            chars.append(self._advance())
            chars.append(self._advance())
            while self._peek() in ("0", "1", "_"):
                chars.append(self._advance())
        else:
            has_dot = False
            has_exp = False
            while self.cursor < self.length:
                ch = self._peek()
                if ch.isdigit():
                    chars.append(self._advance())
                elif ch == "." and not has_dot:
                    has_dot = True
                    chars.append(self._advance())
                elif ch in ("e", "E") and not has_exp:
                    has_exp = True
                    chars.append(self._advance())
                    if self._peek() in ("+", "-"):
                        chars.append(self._advance())
                elif ch in ("f", "F", "l", "L", "u", "U"):
                    chars.append(self._advance())
                else:
                    break

        end_loc = self._get_current_location()
        return Token(
            type=TokenType.LITERAL_NUMBER,
            value="".join(chars),
            location=start_loc,
            end_location=end_loc
        )

    def _lex_identifier_or_keyword(self) -> Token:
        start_loc = self._get_current_location()
        chars = []

        while self.cursor < self.length:
            ch = self._peek()
            if ch.isalnum() or ch == "_":
                chars.append(self._advance())
            else:
                break

        ident = "".join(chars)
        end_loc = self._get_current_location()

        token_type = TokenType.KEYWORD if ident in C_CPP_KEYWORDS else TokenType.IDENTIFIER
        return Token(
            type=token_type,
            value=ident,
            location=start_loc,
            end_location=end_loc
        )

    def _match_operator(self) -> Optional[Token]:
        for op in self.OPERATORS:
            op_len = len(op)
            if self.source[self.cursor:self.cursor + op_len] == op:
                start_loc = self._get_current_location()
                for _ in range(op_len):
                    self._advance()
                end_loc = self._get_current_location()
                return Token(
                    type=TokenType.OPERATOR,
                    value=op,
                    location=start_loc,
                    end_location=end_loc
                )
        return None
