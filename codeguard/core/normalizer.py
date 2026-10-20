"""
Token Normalization module for CodeGuard.
Replaces user-defined variables and functions with sequential placeholders
while preserving keywords, operators, literals, and standard library symbols.
"""
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from .token_types import Token, TokenType, STDLIB_SYMBOLS


@dataclass
class NormalizedToken:
    original_token: Token
    normalized_value: str
    is_user_identifier: bool = False
    assigned_placeholder: Optional[str] = None

    @property
    def span(self):
        return self.original_token.span

    @property
    def location(self):
        return self.original_token.location

    @property
    def end_location(self):
        return self.original_token.end_location

    def __repr__(self):
        return f"NormToken({self.normalized_value}, L{self.location.line}:C{self.location.column})"


class TokenNormalizer:
    """
    Normalizes token stream by mapping user identifiers to consistent canonical IDs.
    Distinguishes functions (FUNC1, FUNC2, ...) from variables (VAR1, VAR2, ...).
    Retains standard library identifiers (printf, malloc, cout, main) untouched.
    """

    def __init__(self, stdlib_whitelist: Optional[Set[str]] = None):
        self.whitelist = stdlib_whitelist if stdlib_whitelist is not None else STDLIB_SYMBOLS
        self.var_map: Dict[str, str] = {}
        self.func_map: Dict[str, str] = {}
        self.var_counter = 0
        self.func_counter = 0
        self.known_funcs: Set[str] = set()

    def _is_followed_by_paren(self, tokens: List[Token], index: int) -> bool:
        """Check if the token at index is immediately followed by '(' punctuator."""
        if index + 1 < len(tokens):
            next_tok = tokens[index + 1]
            return next_tok.type == TokenType.PUNCTUATOR and next_tok.value == "("
        return False

    def normalize(self, tokens: List[Token]) -> List[NormalizedToken]:
        """
        Processes a list of raw tokens and returns normalized tokens.
        Skips preprocessor directives (or normalizes them) so `#include <stdio.h>`
        doesn't disrupt comparison.
        """
        normalized: List[NormalizedToken] = []

        # Pass 1: Discover all function declarations/calls to register known functions
        for i, tok in enumerate(tokens):
            if tok.type == TokenType.IDENTIFIER:
                val = tok.value
                if val not in self.whitelist and self._is_followed_by_paren(tokens, i):
                    self.known_funcs.add(val)

        # Pass 2: Canonicalize identifiers
        for i, tok in enumerate(tokens):
            # Skip PREPROCESSOR directives for token comparison (handled structurally in AST if needed)
            if tok.type == TokenType.PREPROCESSOR:
                continue

            # Check if this token is a user identifier requiring renaming
            if tok.type == TokenType.IDENTIFIER:
                val = tok.value

                # If it's a whitelisted standard symbol, preserve exact name
                if val in self.whitelist:
                    normalized.append(NormalizedToken(
                        original_token=tok,
                        normalized_value=val,
                        is_user_identifier=False
                    ))
                    continue

                # Determine if it's a function or a variable
                is_function = (val in self.known_funcs) or self._is_followed_by_paren(tokens, i)

                if is_function:
                    if val not in self.func_map:
                        self.func_counter += 1
                        self.func_map[val] = f"FUNC{self.func_counter}"
                    placeholder = self.func_map[val]
                else:
                    if val not in self.var_map:
                        self.var_counter += 1
                        self.var_map[val] = f"VAR{self.var_counter}"
                    placeholder = self.var_map[val]

                normalized.append(NormalizedToken(
                    original_token=tok,
                    normalized_value=placeholder,
                    is_user_identifier=True,
                    assigned_placeholder=placeholder
                ))
            else:
                # Keywords, operators, literals, punctuators stay as-is
                normalized.append(NormalizedToken(
                    original_token=tok,
                    normalized_value=tok.value,
                    is_user_identifier=False
                ))

        return normalized

    @property
    def symbol_mapping(self) -> Dict[str, str]:
        """Returns the full dictionary of user original names -> canonical placeholders."""
        combined = dict(self.func_map)
        combined.update(self.var_map)
        return combined
