# CodeGuard
Source Code Similarity and Plagiarism Detection Tool

## 🚀 Live Demo

**Try CodeGuard online:** [Launch CodeGuard](https://codeguard-xhzy.onrender.com)

CodeGuard is a compiler-based source code similarity and plagiarism detection tool designed to analyze C/C++ programs using lexical analysis, token winnowing, and AST-based structural comparison.

> **Note:** The live demo is hosted on Render's free tier, so the first request after inactivity may take a little longer to load.

## ✨ Features

- **Source Code Similarity Analysis** — Compare two C/C++ programs and calculate similarity scores.
- **Token Winnowing** — Detect similarities using normalized token sequences.
- **AST-Based Structural Analysis** — Examine structural similarities between programs.
- **Function-Level Comparison** — Identify matching functions and compare their similarity.
- **Batch Analysis** — Analyze multiple submissions and generate pairwise similarity results.
- **Risk Classification** — Categorize detected similarity into risk levels.
- **HTML Report Generation** — Generate detailed reports for source code comparisons.
- **Interactive Web Interface** — Access CodeGuard through a browser without installing a desktop application.
- **Automated Tests and Benchmarks** — Validate core functionality using test cases and benchmark fixtures.

## 🛠️ Tech Stack

- **Language:** Python
- **Frontend:** HTML, CSS, JavaScript
- **Server:** Python built-in HTTP server
- **Analysis Techniques:** Lexical analysis, token winnowing, AST-based analysis
- **Testing:** Python `unittest`
- **Deployment:** Render
- **Version Control:** Git and GitHub

## 💻 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/MahaNagendran2007/CodeGuard.git
cd CodeGuard
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Start the web server

```bash
python run.py --server
```

Open **http://localhost:8080/** in your browser.

### 4. Run automated tests

```bash
python run.py --test
```

### 5. Run benchmarks

```bash
python run.py --benchmarks
```

## 📂 Project Structure

```text
CodeGuard/
├── codeguard/
│   ├── core/
│   │   ├── ast_analyzer.py
│   │   ├── batch.py
│   │   ├── engine.py
│   │   ├── function_analyzer.py
│   │   ├── lexer.py
│   │   ├── normalizer.py
│   │   ├── report_generator.py
│   │   └── winnowing.py
│   └── web/
│       ├── server.py
│       └── static/
│           ├── app.js
│           ├── index.html
│           └── styles.css
├── tests/
│   ├── fixtures/
│   ├── smoke_test.py
│   ├── test_phase1.py
│   └── test_phase2.py
├── requirements.txt
├── run.py
├── run_tests.bat
├── run_benchmarks.bat
└── start_server.bat
```

## 🎯 Project Objective

The objective of CodeGuard is to explore compiler-based techniques for detecting source code similarities beyond simple textual matching. By combining token-based comparison with structural analysis, the system aims to identify similarities that may remain even when variable names or code organization have been changed.

## 🔮 Future Enhancements

- Expand language support beyond C/C++.
- Improve analysis of advanced structural transformations.
- Add downloadable comparison reports and richer visualizations.
- Strengthen API security and production deployment capabilities.
- Expand the benchmark dataset and automated test coverage.

## 👩‍💻 Author

**Maha Vignesh Shree Nagendran**

- GitHub: [@MahaNagendran2007](https://github.com/MahaNagendran2007)
- Project Repository: [CodeGuard](https://github.com/MahaNagendran2007/CodeGuard)
- Live Demo: [CodeGuard on Render](https://codeguard-xhzy.onrender.com)

## Screenshots
<img width="2870" height="1352" alt="Screenshot 2026-10-21 121623" src="https://github.com/user-attachments/assets/b4edaf7e-e852-49d1-87e9-731e5b630c3c" />
<img width="2848" height="1496" alt="Screenshot 2026-10-21 121638" src="https://github.com/user-attachments/assets/7f8dc0a6-d3b9-41a0-ab40-3d05ad23e2e5" />
<img width="2844" height="1532" alt="Screenshot 2026-10-21 121701" src="https://github.com/user-attachments/assets/199050f8-3b5b-4229-9e40-5d07339d133f" />
<img width="2876" height="1544" alt="Screenshot 2026-10-21 121737" src="https://github.com/user-attachments/assets/017e7a5e-8776-4df7-9f2e-5e85c00e374d" />


