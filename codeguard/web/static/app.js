/**
 * CodeGuard Front-End Client Application
 * Handles dual-editor synchronization, benchmark loading, REST API calls,
 * side-by-side match highlighting, SVG radial gauge animation, and faculty batch analytics.
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements - Navigation & Core Controls
    const langSelect = document.getElementById("lang-select");
    const codeA = document.getElementById("code-a");
    const codeB = document.getElementById("code-b");
    const linesA = document.getElementById("lines-a");
    const linesB = document.getElementById("lines-b");
    const metaA = document.getElementById("meta-a");
    const metaB = document.getElementById("meta-b");
    const titleA = document.getElementById("title-a");
    const titleB = document.getElementById("title-b");
    const fileUploadA = document.getElementById("file-upload-a");
    const fileUploadB = document.getElementById("file-upload-b");
    const btnCopyA = document.getElementById("btn-copy-a");
    const btnCopyB = document.getElementById("btn-copy-b");
    const btnCompare = document.getElementById("btn-compare");
    const btnClear = document.getElementById("btn-clear-editors");
    const resultsPanel = document.getElementById("results-panel");
    const btnExportReport = document.getElementById("btn-export-report");
    const themeToggleBtn = document.getElementById("theme-toggle");

    // ----------------------------------------------------
    // 0. Theme Management (Light & Dark Mode)
    // ----------------------------------------------------
    function initTheme() {
        const savedTheme = localStorage.getItem("codeguard_theme");
        if (savedTheme === "dark" || savedTheme === "light") {
            setTheme(savedTheme);
        } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            setTheme("dark");
        } else {
            setTheme("light");
        }
    }

    function setTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("codeguard_theme", theme);
        if (themeToggleBtn) {
            themeToggleBtn.setAttribute("title", theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode");
        }
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme") || "light";
            const nextTheme = current === "dark" ? "light" : "dark";
            setTheme(nextTheme);
        });
    }

    initTheme();

    // Tab Switcher
    const tabBtnPair = document.getElementById("tab-btn-pair");
    const tabBtnBatch = document.getElementById("tab-btn-batch");
    const viewPair = document.getElementById("view-pairwise");
    const viewBatch = document.getElementById("view-batch");

    // Metrics & Risk Elements
    const scoreOverall = document.getElementById("score-overall");
    const radialCircle = document.getElementById("radial-progress-circle");
    const badgeRisk = document.getElementById("badge-risk");
    const scoreToken = document.getElementById("score-token");
    const barToken = document.getElementById("bar-token");
    const fpCount = document.getElementById("fingerprint-count");

    const scoreAst = document.getElementById("score-ast");
    const scoreCfg = document.getElementById("score-cfg");
    const barCfg = document.getElementById("bar-cfg");
    const scoreStmt = document.getElementById("score-stmt");
    const barStmt = document.getElementById("bar-stmt");
    const scoreCg = document.getElementById("score-cg");
    const barCg = document.getElementById("bar-cg");

    // Forensic & Function Table Elements
    const shortCodeBanner = document.getElementById("short-code-banner");
    const shortCodeText = document.getElementById("short-code-text");
    const explanationList = document.getElementById("explanation-list");
    const funcBreakdownBody = document.getElementById("func-breakdown-body");
    const highlightPaneA = document.getElementById("highlight-pane-a");
    const highlightPaneB = document.getElementById("highlight-pane-b");

    // Batch Dashboard Elements
    const batchFileUpload = document.getElementById("batch-file-upload");
    const btnLoadBatch = document.getElementById("btn-load-sample-batch");
    const batchTotalSub = document.getElementById("batch-total-sub");
    const batchTotalPairs = document.getElementById("batch-total-pairs");
    const batchFlaggedCount = document.getElementById("batch-flagged-count");
    const heatmapContainer = document.getElementById("heatmap-container");
    const flaggedPairsBody = document.getElementById("flagged-pairs-body");

    let currentBatchData = null;

    // ----------------------------------------------------
    // 1. Tab Switching
    // ----------------------------------------------------
    function switchTab(target) {
        if (target === "pair") {
            tabBtnPair.classList.add("active");
            tabBtnPair.setAttribute("aria-selected", "true");
            tabBtnBatch.classList.remove("active");
            tabBtnBatch.setAttribute("aria-selected", "false");
            viewPair.classList.add("active");
            viewBatch.classList.remove("active");
        } else {
            tabBtnBatch.classList.add("active");
            tabBtnBatch.setAttribute("aria-selected", "true");
            tabBtnPair.classList.remove("active");
            tabBtnPair.setAttribute("aria-selected", "false");
            viewBatch.classList.add("active");
            viewPair.classList.remove("active");
        }
    }

    tabBtnPair.addEventListener("click", () => switchTab("pair"));
    tabBtnBatch.addEventListener("click", () => switchTab("batch"));

    // ----------------------------------------------------
    // 2. Editor Gutter & Token Metadata
    // ----------------------------------------------------
    function updateEditorMeta(textarea, gutter, metaElem) {
        const text = textarea.value;
        const lines = text.split("\n");
        const lineCount = lines.length;
        gutter.textContent = Array.from({ length: lineCount }, (_, i) => i + 1).join("\n");

        // Token estimation
        const trimmed = text.trim();
        const tokensEst = trimmed ? trimmed.split(/\s+|[;,{}()+\-*\/=<>!&|#]/).filter(t => t.length > 0).length : 0;
        metaElem.textContent = `${lineCount} lines • ~${tokensEst} tokens`;
    }

    codeA.addEventListener("input", () => updateEditorMeta(codeA, linesA, metaA));
    codeB.addEventListener("input", () => updateEditorMeta(codeB, linesB, metaB));

    // Scroll synchronization between textarea and line gutter
    codeA.addEventListener("scroll", () => { linesA.scrollTop = codeA.scrollTop; });
    codeB.addEventListener("scroll", () => { linesB.scrollTop = codeB.scrollTop; });

    // Copy code buttons
    function attachCopyButton(btn, textarea) {
        if (!btn) return;
        btn.addEventListener("click", async () => {
            const val = textarea.value;
            if (!val) return;
            try {
                await navigator.clipboard.writeText(val);
                const originalHtml = btn.innerHTML;
                btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                setTimeout(() => { btn.innerHTML = originalHtml; }, 1500);
            } catch (err) {
                console.error("Clipboard copy failed", err);
            }
        });
    }
    attachCopyButton(btnCopyA, codeA);
    attachCopyButton(btnCopyB, codeB);

    // ----------------------------------------------------
    // 3. Preset Benchmark Loader
    // ----------------------------------------------------
    document.querySelectorAll(".preset-chip[data-preset]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const presetKey = btn.getAttribute("data-preset");
            try {
                const res = await fetch(`/api/presets/${presetKey}`);
                if (!res.ok) throw new Error("Preset not found");
                const data = await res.json();
                codeA.value = data.code_a;
                codeB.value = data.code_b;
                if (data.language) langSelect.value = data.language;
                titleA.textContent = "program_a.c";
                titleB.textContent = "program_b.c";
                updateEditorMeta(codeA, linesA, metaA);
                updateEditorMeta(codeB, linesB, metaB);
                // Execute comparison
                runComparison();
            } catch (err) {
                console.error("Error loading benchmark:", err);
            }
        });
    });

    // ----------------------------------------------------
    // 4. File Upload & Drag-and-Drop
    // ----------------------------------------------------
    function handleFileSelection(file, textarea, gutter, metaElem, titleElem) {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            textarea.value = e.target.result;
            if (titleElem) titleElem.textContent = file.name;
            updateEditorMeta(textarea, gutter, metaElem);
        };
        reader.readAsText(file);
    }

    if (fileUploadA) {
        fileUploadA.addEventListener("change", (e) => {
            handleFileSelection(e.target.files[0], codeA, linesA, metaA, titleA);
        });
    }

    if (fileUploadB) {
        fileUploadB.addEventListener("change", (e) => {
            handleFileSelection(e.target.files[0], codeB, linesB, metaB, titleB);
        });
    }

    // Drag and drop onto IDE windows
    [
        { frame: document.getElementById("ide-frame-a"), textarea: codeA, gutter: linesA, meta: metaA, title: titleA },
        { frame: document.getElementById("ide-frame-b"), textarea: codeB, gutter: linesB, meta: metaB, title: titleB }
    ].forEach(({ frame, textarea, gutter, meta, title }) => {
        if (!frame) return;
        frame.addEventListener("dragover", (e) => {
            e.preventDefault();
            frame.style.borderColor = "var(--primary)";
        });
        frame.addEventListener("dragleave", () => {
            frame.style.borderColor = "";
        });
        frame.addEventListener("drop", (e) => {
            e.preventDefault();
            frame.style.borderColor = "";
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files[0], textarea, gutter, meta, title);
            }
        });
    });

    btnClear.addEventListener("click", () => {
        codeA.value = "";
        codeB.value = "";
        titleA.textContent = "program_a.c";
        titleB.textContent = "program_b.c";
        updateEditorMeta(codeA, linesA, metaA);
        updateEditorMeta(codeB, linesB, metaB);
        resultsPanel.classList.add("hidden");
    });

    // Keyboard shortcut Ctrl + Enter to run comparison
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            runComparison();
        }
    });

    // ----------------------------------------------------
    // 5. Comparison Execution & Results Rendering
    // ----------------------------------------------------
    async function runComparison() {
        const textA = codeA.value.trim();
        const textB = codeB.value.trim();
        if (!textA || !textB) {
            alert("Please enter or upload C/C++ source code in both Program A and Program B.");
            return;
        }

        btnCompare.disabled = true;
        btnCompare.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin-icon">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                <path d="M12 2a10 10 0 0 1 10 10"></path>
            </svg>
            <span>Analyzing Compiler AST &amp; Winnowing...</span>
        `;

        try {
            const resp = await fetch("/api/compare", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code_a: textA,
                    code_b: textB,
                    language: langSelect.value,
                    filename_a: titleA.textContent || "program_a.c",
                    filename_b: titleB.textContent || "program_b.c"
                })
            });

            if (!resp.ok) {
                const errJson = await resp.json().catch(() => ({}));
                throw new Error(errJson.error || `Comparison request failed (${resp.status})`);
            }
            const data = await resp.json();
            renderResults(data, textA, textB);
        } catch (err) {
            alert("Analysis Error: " + err.message);
        } finally {
            btnCompare.disabled = false;
            btnCompare.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon-svg">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
                <span>Run Compiler Analysis</span>
                <span class="btn-shortcut-badge">Ctrl + ↵</span>
            `;
        }
    }

    btnCompare.addEventListener("click", runComparison);

    function renderResults(data, rawA, rawB) {
        resultsPanel.classList.remove("hidden");

        const score = data.overall_similarity;
        scoreOverall.textContent = `${score.toFixed(1)}%`;

        // Radial progress arc calculation (circumference = 2 * pi * 50 = 314.16)
        const circumference = 314.16;
        const offset = circumference - (score / 100.0) * circumference;
        if (radialCircle) {
            radialCircle.style.strokeDashoffset = offset;
            if (data.risk_level === "HIGH") {
                radialCircle.style.stroke = "var(--risk-high)";
            } else if (data.risk_level === "MEDIUM") {
                radialCircle.style.stroke = "var(--risk-med)";
            } else {
                radialCircle.style.stroke = "var(--risk-low)";
            }
        }

        // Risk Badge
        badgeRisk.className = "risk-badge";
        if (data.risk_level === "HIGH") {
            badgeRisk.classList.add("badge-high");
            badgeRisk.textContent = "HIGH RISK";
        } else if (data.risk_level === "MEDIUM") {
            badgeRisk.classList.add("badge-med");
            badgeRisk.textContent = "MEDIUM RISK";
        } else {
            badgeRisk.classList.add("badge-low");
            badgeRisk.textContent = "LOW RISK";
        }

        // Phase 1 Token Winnowing Metrics
        scoreToken.textContent = `${data.token_similarity.toFixed(1)}%`;
        if (barToken) barToken.style.width = `${data.token_similarity}%`;
        const matchedFps = data.matched_regions ? data.matched_regions.length : 0;
        fpCount.textContent = `${matchedFps} matched fingerprint region(s)`;

        // Phase 2 AST Structural Metrics
        scoreAst.textContent = `${data.structural_similarity.toFixed(1)}%`;
        scoreCfg.textContent = `${data.control_flow_similarity.toFixed(1)}%`;
        if (barCfg) barCfg.style.width = `${data.control_flow_similarity}%`;

        scoreStmt.textContent = `${data.statement_similarity.toFixed(1)}%`;
        if (barStmt) barStmt.style.width = `${data.statement_similarity}%`;

        scoreCg.textContent = `${data.call_graph_similarity.toFixed(1)}%`;
        if (barCg) barCg.style.width = `${data.call_graph_similarity}%`;

        // Low-confidence Caveat Banner
        if (data.is_short_code && data.warning_message) {
            shortCodeBanner.classList.remove("hidden");
            shortCodeText.textContent = data.warning_message;
        } else {
            shortCodeBanner.classList.add("hidden");
        }

        // Forensic Transformation Explanations
        explanationList.innerHTML = "";
        if (data.explanations && data.explanations.length > 0) {
            data.explanations.forEach(exp => {
                const li = document.createElement("li");
                li.innerHTML = escapeHtml(exp).replace(/`([^`]+)`/g, "<code>$1</code>");
                explanationList.appendChild(li);
            });
        } else {
            explanationList.innerHTML = `<li class="table-empty" style="list-style: none;">No significant transformation detected. Programs appear independent.</li>`;
        }

        // Function-Level Breakdown Table (8 columns)
        funcBreakdownBody.innerHTML = "";
        if (data.function_matches && data.function_matches.length > 0) {
            data.function_matches.forEach(m => {
                const tr = document.createElement("tr");
                const pillClass = m.verdict === "COPIED" ? "verdict-copied" :
                                 m.verdict === "SUSPICIOUS" ? "verdict-suspicious" :
                                 m.verdict === "MODIFIED" ? "verdict-modified" : "verdict-unique";

                tr.innerHTML = `
                    <td><strong>${escapeHtml(m.function_a)}</strong></td>
                    <td><strong>${escapeHtml(m.function_b)}</strong></td>
                    <td><code>${escapeHtml(m.line_range_a)}</code></td>
                    <td><code>${escapeHtml(m.line_range_b)}</code></td>
                    <td>${m.token_similarity.toFixed(1)}%</td>
                    <td>${m.structural_similarity.toFixed(1)}%</td>
                    <td><strong>${m.overall_similarity.toFixed(1)}%</strong></td>
                    <td><span class="verdict-pill ${pillClass}">${m.verdict}</span></td>
                `;
                funcBreakdownBody.appendChild(tr);
            });
        } else {
            funcBreakdownBody.innerHTML = `<tr><td colspan="8" class="table-empty">No individual functions detected.</td></tr>`;
        }

        // Side-by-Side Highlighted Code View
        renderHighlightedView(rawA, rawB, data.matched_regions);

        // Scroll smoothly to results
        resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // ----------------------------------------------------
    // 6. Side-by-Side Synchronized Highlighting
    // ----------------------------------------------------
    function renderHighlightedView(codeAStr, codeBStr, regions) {
        if (!regions || regions.length === 0) {
            highlightPaneA.innerHTML = escapeHtml(codeAStr);
            highlightPaneB.innerHTML = escapeHtml(codeBStr);
            return;
        }

        highlightPaneA.innerHTML = buildHighlightedHtml(codeAStr, regions, "a");
        highlightPaneB.innerHTML = buildHighlightedHtml(codeBStr, regions, "b");

        attachHighlightSync();
    }

    function buildHighlightedHtml(codeStr, regions, side) {
        const spans = [];
        regions.forEach((r, idx) => {
            const start = side === "a" ? r.a_char_start : r.b_char_start;
            const end = side === "a" ? r.a_char_end : r.b_char_end;
            if (start !== undefined && end !== undefined && start < end) {
                spans.push({
                    start: Math.max(0, start),
                    end: Math.min(codeStr.length, end),
                    id: idx,
                    lineA: `L${r.a_line_start}–L${r.a_line_end}`,
                    lineB: `L${r.b_line_start}–L${r.b_line_end}`,
                    tokens: r.token_count || 0
                });
            }
        });

        spans.sort((x, y) => x.start - y.start);

        let out = "";
        let lastIdx = 0;

        for (const s of spans) {
            if (s.start < lastIdx) continue;
            out += escapeHtml(codeStr.substring(lastIdx, s.start));
            const chunk = escapeHtml(codeStr.substring(s.start, s.end));
            const tooltip = `Match #${s.id + 1}: Program A (${s.lineA}) ↔ Program B (${s.lineB}) [${s.tokens} tokens]. Click to pin.`;
            out += `<span class="match-span" data-region-id="${s.id}" title="${escapeHtml(tooltip)}">${chunk}</span>`;
            lastIdx = s.end;
        }
        out += escapeHtml(codeStr.substring(lastIdx));
        return out;
    }

    function attachHighlightSync() {
        const spansA = highlightPaneA.querySelectorAll(".match-span");
        const spansB = highlightPaneB.querySelectorAll(".match-span");
        let pinnedId = null;

        function setHoverHighlight(id, active) {
            if (pinnedId !== null) return;
            spansA.forEach(s => {
                if (s.getAttribute("data-region-id") === id) {
                    s.classList.toggle("active-highlight", active);
                    if (active) s.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
            });
            spansB.forEach(s => {
                if (s.getAttribute("data-region-id") === id) {
                    s.classList.toggle("active-highlight", active);
                    if (active) s.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
            });
        }

        [...spansA, ...spansB].forEach(span => {
            const id = span.getAttribute("data-region-id");
            span.addEventListener("mouseenter", () => setHoverHighlight(id, true));
            span.addEventListener("mouseleave", () => setHoverHighlight(id, false));

            span.addEventListener("click", () => {
                if (pinnedId === id) {
                    // Unpin
                    pinnedId = null;
                    spansA.forEach(s => s.classList.remove("pinned-highlight", "active-highlight"));
                    spansB.forEach(s => s.classList.remove("pinned-highlight", "active-highlight"));
                } else {
                    // Pin new selection
                    pinnedId = id;
                    spansA.forEach(s => {
                        const match = s.getAttribute("data-region-id") === id;
                        s.classList.toggle("pinned-highlight", match);
                        s.classList.remove("active-highlight");
                        if (match) s.scrollIntoView({ behavior: "smooth", block: "center" });
                    });
                    spansB.forEach(s => {
                        const match = s.getAttribute("data-region-id") === id;
                        s.classList.toggle("pinned-highlight", match);
                        s.classList.remove("active-highlight");
                        if (match) s.scrollIntoView({ behavior: "smooth", block: "center" });
                    });
                }
            });
        });
    }

    // ----------------------------------------------------
    // 7. Report Export (PDF / Print)
    // ----------------------------------------------------
    btnExportReport.addEventListener("click", async () => {
        const textA = codeA.value.trim();
        const textB = codeB.value.trim();
        if (!textA || !textB) return;

        try {
            const resp = await fetch("/api/report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code_a: textA,
                    code_b: textB,
                    language: langSelect.value,
                    filename_a: titleA.textContent || "program_a.c",
                    filename_b: titleB.textContent || "program_b.c",
                    author_a: "Student A",
                    author_b: "Student B"
                })
            });

            if (!resp.ok) {
                const errJson = await resp.json().catch(() => ({}));
                throw new Error(errJson.error || `Report generation failed (${resp.status})`);
            }
            const htmlContent = await resp.text();
            const reportWindow = window.open("", "_blank");
            reportWindow.document.write(htmlContent);
            reportWindow.document.close();
        } catch (err) {
            alert("Export Error: " + err.message);
        }
    });

    // ----------------------------------------------------
    // 8. Faculty Batch Dashboard & Heatmap
    // ----------------------------------------------------
    btnLoadBatch.addEventListener("click", async () => {
        try {
            btnLoadBatch.disabled = true;
            btnLoadBatch.textContent = "Loading Sample Class...";

            // Fetch benchmark fixtures as sample submissions
            const pIdentical = await (await fetch("/api/presets/pair_identical")).json();
            const pRenamed = await (await fetch("/api/presets/pair_renamed")).json();
            const pReordered = await (await fetch("/api/presets/pair_reordered")).json();
            const pUnrelated = await (await fetch("/api/presets/pair_unrelated")).json();

            const sampleSubmissions = [
                { filename: "student1_alice.c", author: "Alice Chen", content: pIdentical.code_a },
                { filename: "student2_bob_copy.c", author: "Bob Miller", content: pIdentical.code_b },
                { filename: "student3_charlie_renamed.c", author: "Charlie Davis", content: pRenamed.code_b },
                { filename: "student4_diana_reordered.c", author: "Diana Prince", content: pReordered.code_b },
                { filename: "student5_evan_matrix.c", author: "Evan Wright", content: pUnrelated.code_b }
            ];

            await runBatchAnalysis(sampleSubmissions);
        } catch (err) {
            alert("Error loading sample batch: " + err.message);
        } finally {
            btnLoadBatch.disabled = false;
            btnLoadBatch.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                Load Sample Class (5 Submissions)
            `;
        }
    });

    if (batchFileUpload) {
        batchFileUpload.addEventListener("change", async (e) => {
            const files = Array.from(e.target.files);
            if (files.length < 2) {
                alert("Please select at least 2 C/C++ files for batch comparison.");
                return;
            }

            const submissions = [];
            for (let i = 0; i < files.length; i++) {
                const f = files[i];
                const content = await f.text();
                submissions.push({
                    filename: f.name,
                    author: `Student ${i + 1} (${f.name.replace(/\.[^/.]+$/, "")})`,
                    content: content
                });
            }

            runBatchAnalysis(submissions);
        });
    }

    async function runBatchAnalysis(submissions) {
        try {
            const resp = await fetch("/api/batch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    submissions: submissions,
                    threshold: 70.0
                })
            });

            if (!resp.ok) {
                const errJson = await resp.json().catch(() => ({}));
                throw new Error(errJson.error || `Batch analysis failed (${resp.status})`);
            }
            const data = await resp.json();
            currentBatchData = { data, submissions };
            renderBatchReport(data, submissions);
        } catch (err) {
            alert("Batch Analysis Error: " + err.message);
        }
    }

    function renderBatchReport(report, submissions) {
        batchTotalSub.textContent = report.total_submissions;
        batchTotalPairs.textContent = report.total_comparisons;
        batchFlaggedCount.textContent = report.flagged_pairs_count;
        
        const highElem = document.getElementById("batch-high-risk");
        const medElem = document.getElementById("batch-med-risk");
        const lowElem = document.getElementById("batch-low-risk");
        const maxElem = document.getElementById("batch-max-sim");
        const avgElem = document.getElementById("batch-avg-sim");

        if (highElem) highElem.textContent = report.high_risk_count !== undefined ? report.high_risk_count : report.flagged_pairs.length;
        if (medElem) medElem.textContent = report.medium_risk_count !== undefined ? report.medium_risk_count : 0;
        if (lowElem) lowElem.textContent = report.low_risk_count !== undefined ? report.low_risk_count : 0;
        if (maxElem) maxElem.textContent = `${(report.highest_similarity !== undefined ? report.highest_similarity : 0).toFixed(1)}%`;
        if (avgElem) avgElem.textContent = `${(report.average_similarity !== undefined ? report.average_similarity : 0).toFixed(1)}%`;

        // Render Matrix Heatmap
        const matrix = report.pairwise_matrix;
        const subList = report.submissions;
        const n = subList.length;

        let tableHtml = `<table class="heatmap-table"><thead><tr><th>Student</th>`;
        subList.forEach((s, idx) => {
            tableHtml += `<th title="${escapeHtml(s.author)}">S${idx + 1}</th>`;
        });
        tableHtml += `</tr></thead><tbody>`;

        for (let i = 0; i < n; i++) {
            tableHtml += `<tr><th>S${i + 1} (${escapeHtml(subList[i].author.split(" ")[0])})</th>`;
            for (let j = 0; j < n; j++) {
                const score = matrix[i][j];
                let cellClass = "cell-diag";

                if (i !== j) {
                    if (score >= 70.0) {
                        cellClass = "cell-high";
                    } else if (score >= 40.0) {
                        cellClass = "cell-med";
                    } else {
                        cellClass = "cell-low";
                    }
                }

                tableHtml += `
                    <td class="heatmap-cell ${cellClass}" data-idx-a="${i}" data-idx-b="${j}"
                        title="${escapeHtml(subList[i].author)} vs ${escapeHtml(subList[j].author)}: ${score.toFixed(1)}%">
                        ${score.toFixed(0)}%
                    </td>
                `;
            }
            tableHtml += `</tr>`;
        }
        tableHtml += `</tbody></table>`;
        heatmapContainer.innerHTML = tableHtml;

        // Attach click listeners to heatmap cells
        heatmapContainer.querySelectorAll(".heatmap-cell").forEach(cell => {
            cell.addEventListener("click", () => {
                const idxA = parseInt(cell.getAttribute("data-idx-a"));
                const idxB = parseInt(cell.getAttribute("data-idx-b"));
                if (idxA === idxB) return;
                loadPairInInspector(submissions[idxA], submissions[idxB]);
            });
        });

        // Render Flagged Pairs Table
        flaggedPairsBody.innerHTML = "";
        if (report.flagged_pairs.length > 0) {
            report.flagged_pairs.forEach(pair => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${escapeHtml(pair.author_a)}</strong> &amp; <strong>${escapeHtml(pair.author_b)}</strong></td>
                    <td><strong style="color: var(--risk-high);">${pair.overall_similarity.toFixed(1)}%</strong></td>
                    <td><span class="risk-badge badge-high">${pair.risk_level}</span></td>
                    <td>
                        <button class="ide-action-btn btn-inspect-pair" data-file-a="${escapeHtml(pair.file_a)}" data-file-b="${escapeHtml(pair.file_b)}">
                            Inspect Pair →
                        </button>
                    </td>
                `;
                flaggedPairsBody.appendChild(tr);
            });

            flaggedPairsBody.querySelectorAll(".btn-inspect-pair").forEach(btn => {
                btn.addEventListener("click", () => {
                    const fa = btn.getAttribute("data-file-a");
                    const fb = btn.getAttribute("data-file-b");
                    const subA = submissions.find(s => s.filename === fa);
                    const subB = submissions.find(s => s.filename === fb);
                    if (subA && subB) loadPairInInspector(subA, subB);
                });
            });
        } else {
            flaggedPairsBody.innerHTML = `<tr><td colspan="4" class="table-empty">No high-risk collusion pairs detected (&gt;70%).</td></tr>`;
        }
    }

    function loadPairInInspector(subA, subB) {
        codeA.value = subA.content;
        codeB.value = subB.content;
        titleA.textContent = subA.filename;
        titleB.textContent = subB.filename;
        updateEditorMeta(codeA, linesA, metaA);
        updateEditorMeta(codeB, linesB, metaB);
        switchTab("pair");
        runComparison();
    }

    // Helper: HTML entity escaping
    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
