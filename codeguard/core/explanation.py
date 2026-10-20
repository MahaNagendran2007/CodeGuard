"""
Heuristic diff and transformation explainer for CodeGuard.
Analyzes what compiler-level transformations occurred between Program A and Program B:
- Variable and function renamings
- Comment stripping/modifications
- Formatting changes
- Control-flow and AST congruence
"""
from typing import List, Dict, Set, Tuple, Optional
from .normalizer import NormalizedToken, TokenNormalizer
from .lexer import CLexer
from .ast_analyzer import ASTComparisonResult
from .winnowing import WinnowingResult


class TransformationExplainer:
    """
    Generates plain-text forensic explanations of detected plagiaristic transformations.
    """

    @staticmethod
    def explain(
        lexer_a: CLexer,
        lexer_b: CLexer,
        normalizer_a: TokenNormalizer,
        normalizer_b: TokenNormalizer,
        winnowing_res: WinnowingResult,
        ast_res: ASTComparisonResult
    ) -> List[str]:
        notes: List[str] = []

        # 1. Short code confidence note (Requirement 1.4)
        if winnowing_res.is_short_code:
            notes.append(
                "⚠️ LOW CONFIDENCE WARNING: This submission contains short/trivial functions. "
                "Independent implementations of short algorithms naturally produce near-identical "
                "normalized token streams. Plagiarism should NOT be concluded based on this score alone."
            )

        # 2. Variable and Function Renaming Analysis
        # Invert mappings: placeholder -> original name
        inv_a = {v: k for k, v in normalizer_a.symbol_mapping.items()}
        inv_b = {v: k for k, v in normalizer_b.symbol_mapping.items()}

        renamed_vars: List[Tuple[str, str]] = []
        renamed_funcs: List[Tuple[str, str]] = []

        for placeholder, name_a in inv_a.items():
            if placeholder in inv_b:
                name_b = inv_b[placeholder]
                if name_a != name_b:
                    if placeholder.startswith("FUNC"):
                        renamed_funcs.append((name_a, name_b))
                    else:
                        renamed_vars.append((name_a, name_b))

        if renamed_funcs:
            pairs_str = ", ".join(f"`{a}` → `{b}`" for a, b in renamed_funcs[:5])
            if len(renamed_funcs) > 5:
                pairs_str += f" and {len(renamed_funcs) - 5} more"
            notes.append(f"Detected Function Renaming: {pairs_str}.")

        if renamed_vars:
            pairs_str = ", ".join(f"`{a}` → `{b}`" for a, b in renamed_vars[:6])
            if len(renamed_vars) > 6:
                pairs_str += f" and {len(renamed_vars) - 6} more"
            notes.append(f"Detected Identifier/Variable Renaming: {pairs_str}.")
        elif not renamed_funcs and winnowing_res.similarity_score >= 80.0:
            notes.append("Identifier names are identical across both submissions.")

        # 3. Comment Stripping / Modification
        comments_count_a = len(lexer_a.stripped_comments)
        comments_count_b = len(lexer_b.stripped_comments)
        if comments_count_a != comments_count_b:
            notes.append(
                f"Comment Alterations: Program A contains {comments_count_a} comment(s), whereas "
                f"Program B contains {comments_count_b} comment(s). Lexer stripped all comments prior "
                f"to comparison so scores remain invariant to comment presence."
            )
        elif comments_count_a > 0:
            notes.append(
                f"Both programs contain {comments_count_a} comment(s), which were ignored during lexical analysis."
            )

        # 4. AST & Control Flow Explanations
        for exp in ast_res.structural_explanation:
            notes.append(exp)

        # 5. Token Fingerprint match summary
        if winnowing_res.shared_fingerprints_count > 0:
            notes.append(
                f"Found {winnowing_res.shared_fingerprints_count} shared Rabin-Karp winnowed fingerprint(s) "
                f"spanning {len(winnowing_res.matched_regions)} contiguous code region(s)."
            )

        return notes
