"""
AST-Level Structural Comparison Module for CodeGuard.
Uses libclang (with a compiler-front-end token fallback) to extract:
1. Control-Flow Shape (loop and branch nesting hierarchy)
2. Statement-Type Sequences per function
3. Call Graphs and function invocation hierarchy
4. Subtree structural hashing
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional, Any
import hashlib
import re
import difflib

# Attempt importing libclang
HAVE_LIBCLANG = False
try:
    import clang.cindex
    # Test index creation
    _test_idx = clang.cindex.Index.create()
    HAVE_LIBCLANG = True
except Exception:
    HAVE_LIBCLANG = False


@dataclass
class FunctionStructure:
    name: str
    return_type: str
    param_count: int
    control_flow_tree: str                # Nested string representation, e.g. "For[If[Return],Return]"
    statement_kinds: List[str]            # Sequence of AST node kinds (e.g. VarDecl, ForStmt, BinaryOperator)
    called_functions: List[str]           # Names of functions called within this body
    line_start: int
    line_end: int
    subtree_hashes: Set[int] = field(default_factory=set)


@dataclass
class ASTComparisonResult:
    structural_similarity: float          # 0.0 to 100.0
    control_flow_similarity: float        # 0.0 to 100.0
    statement_sequence_similarity: float  # 0.0 to 100.0
    call_graph_similarity: float          # 0.0 to 100.0
    functions_a: List[FunctionStructure]
    functions_b: List[FunctionStructure]
    call_graph_a: Dict[str, List[str]]
    call_graph_b: Dict[str, List[str]]
    structural_explanation: List[str]


# Relevant Clang cursor kinds for control-flow analysis
CONTROL_FLOW_KINDS = {
    "IF_STMT", "FOR_STMT", "WHILE_STMT", "DO_STMT",
    "SWITCH_STMT", "CASE_STMT", "DEFAULT_STMT",
    "BREAK_STMT", "CONTINUE_STMT", "RETURN_STMT",
    "GOTO_STMT"
}

STATEMENT_KINDS = {
    "COMPOUND_STMT", "DECL_STMT", "IF_STMT", "FOR_STMT", "WHILE_STMT",
    "DO_STMT", "SWITCH_STMT", "CASE_STMT", "DEFAULT_STMT", "BREAK_STMT",
    "CONTINUE_STMT", "RETURN_STMT", "CALL_EXPR", "BINARY_OPERATOR",
    "UNARY_OPERATOR", "COMPOUND_ASSIGNMENT_OPERATOR", "ARRAY_SUBSCRIPT_EXPR",
    "VAR_DECL", "PARM_DECL"
}


class ASTAnalyzer:
    """
    Parses C and C++ source code into an Abstract Syntax Tree and extracts
    deep structural fingerprints independent of variable names and superficial text.
    """

    def __init__(self, language: str = "c"):
        self.language = language.lower()

    def parse_source(self, source_code: str, filename: str = "submission.c") -> List[FunctionStructure]:
        """
        Parses source code into a list of FunctionStructure objects.
        Uses libclang if available, or regex-based CFG extraction as fallback.
        """
        if HAVE_LIBCLANG:
            try:
                return self._parse_with_libclang(source_code, filename)
            except Exception:
                # Fallback to robust token/regex structural parser
                return self._parse_with_fallback(source_code)
        else:
            return self._parse_with_fallback(source_code)

    def _clean_source_for_clang(self, code: str) -> str:
        """
        Replaces system #include directives with empty lines so clang does not fail
        when host environment lacks standard C/C++ library headers.
        """
        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("#include") or stripped.startswith("#pragma"):
                lines.append("// " + line)
            else:
                lines.append(line)
        return "\n".join(lines)

    def _parse_with_libclang(self, source_code: str, filename: str) -> List[FunctionStructure]:
        import clang.cindex
        index = clang.cindex.Index.create()

        clean_code = self._clean_source_for_clang(source_code)
        ext = ".cpp" if self.language in ("cpp", "c++") else ".c"
        fn = "temp" + ext

        args = [
            "-std=c++17" if ext == ".cpp" else "-std=c11",
            "-fsyntax-only",
            "-Wno-everything"
        ]

        tu = index.parse(fn, args=args, unsaved_files=[(fn, clean_code)])
        functions: List[FunctionStructure] = []

        for cursor in tu.cursor.get_children():
            # Match function declarations with a definition body
            if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL and cursor.is_definition():
                func_name = cursor.spelling or "<anonymous>"
                ret_type = cursor.result_type.spelling if cursor.result_type else "void"
                params = [c for c in cursor.get_children() if c.kind == clang.cindex.CursorKind.PARM_DECL]

                # Extract statement sequence & control flow tree
                stmt_kinds: List[str] = []
                calls: List[str] = []
                subtree_hashes: Set[int] = set()

                cf_tree = self._traverse_clang_cursor(cursor, stmt_kinds, calls, subtree_hashes)

                l_start = cursor.extent.start.line if cursor.extent.start else 1
                l_end = cursor.extent.end.line if cursor.extent.end else 1

                functions.append(FunctionStructure(
                    name=func_name,
                    return_type=ret_type,
                    param_count=len(params),
                    control_flow_tree=cf_tree,
                    statement_kinds=stmt_kinds,
                    called_functions=calls,
                    line_start=l_start,
                    line_end=l_end,
                    subtree_hashes=subtree_hashes
                ))

        if not functions:
            # If libclang didn't find functions (e.g. single code snippet outside a function),
            # use the fallback parser to capture the structure of the snippet
            return self._parse_with_fallback(source_code)

        return functions

    def _traverse_clang_cursor(
        self,
        cursor: Any,
        stmt_kinds: List[str],
        calls: List[str],
        subtree_hashes: Set[int]
    ) -> str:
        """
        Recursively traverses a clang cursor to build control-flow tree and statement kinds.
        """
        import clang.cindex
        kind_name = cursor.kind.name

        if kind_name in STATEMENT_KINDS:
            stmt_kinds.append(kind_name)

        if cursor.kind == clang.cindex.CursorKind.CALL_EXPR:
            callee_name = cursor.spelling or ""
            if callee_name:
                calls.append(callee_name)

        # Build child representations
        child_trees = []
        child_hashes = []
        for child in cursor.get_children():
            child_cf = self._traverse_clang_cursor(child, stmt_kinds, calls, subtree_hashes)
            if child_cf:
                child_trees.append(child_cf)
            child_hashes.append(hash(child.kind.name))

        # Subtree hash calculation
        subtree_str = f"{kind_name}:" + ",".join(str(h) for h in child_hashes)
        st_hash = int.from_bytes(hashlib.md5(subtree_str.encode("utf-8")).digest()[:8], "big")
        subtree_hashes.add(st_hash)

        # Control flow representation
        if kind_name in CONTROL_FLOW_KINDS:
            short_name = kind_name.replace("_STMT", "").capitalize()
            if child_trees:
                return f"{short_name}[{','.join(child_trees)}]"
            return short_name
        elif child_trees:
            return ",".join(child_trees)

        return ""

    def _parse_with_fallback(self, source_code: str) -> List[FunctionStructure]:
        """
        Fallback parser that extracts control flow, statement kinds, and call graphs
        directly when libclang is unavailable or for freestanding code snippets.
        """
        from .lexer import CLexer
        from .token_types import TokenType

        tokens = CLexer(source_code).tokenize()
        functions: List[FunctionStructure] = []

        # Find function definitions: TYPE IDENT ( PARAMS ) { BODY }
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            # Look for identifier followed by '(' and eventually '{'
            if tok.type == TokenType.IDENTIFIER and i + 1 < n and tokens[i + 1].value == "(":
                func_name = tok.value
                ret_type = tokens[i - 1].value if i > 0 and tokens[i - 1].type == TokenType.KEYWORD else "void"

                # Find matching ')'
                depth = 1
                j = i + 2
                comma_count = 0
                has_tokens = False
                while j < n and depth > 0:
                    if tokens[j].value == "(":
                        depth += 1
                    elif tokens[j].value == ")":
                        depth -= 1
                    elif depth == 1:
                        if tokens[j].value == ",":
                            comma_count += 1
                        elif tokens[j].type != TokenType.PUNCTUATOR and tokens[j].value != "void":
                            has_tokens = True
                    j += 1

                param_count = (comma_count + 1) if has_tokens else 0

                # Check if followed by '{'
                if j < n and tokens[j].value == "{":
                    # Scan body until matching '}'
                    body_start = j
                    b_depth = 1
                    k = j + 1
                    body_tokens = []
                    while k < n and b_depth > 0:
                        if tokens[k].value == "{":
                            b_depth += 1
                        elif tokens[k].value == "}":
                            b_depth -= 1
                        if b_depth > 0:
                            body_tokens.append(tokens[k])
                        k += 1

                    # Extract CFG from body tokens
                    stmt_kinds, cf_tree, calls, subtrees = self._extract_cfg_from_tokens(body_tokens)

                    functions.append(FunctionStructure(
                        name=func_name,
                        return_type=ret_type,
                        param_count=param_count,
                        control_flow_tree=cf_tree,
                        statement_kinds=stmt_kinds,
                        called_functions=calls,
                        line_start=tok.location.line,
                        line_end=tokens[min(k, n - 1)].end_location.line,
                        subtree_hashes=subtrees
                    ))
                    i = k
                    continue
            i += 1

        if not functions:
            # Treat entire body as a single top-level block
            stmt_kinds, cf_tree, calls, subtrees = self._extract_cfg_from_tokens(tokens)
            l_start = tokens[0].location.line if tokens else 1
            l_end = tokens[-1].end_location.line if tokens else 1
            functions.append(FunctionStructure(
                name="<global>",
                return_type="void",
                param_count=0,
                control_flow_tree=cf_tree,
                statement_kinds=stmt_kinds,
                called_functions=calls,
                line_start=l_start,
                line_end=l_end,
                subtree_hashes=subtrees
            ))

        return functions

    def _extract_cfg_from_tokens(self, tokens: List[Any]) -> Tuple[List[str], str, List[str], Set[int]]:
        from .token_types import TokenType

        stmt_kinds: List[str] = []
        calls: List[str] = []
        cf_elements: List[str] = []
        subtrees: Set[int] = set()

        ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}
        COMP_OPS = {"==", "!=", "<", "<=", ">", ">="}
        ARITH_OPS = {"+", "-", "*", "/", "%"}
        LOGICAL_OPS = {"&&", "||", "!"}
        BITWISE_OPS = {"&", "|", "^", "~", "<<", ">>"}
        UNARY_OPS = {"++", "--"}
        TYPE_KW = {
            "int", "char", "float", "double", "void", "long", "short", "unsigned",
            "signed", "struct", "union", "auto", "const", "static", "volatile", "bool"
        }

        for idx, tok in enumerate(tokens):
            val = tok.value
            if val in ("if", "else"):
                stmt_kinds.append("IfStmt")
                cf_elements.append("If")
            elif val in ("for", "while", "do"):
                stmt_kinds.append("LoopStmt")
                cf_elements.append("Loop")
            elif val == "switch":
                stmt_kinds.append("SwitchStmt")
                cf_elements.append("Switch")
            elif val in ("break", "continue", "goto"):
                stmt_kinds.append("JumpStmt")
                cf_elements.append("Jump")
            elif val == "return":
                stmt_kinds.append("ReturnStmt")
                cf_elements.append("Return")
            elif val in TYPE_KW:
                stmt_kinds.append("DeclStmt")
            elif val == "[":
                stmt_kinds.append("ArrayAccess")
            elif val in ("->", "."):
                stmt_kinds.append("MemberAccess")
            elif val in ASSIGN_OPS:
                stmt_kinds.append("AssignOp")
            elif val in COMP_OPS:
                stmt_kinds.append("CompOp")
            elif val in LOGICAL_OPS:
                stmt_kinds.append("LogicalOp")
            elif val in UNARY_OPS:
                stmt_kinds.append("UnaryOp")
            elif val in ARITH_OPS:
                stmt_kinds.append("ArithOp")
            elif val in BITWISE_OPS:
                stmt_kinds.append("BitwiseOp")
            elif tok.type == TokenType.IDENTIFIER:
                if idx + 1 < len(tokens) and tokens[idx + 1].value == "(":
                    calls.append(val)
                    stmt_kinds.append("CallExpr")

        cf_tree = "-".join(cf_elements) if cf_elements else "Seq"
        # Generate subtree hashes from n-grams of statement kinds
        for i in range(len(stmt_kinds) - 2):
            ngram = "-".join(stmt_kinds[i:i + 3])
            subtrees.add(int.from_bytes(hashlib.md5(ngram.encode("utf-8")).digest()[:8], "big"))

        return stmt_kinds, cf_tree, calls, subtrees

    def compare_ast(
        self,
        source_a: str,
        source_b: str,
        filename_a: str = "prog_a.c",
        filename_b: str = "prog_b.c"
    ) -> ASTComparisonResult:
        """
        Compares two source files structurally at the AST level.
        Produces a structural similarity score (0.0 - 100.0) based on:
        - Control-flow tree similarity
        - Statement-kind sequence alignment
        - Call graph similarity
        """
        funcs_a = self.parse_source(source_a, filename_a)
        funcs_b = self.parse_source(source_b, filename_b)

        # 1. Build Call Graphs
        cg_a = {f.name: f.called_functions for f in funcs_a}
        cg_b = {f.name: f.called_functions for f in funcs_b}

        # 2. Control Flow Tree Similarity
        cf_score = self._compute_string_list_similarity(funcs_a, funcs_b)

        # 3. Statement-Kind Sequence Alignment
        all_stmts_a = []
        for f in funcs_a:
            all_stmts_a.extend(f.statement_kinds)
        all_stmts_b = []
        for f in funcs_b:
            all_stmts_b.extend(f.statement_kinds)

        stmt_score = self._compute_sequence_similarity(all_stmts_a, all_stmts_b)

        # 4. Call Graph & Function Structure Similarity
        cg_score = self._compute_call_graph_similarity(cg_a, cg_b, funcs_a, funcs_b)

        # Weighted Structural Score: 40% Control Flow, 35% Statement Sequence, 25% Call Graph
        total_structural = (0.40 * cf_score) + (0.35 * stmt_score) + (0.25 * cg_score)

        # Explanations of structural patterns
        explanations = []
        if cf_score >= 85.0:
            explanations.append("Matching control-flow hierarchy: both programs share identical loop/branch nesting patterns.")
        elif cf_score >= 50.0:
            explanations.append("Partially matching control-flow hierarchy: similar loop and branch constructs detected.")
        else:
            explanations.append("Divergent control-flow hierarchy: loops, conditionals, and branches differ significantly.")

        if stmt_score >= 80.0:
            explanations.append("High AST statement-type correlation: internal statement execution sequence is structurally preserved.")
        elif stmt_score >= 40.0:
            explanations.append("Moderate AST statement correlation: partially overlapping statement structure.")

        if cg_score >= 80.0:
            explanations.append("Compatible call graph topology: function invocation structures are highly congruent.")

        return ASTComparisonResult(
            structural_similarity=round(min(100.0, max(0.0, total_structural)), 2),
            control_flow_similarity=round(min(100.0, max(0.0, cf_score)), 2),
            statement_sequence_similarity=round(min(100.0, max(0.0, stmt_score)), 2),
            call_graph_similarity=round(min(100.0, max(0.0, cg_score)), 2),
            functions_a=funcs_a,
            functions_b=funcs_b,
            call_graph_a=cg_a,
            call_graph_b=cg_b,
            structural_explanation=explanations
        )

    def _compute_string_list_similarity(self, funcs_a: List[FunctionStructure], funcs_b: List[FunctionStructure]) -> float:
        """Calculates similarity between two sets of control-flow tree strings weighted by statement complexity."""
        if not funcs_a and not funcs_b:
            return 100.0
        if not funcs_a or not funcs_b:
            return 0.0

        list_a = [f.control_flow_tree for f in funcs_a if f.control_flow_tree]
        list_b = [f.control_flow_tree for f in funcs_b if f.control_flow_tree]

        if sorted(list_a) == sorted(list_b):
            return 100.0

        weights_a = [max(1, len(f.statement_kinds)) for f in funcs_a]
        total_w_a = sum(weights_a)
        weights_b = [max(1, len(f.statement_kinds)) for f in funcs_b]
        total_w_b = sum(weights_b)

        # Best-match weighted average from A to B
        weighted_score_a = 0.0
        for fa, wa in zip(funcs_a, weights_a):
            tree_a = fa.control_flow_tree.replace("[", "-").replace("]", "").split("-")
            best = max(
                difflib.SequenceMatcher(None, tree_a, fb.control_flow_tree.replace("[", "-").replace("]", "").split("-")).ratio()
                for fb in funcs_b
            )
            weighted_score_a += (wa / total_w_a) * best

        # Best-match weighted average from B to A
        weighted_score_b = 0.0
        for fb, wb in zip(funcs_b, weights_b):
            tree_b = fb.control_flow_tree.replace("[", "-").replace("]", "").split("-")
            best = max(
                difflib.SequenceMatcher(None, tree_b, fa.control_flow_tree.replace("[", "-").replace("]", "").split("-")).ratio()
                for fa in funcs_a
            )
            weighted_score_b += (wb / total_w_b) * best

        avg = (weighted_score_a + weighted_score_b) / 2.0
        return avg * 100.0

    def _compute_sequence_similarity(self, seq_a: List[str], seq_b: List[str]) -> float:
        """Calculates Gestalt pattern sequence similarity between AST node kind streams."""
        if not seq_a and not seq_b:
            return 100.0
        if not seq_a or not seq_b:
            return 0.0

        if seq_a == seq_b:
            return 100.0

        matcher = difflib.SequenceMatcher(None, seq_a, seq_b)
        return matcher.ratio() * 100.0

    def _compute_call_graph_similarity(
        self,
        cg_a: Dict[str, List[str]],
        cg_b: Dict[str, List[str]],
        funcs_a: List[FunctionStructure],
        funcs_b: List[FunctionStructure]
    ) -> float:
        """Compares function counts, parameters, and invocation topology."""
        if not funcs_a and not funcs_b:
            return 100.0
        if not funcs_a or not funcs_b:
            return 0.0

        # Function count parity
        count_sim = min(len(funcs_a), len(funcs_b)) / max(len(funcs_a), len(funcs_b))

        # Parameter distribution similarity
        params_a = sorted([f.param_count for f in funcs_a])
        params_b = sorted([f.param_count for f in funcs_b])
        param_matcher = difflib.SequenceMatcher(None, params_a, params_b)
        param_sim = param_matcher.ratio()

        # Identify internal function names
        names_a = {f.name for f in funcs_a if f.name != "<global>"}
        names_b = {f.name for f in funcs_b if f.name != "<global>"}

        # Internal call edges (calls among defined functions)
        internal_calls_a = sum(1 for calls in cg_a.values() for c in calls if c in names_a)
        internal_calls_b = sum(1 for calls in cg_b.values() for c in calls if c in names_b)

        # Recursion check
        rec_a = sum(1 for fname, calls in cg_a.items() if fname in calls)
        rec_b = sum(1 for fname, calls in cg_b.items() if fname in calls)
        rec_sim = 1.0 if (rec_a == 0 and rec_b == 0) else (min(rec_a, rec_b) / max(rec_a, rec_b) if max(rec_a, rec_b) > 0 else 0.0)

        # External / stdlib calls overlap
        ext_a = set(c for calls in cg_a.values() for c in calls if c not in names_a)
        ext_b = set(c for calls in cg_b.values() for c in calls if c not in names_b)
        if ext_a or ext_b:
            ext_sim = len(ext_a & ext_b) / len(ext_a | ext_b) if (ext_a | ext_b) else 0.0
        else:
            ext_sim = 1.0

        # Internal edge topology similarity
        if internal_calls_a == 0 and internal_calls_b == 0:
            edge_sim = 1.0
        elif max(internal_calls_a, internal_calls_b) > 0:
            edge_sim = min(internal_calls_a, internal_calls_b) / max(internal_calls_a, internal_calls_b)
        else:
            edge_sim = 0.0

        combined = (0.25 * count_sim) + (0.25 * param_sim) + (0.25 * edge_sim) + (0.15 * ext_sim) + (0.10 * rec_sim)
        return combined * 100.0
