@echo off
title CodeGuard Web Server
echo ============================================================
echo   CodeGuard C/C++ Plagiarism Detection System
echo   Starting local server...
echo   Open in your browser:
echo     -> http://localhost:8080/
echo     -> http://127.0.0.1:8080/
echo ============================================================
python run.py --server || py run.py --server
pause
