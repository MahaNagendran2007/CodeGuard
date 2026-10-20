"""
Winnowing Algorithm (Rabin-Karp k-gram fingerprinting) for CodeGuard.
Guarantees detection of matches >= (w + k - 1) tokens.
Tracks source coordinates to enable visual match highlighting.
"""
import hashlib
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from .normalizer import NormalizedToken


@dataclass(frozen=True)
class Fingerprint:
    hash_val: int
    token_start: int
    token_end: int       # inclusive
    line_start: int
    line_end: int
    col_start: int
    col_end: int
    char_start: int
    char_end: int


@dataclass
class MatchedRegion:
    """Consolidated matching range between two files."""
    a_line_start: int
    a_line_end: int
    a_char_start: int
    a_char_end: int
    b_line_start: int
    b_line_end: int
    b_char_start: int
    b_char_end: int
    token_count: int
    snippet_a: str = ""
    snippet_b: str = ""


@dataclass
class WinnowingResult:
    similarity_score: float             # 0.0 to 100.0
    jaccard_similarity: float           # 0.0 to 1.0
    containment_similarity: float       # 0.0 to 1.0
    total_fingerprints_a: int
    total_fingerprints_b: int
    shared_fingerprints_count: int
    matched_regions: List[MatchedRegion]
    is_short_code: bool
    warning_message: Optional[str] = None


