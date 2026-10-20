"""
Multi-file Comparison, Pairwise Matrix, and Faculty Dashboard for CodeGuard (Phase 4).
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from .engine import CodeGuardEngine, CodeGuardResult


@dataclass
class FileSubmission:
    filename: str
    author: str
    content: str
    language: str = "c"


@dataclass
class PairwiseComparison:
    file_a: str
    file_b: str
    author_a: str
    author_b: str
    overall_similarity: float
    token_similarity: float
    structural_similarity: float
    risk_level: str
    risk_color: str
    is_flagged: bool


@dataclass
class BatchAnalysisReport:
    total_submissions: int
    total_comparisons: int
    flagged_pairs_count: int
    high_risk_pairs: List[PairwiseComparison]
    pairwise_matrix: List[List[float]]  # N x N similarity values (0 - 100)
    file_labels: List[str]
    comparisons: List[PairwiseComparison]


class BatchEngine:
    """
    Executes all-pairs pairwise plagiarism detection across multiple student submissions.
    Flags suspicious pairs and prepares data for matrix and heatmap rendering.
    """

    def __init__(self, flag_threshold: float = 70.0):
        self.engine = CodeGuardEngine()
        self.flag_threshold = flag_threshold

    def analyze_batch(self, submissions: List[FileSubmission]) -> BatchAnalysisReport:
        n = len(submissions)
        matrix: List[List[float]] = [[0.0] * n for _ in range(n)]
        comparisons: List[PairwiseComparison] = []
        high_risk: List[PairwiseComparison] = []

        # Populate diagonal with 100% self-similarity
        for i in range(n):
            matrix[i][i] = 100.0

        for i in range(n):
            for j in range(i + 1, n):
                sub_a = submissions[i]
                sub_b = submissions[j]

                # Run comparison
                res: CodeGuardResult = self.engine.compare(
                    code_a=sub_a.content,
                    code_b=sub_b.content,
                    language=sub_a.language,
                    filename_a=sub_a.filename,
                    filename_b=sub_b.filename
                )

                score = res.overall_similarity
                matrix[i][j] = score
                matrix[j][i] = score

                is_flagged = score >= self.flag_threshold
                pair = PairwiseComparison(
                    file_a=sub_a.filename,
                    file_b=sub_b.filename,
                    author_a=sub_a.author,
                    author_b=sub_b.author,
                    overall_similarity=score,
                    token_similarity=res.token_similarity,
                    structural_similarity=res.structural_similarity,
                    risk_level=res.risk_level,
                    risk_color=res.risk_color,
                    is_flagged=is_flagged
                )

                comparisons.append(pair)
                if is_flagged:
                    high_risk.append(pair)

        # Sort high risk pairs descending by similarity
        high_risk.sort(key=lambda p: p.overall_similarity, reverse=True)

        return BatchAnalysisReport(
            total_submissions=n,
            total_comparisons=len(comparisons),
            flagged_pairs_count=len(high_risk),
            high_risk_pairs=high_risk,
            pairwise_matrix=matrix,
            file_labels=[s.filename for s in submissions],
            comparisons=comparisons
        )
