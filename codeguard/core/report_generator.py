"""
Report Generation for CodeGuard (Phase 4 Feature 3).
Generates comprehensive printable/PDF reports detailing similarity metrics,
AST structural evidence, function matches, and detected transformations.
"""
from typing import List, Dict, Any, Optional
import html
import datetime
from .engine import CodeGuardResult
from .function_analyzer import FunctionMatch


class ReportGenerator:
    """
    Generates structured, styled reports suitable for academic misconduct investigations.
    """

    @staticmethod
    def generate_html_report(
        result: CodeGuardResult,
        filename_a: str = "program_a.c",
        filename_b: str = "program_b.c",
        function_matches: Optional[List[FunctionMatch]] = None,
        author_a: str = "Student A",
        author_b: str = "Student B"
    ) -> str:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        matched_regions_rows = ""
        for idx, r in enumerate(result.matched_regions[:15], 1):
            snip_a = html.escape(r.get("snippet_a", "")[:120])
            snip_b = html.escape(r.get("snippet_b", "")[:120])
            matched_regions_rows += f"""
            <tr>
                <td>#{idx}</td>
                <td>Lines {r['a_line_start']}–{r['a_line_end']}</td>
                <td>Lines {r['b_line_start']}–{r['b_line_end']}</td>
                <td>{r['token_count']}</td>
                <td><code>{snip_a}</code></td>
            </tr>
            """

        func_rows = ""
        if function_matches:
            for fm in function_matches:
                verdict_color = "#ef4444" if fm.verdict in ("COPIED", "SUSPICIOUS") else "#10b981"
                func_rows += f"""
                <tr>
                    <td><strong>{html.escape(fm.function_a)}</strong></td>
                    <td><strong>{html.escape(fm.function_b)}</strong></td>
                    <td><code>{html.escape(fm.line_range_a)}</code></td>
                    <td><code>{html.escape(fm.line_range_b)}</code></td>
                    <td>{fm.token_similarity:.1f}%</td>
                    <td>{fm.structural_similarity:.1f}%</td>
                    <td><strong>{fm.overall_similarity:.1f}%</strong></td>
                    <td><span style="color: {verdict_color}; font-weight: bold;">{fm.verdict}</span></td>
                </tr>
                """

        explanations_li = "".join(f"<li>{html.escape(e)}</li>" for e in result.explanations)

        warning_block = ""
        if result.warning_message:
            warning_block = f"""
            <div class="alert-box warning">
                <strong>Limitation Notice:</strong> {html.escape(result.warning_message)}
            </div>
            """

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CodeGuard Plagiarism Inspection Report — {html.escape(filename_a)} vs {html.escape(filename_b)}</title>
<style>
    @media print {{
        body {{ margin: 0; padding: 15mm; font-size: 11pt; color: #111; }}
        .no-print {{ display: none; }}
        .page-break {{ page-break-after: always; }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.5;
        color: #1f2937;
        background: #f9fafb;
        margin: 0;
        padding: 40px;
    }}
    .container {{
        max-width: 900px;
        margin: 0 auto;
        background: #ffffff;
        padding: 40px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .header {{
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 20px;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .title {{ font-size: 24px; font-weight: 800; color: #111827; margin: 0; }}
    .subtitle {{ color: #6b7280; font-size: 14px; margin-top: 5px; }}
    .badge {{
        display: inline-block;
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 14px;
        color: white;
        background-color: {result.risk_color};
    }}
    .metrics-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 25px;
    }}
    .metric-card {{
        background: #f3f4f6;
        padding: 16px;
        border-radius: 6px;
        text-align: center;
    }}
    .metric-value {{ font-size: 28px; font-weight: 800; color: #1f2937; }}
    .metric-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #6b7280; margin-top: 4px; }}
    .alert-box {{
        padding: 14px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-size: 13px;
    }}
    .alert-box.warning {{
        background: #fef3c7;
        color: #92400e;
        border-left: 4px solid #f59e0b;
    }}
    h2 {{ font-size: 18px; color: #111827; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; margin-top: 30px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
    th {{ background: #f9fafb; font-weight: 600; color: #4b5563; }}
    code {{ background: #f3f4f6; padding: 2px 5px; border-radius: 4px; font-family: monospace; font-size: 12px; }}
    .print-btn {{
        background: #2563eb;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <div class="title">CodeGuard Plagiarism Inspection Report</div>
            <div class="subtitle">Generated on {now} &bull; Compiler Front-End Source Analysis</div>
        </div>
        <div>
            <span class="badge">{result.risk_level} RISK</span>
            <button class="print-btn no-print" onclick="window.print()" style="margin-left: 10px;">Print / Save PDF</button>
        </div>
    </div>

    {warning_block}

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value">{result.overall_similarity:.1f}%</div>
            <div class="metric-label">Composite Similarity</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{result.token_similarity:.1f}%</div>
            <div class="metric-label">Token Winnowing (Phase 1)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{result.structural_similarity:.1f}%</div>
            <div class="metric-label">AST Structure (Phase 2)</div>
        </div>
    </div>

    <div class="metrics-grid" style="grid-template-columns: repeat(3, 1fr); margin-top: -10px;">
        <div class="metric-card" style="padding: 10px;">
            <div class="metric-value" style="font-size: 20px;">{result.control_flow_similarity:.1f}%</div>
            <div class="metric-label">Control-Flow CFG</div>
        </div>
        <div class="metric-card" style="padding: 10px;">
            <div class="metric-value" style="font-size: 20px;">{result.statement_similarity:.1f}%</div>
            <div class="metric-label">Statement Sequence</div>
        </div>
        <div class="metric-card" style="padding: 10px;">
            <div class="metric-value" style="font-size: 20px;">{result.call_graph_similarity:.1f}%</div>
            <div class="metric-label">Call Graph Topology</div>
        </div>
    </div>

    <h2>Submissions Information</h2>
    <table>
        <tr>
            <th>Program A</th>
            <td>{html.escape(filename_a)} ({author_a}) &bull; {result.tokens_count_a} normalized tokens</td>
        </tr>
        <tr>
            <th>Program B</th>
            <td>{html.escape(filename_b)} ({author_b}) &bull; {result.tokens_count_b} normalized tokens</td>
        </tr>
        <tr>
            <th>Language</th>
            <td>{html.escape(result.language.upper())} (C11 / C++17 Front-End)</td>
        </tr>
    </table>

    <h2>Forensic Transformation Explanation</h2>
    <ul>
        {explanations_li}
    </ul>

    {"<h2>Function-Level Match Breakdown</h2><table><thead><tr><th>Function A</th><th>Function B</th><th>Line Range A</th><th>Line Range B</th><th>Token Sim</th><th>AST Sim</th><th>Overall</th><th>Verdict</th></tr></thead><tbody>" + func_rows + "</tbody></table>" if func_rows else ""}

    <h2>Matched Fingerprint Regions (Top Matches)</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Program A</th>
                <th>Program B</th>
                <th>Tokens</th>
                <th>Sample Snippet</th>
            </tr>
        </thead>
        <tbody>
            {matched_regions_rows if matched_regions_rows else "<tr><td colspan='5'>No matching fingerprint regions detected.</td></tr>"}
        </tbody>
    </table>

    <div style="margin-top: 40px; padding-top: 15px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; text-align: center;">
        CodeGuard Compiler-Based Plagiarism Detection Engine &bull; Academic Integrity Evaluation
    </div>
</div>
</body>
</html>
"""
        return html_template
