"""
Unified Comparison Engine for CodeGuard.
Combines Lexical/Token Winnowing (Phase 1) and AST Structural Comparison (Phase 2).
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json

from .lexer import CLexer
from .normalizer import TokenNormalizer, NormalizedToken
from .winnowing import WinnowingEngine, WinnowingResult, MatchedRegion
from .ast_analyzer import ASTAnalyzer, ASTComparisonResult, FunctionStructure
from .explanation import TransformationExplainer


@dataclass
class CodeGuardResult:
    overall_similarity: float           # Combined weighted score (0.0 - 100.0)
    token_similarity: float             # Phase 1 Winnowing score (0.0 - 100.0)
    structural_similarity: float        # Phase 2 AST score (0.0 - 100.0)
    control_flow_similarity: float      # AST CFG score (0.0 - 100.0)
    statement_similarity: float         # AST Stmt sequence score (0.0 - 100.0)
    call_graph_similarity: float        # AST Call graph score (0.0 - 100.0)
    risk_level: str                     # "HIGH", "MEDIUM", "LOW"
    risk_color: str                     # "#ef4444", "#f59e0b", "#10b981"
    is_short_code: bool
    warning_message: Optional[str]
    matched_regions: List[Dict[str, Any]]
    explanations: List[str]
    functions_a: List[Dict[str, Any]]
    functions_b: List[Dict[str, Any]]
    tokens_count_a: int
    tokens_count_b: int
    language: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class CodeGuardEngine:
    """
    Primary orchestrator for comparing two C/C++ source code submissions.
    """

    def __init__(
        self,
        token_weight: float = 0.50,
        ast_weight: float = 0.50,
        k: int = 5,
        w: int = 4
    ):
        self.token_weight = token_weight
        self.ast_weight = ast_weight
        self.winnowing_engine = WinnowingEngine(k=k, w=w)

    def compare(
        self,
        code_a: str,
        code_b: str,
        language: str = "c",
        filename_a: str = "program_a.c",
        filename_b: str = "program_b.c"
    ) -> CodeGuardResult:
        """
        Performs full dual-engine comparison on two submissions.
        """
        # Phase 1: Lexical Analysis & Normalization
        lexer_a = CLexer(code_a, filename=filename_a)
        tokens_raw_a = lexer_a.tokenize()

        lexer_b = CLexer(code_b, filename=filename_b)
        tokens_raw_b = lexer_b.tokenize()

        norm_engine_a = TokenNormalizer()
        tokens_norm_a = norm_engine_a.normalize(tokens_raw_a)

        norm_engine_b = TokenNormalizer()
        tokens_norm_b = norm_engine_b.normalize(tokens_raw_b)

        # Winnowing Token Comparison
        winnow_res = self.winnowing_engine.compare(
            tokens_norm_a, tokens_norm_b, source_a=code_a, source_b=code_b
        )

        # Phase 2: AST Structural Comparison
        ast_analyzer = ASTAnalyzer(language=language)
        ast_res = ast_analyzer.compare_ast(
            code_a, code_b, filename_a=filename_a, filename_b=filename_b
        )

        # Composite Score Calculation
        overall = (self.token_weight * winnow_res.similarity_score) + \
                  (self.ast_weight * ast_res.structural_similarity)
        overall = round(min(100.0, max(0.0, overall)), 2)

        # Risk Classification
        if overall >= 70.0:
            risk_level = "HIGH"
            risk_color = "#ef4444"  # Red
        elif overall >= 40.0:
            risk_level = "MEDIUM"
            risk_color = "#f59e0b"  # Amber
        else:
            risk_level = "LOW"
            risk_color = "#10b981"  # Green

        # Generate Explanations
        explanations = TransformationExplainer.explain(
            lexer_a, lexer_b,
            norm_engine_a, norm_engine_b,
            winnow_res, ast_res
        )

        # Format matched regions for serializable output
        formatted_regions = [
            {
                "a_line_start": r.a_line_start,
                "a_line_end": r.a_line_end,
                "a_char_start": r.a_char_start,
                "a_char_end": r.a_char_end,
                "b_line_start": r.b_line_start,
                "b_line_end": r.b_line_end,
                "b_char_start": r.b_char_start,
                "b_char_end": r.b_char_end,
                "token_count": r.token_count,
                "snippet_a": r.snippet_a,
                "snippet_b": r.snippet_b,
            }
            for r in winnow_res.matched_regions
        ]

        # Format functions
        funcs_a_dicts = [
            {
                "name": f.name,
                "return_type": f.return_type,
                "param_count": f.param_count,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "called_functions": f.called_functions,
                "control_flow_tree": f.control_flow_tree
            }
            for f in ast_res.functions_a
        ]

        funcs_b_dicts = [
            {
                "name": f.name,
                "return_type": f.return_type,
                "param_count": f.param_count,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "called_functions": f.called_functions,
                "control_flow_tree": f.control_flow_tree
            }
            for f in ast_res.functions_b
        ]

        return CodeGuardResult(
            overall_similarity=overall,
            token_similarity=winnow_res.similarity_score,
            structural_similarity=ast_res.structural_similarity,
            control_flow_similarity=ast_res.control_flow_similarity,
            statement_similarity=ast_res.statement_sequence_similarity,
            call_graph_similarity=ast_res.call_graph_similarity,
            risk_level=risk_level,
            risk_color=risk_color,
            is_short_code=winnow_res.is_short_code,
            warning_message=winnow_res.warning_message,
            matched_regions=formatted_regions,
            explanations=explanations,
            functions_a=funcs_a_dicts,
            functions_b=funcs_b_dicts,
            tokens_count_a=len(tokens_norm_a),
            tokens_count_b=len(tokens_norm_b),
            language=language
        )
