"""
Token definitions and classifications for CodeGuard C/C++ lexer.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Set


class TokenType(Enum):
    KEYWORD = auto()
    IDENTIFIER = auto()
    LITERAL_NUMBER = auto()
    LITERAL_STRING = auto()
    LITERAL_CHAR = auto()
    OPERATOR = auto()
    PUNCTUATOR = auto()
    PREPROCESSOR = auto()
    COMMENT = auto()  # Kept in enum for explicit detection, stripped before normalization
    WHITESPACE = auto()  # Kept in enum for completeness, skipped during token stream generation
    UNKNOWN = auto()


@dataclass(frozen=True)
class SourceLocation:
    line: int        # 1-indexed
    column: int      # 1-indexed
    offset: int      # 0-indexed byte/char offset in source


@dataclass
class Token:
    type: TokenType
    value: str
    location: SourceLocation
    end_location: SourceLocation

    @property
    def span(self):
        return (self.location.offset, self.end_location.offset)

    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', L{self.location.line}:C{self.location.column})"


# C and C++ Language Keywords (Standard C11 / C++17)
C_CPP_KEYWORDS: Set[str] = {
    # C Keywords
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Alignas", "_Alignof",
    "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary", "_Noreturn",
    "_Static_assert", "_Thread_local",
    # C++ Keywords
    "alignas", "alignof", "and", "and_eq", "asm", "bitand", "bitor",
    "bool", "catch", "char16_t", "char32_t", "char8_t", "class", "compl",
    "concept", "consteval", "constexpr", "constinit", "const_cast", "co_await",
    "co_return", "co_yield", "decltype", "delete", "dynamic_cast", "explicit",
    "export", "false", "friend", "mutable", "namespace", "new", "noexcept",
    "not", "not_eq", "nullptr", "operator", "or", "or_eq", "override",
    "private", "protected", "public", "reinterpret_cast", "requires",
    "static_assert", "static_cast", "template", "this", "thread_local",
    "throw", "true", "try", "typeid", "typename", "using", "virtual",
    "wchar_t", "xor", "xor_eq",
}

# Common C/C++ Standard Library Functions, Types and Symbols (Whitelisted from normalization)
# When students use printf, malloc, std::vector, etc., those retain their semantics.
STDLIB_SYMBOLS: Set[str] = {
    # C Standard I/O & Memory
    "printf", "scanf", "fprintf", "fscanf", "sprintf", "sscanf", "snprintf",
    "puts", "gets", "fgets", "fputs", "getchar", "putchar", "fopen", "fclose",
    "fread", "fwrite", "fseek", "ftell", "rewind", "fflush", "perror",
    "malloc", "calloc", "realloc", "free", "exit", "abort", "atexit",
    "atoi", "atof", "atol", "atoll", "strtol", "strtod", "rand", "srand",
    "qsort", "bsearch", "abs", "labs",
    # C String & Math
    "strlen", "strcpy", "strncpy", "strcat", "strncat", "strcmp", "strncmp",
    "strchr", "strrchr", "strstr", "strtok", "memset", "memcpy", "memmove",
    "memcmp", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sqrt",
    "pow", "exp", "log", "log10", "ceil", "floor", "fabs",
    # C Types
    "size_t", "ptrdiff_t", "int8_t", "int16_t", "int32_t", "int64_t",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t", "FILE", "NULL",
    # C++ std namespace symbols
    "std", "cout", "cin", "cerr", "clog", "endl", "string", "vector",
    "map", "set", "unordered_map", "unordered_set", "queue", "stack",
    "deque", "list", "pair", "tuple", "array", "unique_ptr", "shared_ptr",
    "make_unique", "make_shared", "min", "max", "sort", "reverse", "find",
    "swap", "accumulate", "begin", "end", "size", "push_back", "pop_back",
    "empty", "clear", "insert", "erase", "length",
    # Main function entrypoint
    "main",
}
