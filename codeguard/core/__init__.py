"""
CodeGuard Core Engine: Lexical Analysis, Normalization, and Winnowing.
"""
from .token_types import TokenType, SourceLocation, Token, C_CPP_KEYWORDS, STDLIB_SYMBOLS
from .lexer import CLexer, LexerError
from .normalizer import TokenNormalizer, NormalizedToken
from .winnowing import WinnowingEngine, WinnowingResult, Fingerprint, MatchedRegion

__all__ = [
    "TokenType",
    "SourceLocation",
    "Token",
    "C_CPP_KEYWORDS",
    "STDLIB_SYMBOLS",
    "CLexer",
    "LexerError",
    "TokenNormalizer",
    "NormalizedToken",
    "WinnowingEngine",
    "WinnowingResult",
    "Fingerprint",
    "MatchedRegion"
]
