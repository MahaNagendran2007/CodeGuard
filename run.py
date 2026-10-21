"""
CodeGuard: Source Code Plagiarism Detection System
Primary CLI and Web Application Entrypoint.

Usage:
  py run.py --server [port]              Launch the interactive web UI (Default port: 8080)
  py run.py --compare file_a.c file_b.c  Compare two C/C++ files from the terminal
  py run.py --benchmarks                 Run verification on all 4 benchmark test pairs
  py run.py --test                       Run the automated test suite
"""
import sys
import os
import argparse
import unittest

# Ensure stdout uses utf-8 on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure current directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from codeguard.core.engine import CodeGuardEngine
from codeguard.core.ast_analyzer import ASTAnalyzer
from codeguard.core.function_analyzer import FunctionLevelAnalyzer
from codeguard.web.server import start_server


def run_cli_compare(file_a: str, file_b: str, lang: str = "c"):
    if not os.path.exists(file_a):
        print(f"Error: File '{file_a}' not found.")
        sys.exit(1)
    if not os.path.exists(file_b):
        print(f"Error: File '{file_b}' not found.")
        sys.exit(1)

    with open(file_a, "r", encoding="utf-8") as fa:
        code_a = fa.read()
    with open(file_b, "r", encoding="utf-8") as fb:
        code_b = fb.read()

    engine = CodeGuardEngine()
    result = engine.compare(code_a, code_b, language=lang, filename_a=file_a, filename_b=file_b)

    print("=" * 65)
    print("      🛡️  CodeGuard Plagiarism Inspection Report")
    print("=" * 65)
    print(f"Program A: {file_a} ({result.tokens_count_a} normalized tokens)")
    print(f"Program B: {file_b} ({result.tokens_count_b} normalized tokens)")
    print(f"Language:  {result.language.upper()} (C11 / C++17 Front-End)")
    print("-" * 65)
    print(f"  • OVERALL PLAGIARISM SCORE:  {result.overall_similarity:.1f}%")
    print(f"  • Token Winnowing Score:     {result.token_similarity:.1f}% (Phase 1)")
    print(f"  • AST Structural Score:      {result.structural_similarity:.1f}% (Phase 2)")
    print(f"      - Control-Flow CFG:      {result.control_flow_similarity:.1f}%")
    print(f"      - Statement Sequences:   {result.statement_similarity:.1f}%")
    print(f"      - Call Graph Topology:   {result.call_graph_similarity:.1f}%")
    print(f"  • VERDICT / RISK LEVEL:      [{result.risk_level}]")
    print("-" * 65)

    if result.warning_message:
        print(f"⚠️  {result.warning_message}")
        print("-" * 65)

    print("Forensic Transformation Explanations:")
    for idx, exp in enumerate(result.explanations, 1):
        print(f"  {idx}. {exp}")

    # Function Level Breakdown
    funcs_a = ASTAnalyzer(language=lang).parse_source(code_a)
    funcs_b = ASTAnalyzer(language=lang).parse_source(code_b)
    matches = FunctionLevelAnalyzer().analyze(code_a, code_b, funcs_a, funcs_b)

    if matches:
        print("-" * 65)
        print("Function-Level Match Breakdown:")
        for m in matches:
            print(f"  • {m.function_a} ({m.line_range_a}) <-> {m.function_b} ({m.line_range_b}): "
                  f"Token: {m.token_similarity:.1f}%, AST: {m.structural_similarity:.1f}%, "
                  f"Overall: {m.overall_similarity:.1f}% [{m.verdict}]")

    print("=" * 65)


def run_benchmarks():
    fixtures_dir = os.path.join(BASE_DIR, "tests", "fixtures")
    test_pairs = [
        ("pair_identical", "1. Identical Submissions"),
        ("pair_renamed", "2. Renamed Variables & Functions"),
        ("pair_reordered", "3. Reordered Statements & Functions"),
        ("pair_unrelated", "4. Unrelated Algorithms (QuickSort vs Matrix)"),
        ("pair_short", "5. Short 3-Line Function (Caveat Test)")
    ]

    print("\n" + "=" * 70)
    print("      🧪 Running CodeGuard Compiler Benchmark Evaluation Suite")
    print("=" * 70)

    engine = CodeGuardEngine()

    for folder, desc in test_pairs:
        fa = os.path.join(fixtures_dir, folder, "program_a.c")
        fb = os.path.join(fixtures_dir, folder, "program_b.c")
        with open(fa, "r", encoding="utf-8") as f:
            code_a = f.read()
        with open(fb, "r", encoding="utf-8") as f:
            code_b = f.read()

        res = engine.compare(code_a, code_b, language="c")

        print(f"\n{desc}:")
        print(f"  Token Sim: {res.token_similarity:.1f}% | AST Sim: {res.structural_similarity:.1f}% | Overall: {res.overall_similarity:.1f}%")
        print(f"  Risk: [{res.risk_level}] | Matched Regions: {len(res.matched_regions)}")
        if res.is_short_code:
            print(f"  Notice: Correctly triggered short submission low-confidence warning.")
        if res.explanations:
            print(f"  Key Explanation: {res.explanations[0]}")

    print("\n" + "=" * 70)
    print("  All benchmark sanity checks completed successfully.")
    print("=" * 70 + "\n")


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(BASE_DIR, "tests"))
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)


def main():
    parser = argparse.ArgumentParser(
        description="CodeGuard: Compiler-Based C/C++ Plagiarism Detection System"
    )
    parser.add_argument("--server", "-s", action="store_true", help="Launch web UI server")
    parser.add_argument("--port", "-p", type=int, default=int(os.environ.get("PORT","8080")), help="Port for web server")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("FILE_A", "FILE_B"), help="Compare two source files")
    parser.add_argument("--benchmarks", "-b", action="store_true", help="Run benchmark verification test pairs")
    parser.add_argument("--test", "-t", action="store_true", help="Run automated test suite")
    parser.add_argument("--lang", default="c", choices=["c", "cpp"], help="Programming language (default: c)")

    args = parser.parse_args()

    if args.server:
        start_server(port=args.port)
    elif args.compare:
        run_cli_compare(args.compare[0], args.compare[1], lang=args.lang)
    elif args.benchmarks:
        run_benchmarks()
    elif args.test:
        run_tests()
    else:
        # Default: if no arguments provided, display help and offer interactive options
        parser.print_help()
        print("\nTip: Run 'py run.py --benchmarks' or 'py run.py --server' to get started.")


if __name__ == "__main__":
    main()
