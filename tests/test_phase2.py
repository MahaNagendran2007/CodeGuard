"""
Phase 2 Unit Tests: AST Structural Comparison and Combined Engine.
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from codeguard.core.ast_analyzer import ASTAnalyzer
from codeguard.core.engine import CodeGuardEngine
from codeguard.core.function_analyzer import FunctionLevelAnalyzer
from codeguard.core.batch import BatchEngine, FileSubmission


class TestASTAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = ASTAnalyzer(language="c")

    def test_parse_c_functions(self):
        code = """
        int max_val(int a, int b) {
            if (a > b) {
                return a;
            }
            return b;
        }
        """
        funcs = self.analyzer.parse_source(code)
        self.assertGreaterEqual(len(funcs), 1)
        target_func = [f for f in funcs if f.name == "max_val"][0]
        self.assertEqual(target_func.name, "max_val")
        self.assertEqual(target_func.param_count, 2)
        self.assertIn("If", target_func.control_flow_tree)
        self.assertIn("Return", target_func.control_flow_tree)

    def test_renamed_programs_have_high_ast_similarity(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_renamed")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        result = self.analyzer.compare_ast(code_a, code_b)
        # Structural similarity should be very high (>= 85%) despite renamed functions and variables
        self.assertGreaterEqual(result.structural_similarity, 85.0)
        self.assertGreaterEqual(result.control_flow_similarity, 85.0)

    def test_unrelated_programs_have_low_ast_similarity(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_unrelated")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        result = self.analyzer.compare_ast(code_a, code_b)
        # QuickSort vs Matrix Multiply should have low structural similarity (< 45%)
        self.assertLess(result.structural_similarity, 45.0)


class TestFullEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CodeGuardEngine()

    def test_identical_comparison(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_identical")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        result = self.engine.compare(code_a, code_b)
        self.assertGreaterEqual(result.overall_similarity, 98.0)
        self.assertEqual(result.risk_level, "HIGH")

    def test_renamed_comparison(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_renamed")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        result = self.engine.compare(code_a, code_b)
        self.assertGreaterEqual(result.overall_similarity, 85.0)
        self.assertEqual(result.risk_level, "HIGH")
        # Explanations should include detected variable renaming
        has_renaming_note = any("Renaming" in exp for exp in result.explanations)
        self.assertTrue(has_renaming_note)

    def test_unrelated_comparison(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_unrelated")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        result = self.engine.compare(code_a, code_b)
        self.assertLess(result.overall_similarity, 30.0)
        self.assertEqual(result.risk_level, "LOW")


class TestFunctionAndBatch(unittest.TestCase):

    def test_function_level_analyzer(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "pair_renamed")
        with open(os.path.join(fixtures_dir, "program_a.c"), "r") as f:
            code_a = f.read()
        with open(os.path.join(fixtures_dir, "program_b.c"), "r") as f:
            code_b = f.read()

        funcs_a = ASTAnalyzer().parse_source(code_a)
        funcs_b = ASTAnalyzer().parse_source(code_b)

        analyzer = FunctionLevelAnalyzer()
        matches = analyzer.analyze(code_a, code_b, funcs_a, funcs_b)
        self.assertGreater(len(matches), 0)
        # bubble_sort should match sort_elements with high score
        sort_match = [m for m in matches if m.function_a == "bubble_sort"][0]
        self.assertEqual(sort_match.function_b, "sort_elements")
        self.assertGreaterEqual(sort_match.overall_similarity, 80.0)
        self.assertEqual(sort_match.verdict, "COPIED")

    def test_batch_engine(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        with open(os.path.join(fixtures_dir, "pair_identical", "program_a.c"), "r") as f:
            c1 = f.read()
        with open(os.path.join(fixtures_dir, "pair_renamed", "program_b.c"), "r") as f:
            c2 = f.read()
        with open(os.path.join(fixtures_dir, "pair_unrelated", "program_b.c"), "r") as f:
            c3 = f.read()

        submissions = [
            FileSubmission("student1_binsearch.c", "Alice", c1),
            FileSubmission("student2_bubblesort.c", "Bob", c2),
            FileSubmission("student3_matrix.c", "Charlie", c3),
        ]

        batch = BatchEngine(flag_threshold=70.0)
        report = batch.analyze_batch(submissions)
        self.assertEqual(report.total_submissions, 3)
        self.assertEqual(report.total_comparisons, 3)
        self.assertEqual(len(report.pairwise_matrix), 3)


if __name__ == "__main__":
    unittest.main()
