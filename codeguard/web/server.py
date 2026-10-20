"""
HTTP Server and REST API for CodeGuard UI.
Built on Python's standard library http.server for 100% zero-dependency execution.
"""
import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List

# Ensure codeguard is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from codeguard.core.engine import CodeGuardEngine, CodeGuardResult
from codeguard.core.ast_analyzer import ASTAnalyzer
from codeguard.core.function_analyzer import FunctionLevelAnalyzer
from codeguard.core.batch import BatchEngine, FileSubmission
from codeguard.core.report_generator import ReportGenerator

STATIC_DIR = os.path.join(CURRENT_DIR, "static")

# Supported Languages Configuration (Extensible)
LANGUAGE_CONFIG = [
    {"id": "c", "name": "C (C11)", "enabled": True},
    {"id": "cpp", "name": "C++ (C++17)", "enabled": True},
    {"id": "python", "name": "Python (Coming Soon)", "enabled": False, "note": "Compiler AST engine extension planned"}
]

# Benchmark sample pairs for quick evaluation in viva/testing
def load_benchmark_fixtures() -> Dict[str, Dict[str, str]]:
    fixtures_dir = os.path.join(PROJECT_ROOT, "tests", "fixtures")
    presets = {}

    fixture_keys = [
        ("pair_identical", "Identical Submissions (100% Match)"),
        ("pair_renamed", "Renamed Variables & Stripped Comments (Plagiarism Attempt)"),
        ("pair_reordered", "Reordered Statements & Refactored Functions"),
        ("pair_unrelated", "Completely Unrelated Algorithms (QuickSort vs Matrix Multiply)"),
        ("pair_short", "Short 3-line Function (Low Confidence Caveat Test)")
    ]

    for dir_name, title in fixture_keys:
        p_a = os.path.join(fixtures_dir, dir_name, "program_a.c")
        p_b = os.path.join(fixtures_dir, dir_name, "program_b.c")
        if os.path.exists(p_a) and os.path.exists(p_b):
            with open(p_a, "r", encoding="utf-8") as fa, open(p_b, "r", encoding="utf-8") as fb:
                presets[dir_name] = {
                    "title": title,
                    "code_a": fa.read(),
                    "code_b": fb.read(),
                    "language": "c"
                }

    return presets


PRESETS = load_benchmark_fixtures()


class CodeGuardRequestHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            self._send_json({
                "languages": LANGUAGE_CONFIG,
                "presets": {k: {"title": v["title"], "language": v["language"]} for k, v in PRESETS.items()}
            })
            return

        if path.startswith("/api/presets/"):
            preset_id = path.replace("/api/presets/", "")
            if preset_id in PRESETS:
                self._send_json(PRESETS[preset_id])
            else:
                self.send_error(404, "Preset not found")
            return

        # Serve static frontend files
        if path == "" or path == "/" or path == "/index.html":
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/styles.css":
            self._serve_file(os.path.join(STATIC_DIR, "styles.css"), "text/css; charset=utf-8")
        elif path == "/app.js":
            self._serve_file(os.path.join(STATIC_DIR, "app.js"), "application/javascript; charset=utf-8")
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len)

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self._send_json({"error": "Malformed JSON payload in request."}, status=400)
            return

        if path == "/api/compare":
            self._handle_compare(body)
        elif path == "/api/batch":
            self._handle_batch(body)
        elif path == "/api/report":
            self._handle_report(body)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data: Any, status: int = 200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _serve_file(self, filepath: str, mime_type: str):
        if not os.path.exists(filepath):
            self.send_error(404, f"File not found: {os.path.basename(filepath)}")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_compare(self, body: Dict[str, Any]):
        code_a = body.get("code_a", "")
        code_b = body.get("code_b", "")
        lang = body.get("language", "c")
        filename_a = body.get("filename_a", "submission_a.c")
        filename_b = body.get("filename_b", "submission_b.c")

        if not code_a or not code_b or not code_a.strip() or not code_b.strip():
            self._send_json({"error": "Both Program A and Program B source code must be provided."}, status=400)
            return

        if lang not in ("c", "cpp"):
            self._send_json({"error": f"Unsupported language '{lang}'. Only 'c' and 'cpp' are supported."}, status=400)
            return

        if len(code_a) > 2_000_000 or len(code_b) > 2_000_000:
            self._send_json({"error": "Input file exceeds maximum allowed size (2 MB per file)."}, status=413)
            return

        try:
            engine = CodeGuardEngine()
            res = engine.compare(code_a, code_b, language=lang, filename_a=filename_a, filename_b=filename_b)

            # Function-level breakdown (Phase 4.1)
            funcs_a = ASTAnalyzer(language=lang).parse_source(code_a)
            funcs_b = ASTAnalyzer(language=lang).parse_source(code_b)
            func_analyzer = FunctionLevelAnalyzer()
            func_matches = func_analyzer.analyze(code_a, code_b, funcs_a, funcs_b)

            func_matches_dict = [
                {
                    "function_a": m.function_a,
                    "function_b": m.function_b,
                    "line_range_a": m.line_range_a,
                    "line_range_b": m.line_range_b,
                    "token_similarity": m.token_similarity,
                    "structural_similarity": m.structural_similarity,
                    "overall_similarity": m.overall_similarity,
                    "verdict": m.verdict
                }
                for m in func_matches
            ]

            result_dict = res.to_dict()
            result_dict["function_matches"] = func_matches_dict

            self._send_json(result_dict)
        except Exception as e:
            self._send_json({"error": f"Plagiarism analysis failed: {str(e)}"}, status=500)

    def _handle_batch(self, body: Dict[str, Any]):
        raw_submissions = body.get("submissions", [])
        threshold = float(body.get("threshold", 70.0))

        if not raw_submissions or len(raw_submissions) < 2:
            self._send_json({"error": "At least 2 submissions are required for batch analysis."}, status=400)
            return

        if len(raw_submissions) > 50:
            self._send_json({"error": "Batch analysis is limited to a maximum of 50 submissions at a time."}, status=400)
            return

        try:
            submissions = [
                FileSubmission(
                    filename=s.get("filename", f"file_{i+1}.c"),
                    author=s.get("author", f"Student {i+1}"),
                    content=s.get("content", ""),
                    language=s.get("language", "c")
                )
                for i, s in enumerate(raw_submissions)
            ]

            batch_engine = BatchEngine(flag_threshold=threshold)
            report = batch_engine.analyze_batch(submissions)

            comps = report.comparisons
            high_cnt = sum(1 for p in comps if p.risk_level == "HIGH")
            med_cnt = sum(1 for p in comps if p.risk_level == "MEDIUM")
            low_cnt = sum(1 for p in comps if p.risk_level == "LOW")
            max_sim = round(max((p.overall_similarity for p in comps), default=0.0), 1) if comps else 0.0
            avg_sim = round(sum(p.overall_similarity for p in comps) / len(comps), 1) if comps else 0.0

            resp = {
                "total_submissions": report.total_submissions,
                "total_comparisons": report.total_comparisons,
                "flagged_pairs_count": report.flagged_pairs_count,
                "high_risk_count": high_cnt,
                "medium_risk_count": med_cnt,
                "low_risk_count": low_cnt,
                "highest_similarity": max_sim,
                "average_similarity": avg_sim,
                "file_labels": report.file_labels,
                "pairwise_matrix": report.pairwise_matrix,
                "submissions": [
                    {
                        "filename": s.filename,
                        "author": s.author,
                        "content": s.content
                    }
                    for s in submissions
                ],
                "flagged_pairs": [
                    {
                        "file_a": p.file_a,
                        "file_b": p.file_b,
                        "author_a": p.author_a,
                        "author_b": p.author_b,
                        "overall_similarity": p.overall_similarity,
                        "token_similarity": p.token_similarity,
                        "structural_similarity": p.structural_similarity,
                        "risk_level": p.risk_level,
                        "risk_color": p.risk_color,
                        "is_flagged": p.is_flagged
                    }
                    for p in report.high_risk_pairs
                ],
                "high_risk_pairs": [
                    {
                        "file_a": p.file_a,
                        "file_b": p.file_b,
                        "author_a": p.author_a,
                        "author_b": p.author_b,
                        "overall_similarity": p.overall_similarity,
                        "token_similarity": p.token_similarity,
                        "structural_similarity": p.structural_similarity,
                        "risk_level": p.risk_level,
                        "risk_color": p.risk_color,
                        "is_flagged": p.is_flagged
                    }
                    for p in report.high_risk_pairs
                ],
                "comparisons": [
                    {
                        "file_a": p.file_a,
                        "file_b": p.file_b,
                        "author_a": p.author_a,
                        "author_b": p.author_b,
                        "overall_similarity": p.overall_similarity,
                        "risk_level": p.risk_level,
                        "is_flagged": p.is_flagged
                    }
                    for p in report.comparisons
                ]
            }
            self._send_json(resp)
        except Exception as e:
            self._send_json({"error": f"Batch analysis failed: {str(e)}"}, status=500)

    def _handle_report(self, body: Dict[str, Any]):
        code_a = body.get("code_a", "")
        code_b = body.get("code_b", "")
        lang = body.get("language", "c")
        filename_a = body.get("filename_a", "program_a.c")
        filename_b = body.get("filename_b", "program_b.c")
        author_a = body.get("author_a", "Student A")
        author_b = body.get("author_b", "Student B")

        if not code_a or not code_b or not code_a.strip() or not code_b.strip():
            self._send_json({"error": "Both Program A and Program B source code must be provided to generate a report."}, status=400)
            return

        try:
            engine = CodeGuardEngine()
            res = engine.compare(code_a, code_b, language=lang, filename_a=filename_a, filename_b=filename_b)

            funcs_a = ASTAnalyzer(language=lang).parse_source(code_a)
            funcs_b = ASTAnalyzer(language=lang).parse_source(code_b)
            func_matches = FunctionLevelAnalyzer().analyze(code_a, code_b, funcs_a, funcs_b)

            html_content = ReportGenerator.generate_html_report(
                res, filename_a, filename_b, func_matches, author_a, author_b
            )

            resp_bytes = html_content.encode("utf-8")
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)
        except Exception as e:
            self._send_json({"error": f"Report generation failed: {str(e)}"}, status=500)

    def log_message(self, format, *args):
        # Concise logging to stdout
        sys.stdout.write(f"[CodeGuard Server] {self.address_string()} - {format % args}\n")


def start_server(host: str = "0.0.0.0", port: int = 8080):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, CodeGuardRequestHandler)
    print(f"============================================================")
    print(f"  CodeGuard Plagiarism Detection Server running at:")
    print(f"  -> http://localhost:{port}/")
    print(f"  -> http://127.0.0.1:{port}/")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down CodeGuard server.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_server(port=port)
