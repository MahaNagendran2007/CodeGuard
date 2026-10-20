"""
Phase 1 Unit Tests: Lexer, Normalizer, and Winnowing Algorithm.
"""
import unittest
import os
import sys

# Ensure codeguard package is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from codeguard.core.token_types import TokenType
from codeguard.core.lexer import CLexer
from codeguard.core.normalizer import TokenNormalizer
from codeguard.core.winnowing import WinnowingEngine, hash_kgram


class TestCLexer(unittest.TestCase):

    def test_comment_stripping(self):
        code_with_comments = """
        // This is a single line comment
        int main() {
            /* This is a 
               multi-line comment */
            int x = 42; // end of line comment
            return x;
        }
        """
        lexer = CLexer(code_with_comments)
        tokens = lexer.tokenize()

        # Check that no token is a comment
        for tok in tokens:
            self.assertNotEqual(tok.type, TokenType.COMMENT)

        # Check that stripped comments were tracked
        self.assertEqual(len(lexer.stripped_comments), 3)

        # Ensure core tokens are present
        token_values = [t.value for t in tokens]
        self.assertIn("int", token_values)
        self.assertIn("main", token_values)
        self.assertIn("42", token_values)
        self.assertIn("return", token_values)

    def test_formatting_invariance(self):
        code_clean = "int a=5;int b=10;return a+b;"
        code_spaced = "   int    a =  5 ; \n\n\t int  b  = 10 ; \n return  a  +  b ; "

        tokens_clean = CLexer(code_clean).tokenize()
        tokens_spaced = CLexer(code_spaced).tokenize()

        self.assertEqual(len(tokens_clean), len(tokens_spaced))
        for t1, t2 in zip(tokens_clean, tokens_spaced):
            self.assertEqual(t1.type, t2.type)
            self.assertEqual(t1.value, t2.value)

    def test_multi_char_operators(self):
        code = "a += b; c == d; e -> f; g && h; i++; j <<= 2;"
        tokens = CLexer(code).tokenize()
        operators = [t.value for t in tokens if t.type == TokenType.OPERATOR]
        self.assertIn("+=", operators)
        self.assertIn("==", operators)
        self.assertIn("->", operators)
        self.assertIn("&&", operators)
        self.assertIn("++", operators)
        self.assertIn("<<=", operators)


class TestTokenNormalizer(unittest.TestCase):

    def test_identifier_renaming_consistency(self):
        code = "int counter = 0; while(counter < 10) { counter++; }"
        tokens = CLexer(code).tokenize()
        normalizer = TokenNormalizer()
        norm_tokens = normalizer.normalize(tokens)

        # 'counter' should be consistently mapped to VAR1
        norm_values = [t.normalized_value for t in norm_tokens]
        self.assertEqual(norm_values[1], "VAR1")
        self.assertEqual(norm_values[7], "VAR1")
        self.assertEqual(norm_values[12], "VAR1")

        # Keywords and literals remain intact
        self.assertEqual(norm_values[0], "int")
        self.assertEqual(norm_values[5], "while")
        self.assertEqual(norm_values[9], "10")

    def test_stdlib_whitelist_preservation(self):
        code = "int main() { printf(\"Hello\"); malloc(100); return 0; }"
        tokens = CLexer(code).tokenize()
        normalizer = TokenNormalizer()
        norm_tokens = normalizer.normalize(tokens)

        norm_values = [t.normalized_value for t in norm_tokens]
        # main, printf, malloc must NOT be renamed
        self.assertIn("main", norm_values)
        self.assertIn("printf", norm_values)
        self.assertIn("malloc", norm_values)

    def test_renamed_code_normalizes_identically(self):
        code_a = "int calculate(int val) { int result = val * 2; return result; }"
        code_b = "int compute(int num) { int output = num * 2; return output; }"

        tokens_a = CLexer(code_a).tokenize()
        tokens_b = CLexer(code_b).tokenize()

        norm_a = TokenNormalizer().normalize(tokens_a)
        norm_b = TokenNormalizer().normalize(tokens_b)

        values_a = [t.normalized_value for t in norm_a]
        values_b = [t.normalized_value for t in norm_b]

        self.assertEqual(values_a, values_b)


class TestWinnowingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = WinnowingEngine(k=5, w=4)

    def test_identical_fixtures(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_identical")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        tokens_a = TokenNormalizer().normalize(CLexer(code_a).tokenize())
        tokens_b = TokenNormalizer().normalize(CLexer(code_b).tokenize())

        result = self.engine.compare(tokens_a, tokens_b, code_a, code_b)
        self.assertEqual(result.similarity_score, 100.0)
        self.assertGreater(len(result.matched_regions), 0)

    def test_renamed_fixtures(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_renamed")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        tokens_a = TokenNormalizer().normalize(CLexer(code_a).tokenize())
        tokens_b = TokenNormalizer().normalize(CLexer(code_b).tokenize())

        result = self.engine.compare(tokens_a, tokens_b, code_a, code_b)
        # Even with completely renamed variables/functions, comments stripped, formatting changed:
        # Token similarity must be high (>= 90%)
        self.assertGreaterEqual(result.similarity_score, 90.0)

    def test_unrelated_fixtures(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_unrelated")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        tokens_a = TokenNormalizer().normalize(CLexer(code_a).tokenize())
        tokens_b = TokenNormalizer().normalize(CLexer(code_b).tokenize())

        result = self.engine.compare(tokens_a, tokens_b, code_a, code_b)
        # Unrelated algorithms (QuickSort vs Matrix Multiplication) must have very low similarity
        self.assertLess(result.similarity_score, 25.0)

    def test_reordered_fixtures(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_reordered")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        tokens_a = TokenNormalizer().normalize(CLexer(code_a).tokenize())
        tokens_b = TokenNormalizer().normalize(CLexer(code_b).tokenize())

        result = self.engine.compare(tokens_a, tokens_b, code_a, code_b)
        # Reordered statements have moderate token similarity (partially shifted k-grams)
        self.assertGreater(result.similarity_score, 30.0)

    def test_short_code_limitation_warning(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_short")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        tokens_a = TokenNormalizer().normalize(CLexer(code_a).tokenize())
        tokens_b = TokenNormalizer().normalize(CLexer(code_b).tokenize())

        result = self.engine.compare(tokens_a, tokens_b, code_a, code_b)
        # Evaluates 1.4: short function triggers low-confidence warning
        self.assertTrue(result.is_short_code)
        self.assertIsNotNone(result.warning_message)
        self.assertIn("Short submission detected", result.warning_message)


if __name__ == "__main__":
    unittest.main()
