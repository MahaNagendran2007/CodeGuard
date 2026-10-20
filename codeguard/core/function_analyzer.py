"""
Function-Level Similarity Breakdown for CodeGuard (Phase 4 Feature 1).
Compares individual functions across submissions to detect targeted function-level copying.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from .lexer import CLexer
from .normalizer import TokenNormalizer
from .winnowing import WinnowingEngine
from .ast_analyzer import ASTAnalyzer, FunctionStructure


@dataclass
class FunctionMatch:
    function_a: str
    function_b: str
    line_range_a: str
    line_range_b: str
    token_similarity: float
    structural_similarity: float
    overall_similarity: float
    verdict: str  # "COPIED", "SUSPICIOUS", "MODIFIED", "UNIQUE"


class FunctionLevelAnalyzer:
    """
    Extracts individual function bodies and performs pairwise similarity analysis.
    """

    def __init__(self):
        self.winnowing = WinnowingEngine(k=4, w=3)
        self.ast_analyzer = ASTAnalyzer()

    def _extract_function_source(self, code: str, f: FunctionStructure) -> str:
        lines = code.splitlines()
        start = max(0, f.line_start - 1)
        end = min(len(lines), f.line_end)
        return "\n".join(lines[start:end])

    def analyze(
        self,
        code_a: str,
        code_b: str,
        funcs_a: List[FunctionStructure],
        funcs_b: List[FunctionStructure]
    ) -> List[FunctionMatch]:
        results: List[FunctionMatch] = []

        if not funcs_a or not funcs_b:
            return results

        # For each function in A, find best matching function in B
        for fa in funcs_a:
            if fa.name == "<global>":
                continue
            src_a = self._extract_function_source(code_a, fa)
            toks_a = TokenNormalizer().normalize(CLexer(src_a).tokenize())

            best_match: Optional[FunctionMatch] = None
            best_score = -1.0

            for fb in funcs_b:
                if fb.name == "<global>":
                    continue
                src_b = self._extract_function_source(code_b, fb)
                toks_b = TokenNormalizer().normalize(CLexer(src_b).tokenize())

                # Token comparison
                tok_res = self.winnowing.compare(toks_a, toks_b, src_a, src_b)
                tok_sim = tok_res.similarity_score

                # AST comparison
                ast_res = self.ast_analyzer.compare_ast(src_a, src_b)
                ast_sim = ast_res.structural_similarity

                overall = round(0.5 * tok_sim + 0.5 * ast_sim, 2)

                if overall > best_score:
                    best_score = overall
                    if overall >= 80.0:
                        verdict = "COPIED"
                    elif overall >= 55.0:
                        verdict = "SUSPICIOUS"
                    elif overall >= 35.0:
                        verdict = "MODIFIED"
                    else:
                        verdict = "UNIQUE"

                    best_match = FunctionMatch(
                        function_a=fa.name,
                        function_b=fb.name,
                        line_range_a=f"L{fa.line_start}-L{fa.line_end}",
                        line_range_b=f"L{fb.line_start}-L{fb.line_end}",
                        token_similarity=tok_sim,
                        structural_similarity=ast_sim,
                        overall_similarity=overall,
                        verdict=verdict
                    )

            if best_match:
                results.append(best_match)

        return results