def hash_kgram(tokens: List[NormalizedToken]) -> int:
    """
    Computes a deterministic 64-bit integer hash for a k-gram of normalized tokens.
    Uses MD5 truncated to 64 bits to guarantee cross-platform consistency.
    """
    token_str = " ".join(t.normalized_value for t in tokens)
    digest = hashlib.md5(token_str.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


class WinnowingEngine:
    """
    Implements the Winnowing algorithm as described by Schleimer, Wilkerson, and Aiken (2003).
    """

    def __init__(self, k: int = 5, w: int = 4, short_code_threshold: int = 20):
        """
        :param k: Length of each token k-gram.
        :param w: Size of the sliding window over k-grams.
        :param short_code_threshold: Token count threshold below which confidence is reduced.
        """
        self.k = k
        self.w = w
        self.short_code_threshold = short_code_threshold

    def compute_fingerprints(self, tokens: List[NormalizedToken]) -> List[Fingerprint]:
        """
        Generates winnowed fingerprints from a stream of normalized tokens.
        """
        n = len(tokens)
        if n < self.k:
            # Not enough tokens for even one k-gram
            if n > 0:
                h = hash_kgram(tokens)
                return [Fingerprint(
                    hash_val=h,
                    token_start=0,
                    token_end=n - 1,
                    line_start=tokens[0].location.line,
                    line_end=tokens[-1].end_location.line,
                    col_start=tokens[0].location.column,
                    col_end=tokens[-1].end_location.column,
                    char_start=tokens[0].span[0],
                    char_end=tokens[-1].span[1]
                )]
            return []

        # Step 1: Compute hashes for all k-grams
        kgram_hashes: List[Tuple[int, int, int]] = []  # (hash_val, start_idx, end_idx)
        for i in range(n - self.k + 1):
            kgram = tokens[i:i + self.k]
            h = hash_kgram(kgram)
            kgram_hashes.append((h, i, i + self.k - 1))

        # Step 2: Slide window of size w over k-gram hashes
        num_kgrams = len(kgram_hashes)
        if num_kgrams <= self.w:
            # Window is larger than or equal to available k-grams: select minimum
            min_entry = min(kgram_hashes, key=lambda item: item[0])
            start_tok = tokens[min_entry[1]]
            end_tok = tokens[min_entry[2]]
            return [Fingerprint(
                hash_val=min_entry[0],
                token_start=min_entry[1],
                token_end=min_entry[2],
                line_start=start_tok.location.line,
                line_end=end_tok.end_location.line,
                col_start=start_tok.location.column,
                col_end=end_tok.end_location.column,
                char_start=start_tok.span[0],
                char_end=end_tok.span[1]
            )]

        fingerprints: List[Fingerprint] = []
        last_selected_idx = -1

        for i in range(num_kgrams - self.w + 1):
            window = kgram_hashes[i:i + self.w]
            # Standard MOSS rule: in case of ties, select rightmost minimum
            # By traversing reverse and finding minimum, we get the rightmost index
            min_val = min(item[0] for item in window)
            # Find the rightmost item having min_val
            rightmost_idx = -1
            for offset in range(self.w - 1, -1, -1):
                if window[offset][0] == min_val:
                    rightmost_idx = i + offset
                    break

            if rightmost_idx != last_selected_idx:
                selected = kgram_hashes[rightmost_idx]
                start_tok = tokens[selected[1]]
                end_tok = tokens[selected[2]]
                fingerprints.append(Fingerprint(
                    hash_val=selected[0],
                    token_start=selected[1],
                    token_end=selected[2],
                    line_start=start_tok.location.line,
                    line_end=end_tok.end_location.line,
                    col_start=start_tok.location.column,
                    col_end=end_tok.end_location.column,
                    char_start=start_tok.span[0],
                    char_end=end_tok.span[1]
                ))
                last_selected_idx = rightmost_idx

        return fingerprints

    def compare(
        self,
        tokens_a: List[NormalizedToken],
        tokens_b: List[NormalizedToken],
        source_a: str = "",
        source_b: str = ""
    ) -> WinnowingResult:
        """
        Compares two normalized token streams using winnowed fingerprints.
        """
        fps_a = self.compute_fingerprints(tokens_a)
        fps_b = self.compute_fingerprints(tokens_b)

        is_short = (len(tokens_a) < self.short_code_threshold or
                    len(tokens_b) < self.short_code_threshold)
        warning = None
        if is_short:
            warning = (
                f"Short submission detected (A: {len(tokens_a)} tokens, B: {len(tokens_b)} tokens). "
                f"Simple short functions often yield high normalized similarity by chance; "
                f"treat this score with lower confidence."
            )

        if not fps_a or not fps_b:
            # Handle edge cases (empty files)
            score = 100.0 if (not tokens_a and not tokens_b) else 0.0
            return WinnowingResult(
                similarity_score=score,
                jaccard_similarity=1.0 if score == 100.0 else 0.0,
                containment_similarity=1.0 if score == 100.0 else 0.0,
                total_fingerprints_a=len(fps_a),
                total_fingerprints_b=len(fps_b),
                shared_fingerprints_count=0,
                matched_regions=[],
                is_short_code=is_short,
                warning_message=warning
            )

        # Index fingerprints of B by hash
        fps_b_map: Dict[int, List[Fingerprint]] = {}
        for fp in fps_b:
            fps_b_map.setdefault(fp.hash_val, []).append(fp)

        # Find matches and covered token indices
        matched_tokens_a: Set[int] = set()
        matched_tokens_b: Set[int] = set()
        raw_regions: List[MatchedRegion] = []
        shared_hashes: Set[int] = set()

        for fp_a in fps_a:
            if fp_a.hash_val in fps_b_map:
                shared_hashes.add(fp_a.hash_val)

                for fp_b in fps_b_map[fp_a.hash_val]:
                    # Expand match backwards along identical normalized tokens
                    start_a = fp_a.token_start
                    start_b = fp_b.token_start
                    while (start_a > 0 and start_b > 0 and
                           tokens_a[start_a - 1].normalized_value == tokens_b[start_b - 1].normalized_value):
                        start_a -= 1
                        start_b -= 1

                    # Expand match forwards along identical normalized tokens
                    end_a = fp_a.token_end
                    end_b = fp_b.token_end
                    while (end_a + 1 < len(tokens_a) and end_b + 1 < len(tokens_b) and
                           tokens_a[end_a + 1].normalized_value == tokens_b[end_b + 1].normalized_value):
                        end_a += 1
                        end_b += 1

                    for i in range(start_a, end_a + 1):
                        matched_tokens_a.add(i)
                    for j in range(start_b, end_b + 1):
                        matched_tokens_b.add(j)

                    c_start_a = tokens_a[start_a].span[0]
                    c_end_a = tokens_a[end_a].span[1]
                    c_start_b = tokens_b[start_b].span[0]
                    c_end_b = tokens_b[end_b].span[1]

                    snip_a = source_a[c_start_a:c_end_a] if source_a else ""
                    snip_b = source_b[c_start_b:c_end_b] if source_b else ""

                    raw_regions.append(MatchedRegion(
                        a_line_start=tokens_a[start_a].location.line,
                        a_line_end=tokens_a[end_a].end_location.line,
                        a_char_start=c_start_a,
                        a_char_end=c_end_a,
                        b_line_start=tokens_b[start_b].location.line,
                        b_line_end=tokens_b[end_b].end_location.line,
                        b_char_start=c_start_b,
                        b_char_end=c_end_b,
                        token_count=end_a - start_a + 1,
                        snippet_a=snip_a,
                        snippet_b=snip_b
                    ))

        # Check if entire normalized token sequence is 100% identical
        if len(tokens_a) > 0 and len(tokens_a) == len(tokens_b):
            if [t.normalized_value for t in tokens_a] == [t.normalized_value for t in tokens_b]:
                for i in range(len(tokens_a)):
                    matched_tokens_a.add(i)
                    matched_tokens_b.add(i)
                if not raw_regions and tokens_a:
                    c_start_a = tokens_a[0].span[0]
                    c_end_a = tokens_a[-1].span[1]
                    c_start_b = tokens_b[0].span[0]
                    c_end_b = tokens_b[-1].span[1]
                    raw_regions.append(MatchedRegion(
                        a_line_start=tokens_a[0].location.line,
                        a_line_end=tokens_a[-1].end_location.line,
                        a_char_start=c_start_a,
                        a_char_end=c_end_a,
                        b_line_start=tokens_b[0].location.line,
                        b_line_end=tokens_b[-1].end_location.line,
                        b_char_start=c_start_b,
                        b_char_end=c_end_b,
                        token_count=len(tokens_a),
                        snippet_a=source_a[c_start_a:c_end_a] if source_a else "",
                        snippet_b=source_b[c_start_b:c_end_b] if source_b else ""
                    ))

        # Merge overlapping / contiguous matched regions for clean UI highlighting
        merged_regions = self._merge_matched_regions(raw_regions, source_a, source_b)

        # Compute token coverage metrics
        cov_a = len(matched_tokens_a) / len(tokens_a) if tokens_a else 0.0
        cov_b = len(matched_tokens_b) / len(tokens_b) if tokens_b else 0.0

        # Jaccard and containment metrics over fingerprint sets
        hashes_a = {fp.hash_val for fp in fps_a}
        hashes_b = {fp.hash_val for fp in fps_b}
        intersection = hashes_a.intersection(hashes_b)
        union = hashes_a.union(hashes_b)

        jaccard = len(intersection) / len(union) if union else 0.0
        containment = len(intersection) / min(len(hashes_a), len(hashes_b)) if min(len(hashes_a), len(hashes_b)) > 0 else 0.0

        if cov_a + cov_b > 0:
            sim_score = ((cov_a + cov_b) / 2.0) * 100.0
        else:
            sim_score = 0.0

        # If identical token streams, ensure exact 100.0
        if len(tokens_a) > 0 and len(tokens_a) == len(tokens_b):
            if [t.normalized_value for t in tokens_a] == [t.normalized_value for t in tokens_b]:
                sim_score = 100.0
                jaccard = 1.0
                containment = 1.0

        return WinnowingResult(
            similarity_score=round(min(100.0, max(0.0, sim_score)), 2),
            jaccard_similarity=round(jaccard, 4),
            containment_similarity=round(containment, 4),
            total_fingerprints_a=len(fps_a),
            total_fingerprints_b=len(fps_b),
            shared_fingerprints_count=len(shared_hashes),
            matched_regions=merged_regions,
            is_short_code=is_short,
            warning_message=warning
        )

    def _merge_matched_regions(
        self,
        regions: List[MatchedRegion],
        source_a: str,
        source_b: str
    ) -> List[MatchedRegion]:
        """
        Merges adjacent or overlapping matched regions to prevent visual fragmentation in UI.
        """
        if not regions:
            return []

        # Sort by file A character start position
        sorted_regions = sorted(regions, key=lambda r: (r.a_char_start, r.b_char_start))
        merged: List[MatchedRegion] = [sorted_regions[0]]

        for curr in sorted_regions[1:]:
            prev = merged[-1]
            # Check if regions overlap or are adjacent in both files
            a_overlaps = curr.a_char_start <= prev.a_char_end + 10
            b_overlaps = (curr.b_char_start >= prev.b_char_start and
                          curr.b_char_start <= prev.b_char_end + 10)

            if a_overlaps and b_overlaps:
                # Merge into previous region
                new_a_end = max(prev.a_char_end, curr.a_char_end)
                new_b_end = max(prev.b_char_end, curr.b_char_end)
                new_a_line_end = max(prev.a_line_end, curr.a_line_end)
                new_b_line_end = max(prev.b_line_end, curr.b_line_end)

                prev.a_char_end = new_a_end
                prev.b_char_end = new_b_end
                prev.a_line_end = new_a_line_end
                prev.b_line_end = new_b_line_end
                prev.token_count += curr.token_count
                if source_a:
                    prev.snippet_a = source_a[prev.a_char_start:prev.a_char_end]
                if source_b:
                    prev.snippet_b = source_b[prev.b_char_start:prev.b_char_end]
            else:
                merged.append(curr)

        return merged
