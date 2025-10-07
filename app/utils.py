# app/utils.py
import os
import tempfile
import subprocess
import uuid
import re
from typing import Dict, Any

def save_code_to_tempfile(code: str, language: str, filename_hint: str | None = None) -> str:
    """
    Save code to a temp file and return full path.
    For Java, tries to infer public class name to name the file.
    """
    tmpdir = tempfile.mkdtemp(prefix="netcop_")
    if language.lower() == "java":
        m = re.search(r'public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)', code)
        if m:
            fname = f"{m.group(1)}.java"
        elif filename_hint:
            fname = filename_hint if filename_hint.endswith(".java") else filename_hint + ".java"
        else:
            fname = "Main.java"
    elif language.lower() == "python" or language.lower().startswith("py"):
        fname = filename_hint if filename_hint and filename_hint.endswith(".py") else "script.py"
    else:
        # generic text file
        fname = filename_hint or "code.txt"
    path = os.path.join(tmpdir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

def compile_java(java_path: str) -> Dict[str, Any]:
    """
    Attempt to compile Java code. Returns dict with success, stdout, stderr.
    Requires javac on PATH.
    """
    try:
        proc = subprocess.run(["javac", java_path], capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "javac not found on PATH. Install JDK and ensure javac is available."}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "javac timed out."}
    return {"success": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}

def python_syntax_check(py_path: str) -> Dict[str, Any]:
    """
    Quick syntax check using python -m py_compile.
    """
    try:
        proc = subprocess.run(["python", "-m", "py_compile", py_path], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "py_compile timed out."}
    return {"success": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}

def run_code(language: str, code: str):
    """
    Compiles and/or runs code depending on the language.
    Returns stdout/stderr and exit code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        if language.lower() == "java":
            file_path = os.path.join(tmpdir, "Main.java")
            with open(file_path, "w") as f:
                f.write(code)

            # Compile
            compile_proc = subprocess.run(
                ["javac", file_path],
                capture_output=True, text=True
            )

            if compile_proc.returncode != 0:
                return {
                    "compile_output": compile_proc.stderr,
                    "run_output": "",
                    "exit_code": compile_proc.returncode
                }

            # Run
            run_proc = subprocess.run(
                ["java", "-cp", tmpdir, "Main"],
                capture_output=True, text=True
            )
            return {
                "compile_output": compile_proc.stdout + compile_proc.stderr,
                "run_output": run_proc.stdout + run_proc.stderr,
                "exit_code": run_proc.returncode
            }

        elif language.lower() == "python":
            file_path = os.path.join(tmpdir, "script.py")
            with open(file_path, "w") as f:
                f.write(code)

            run_proc = subprocess.run(
                ["python", file_path],
                capture_output=True, text=True
            )
            return {
                "compile_output": "",
                "run_output": run_proc.stdout + run_proc.stderr,
                "exit_code": run_proc.returncode
            }

        else:
            return {
                "compile_output": "",
                "run_output": f"Language {language} not supported.",
                "exit_code": -1
            }


def analyze_code(language: str, code: str, model: str):
    """
    Calls your LLM model to analyze the code AND also compiles/runs it.
    """
    from app.adapters.ollama_adapter import query_model  # reuse adapter

    # Ask LLM for analysis/security insights
    prompt = f"""
    You are a code analyzer. Analyze the following {language} code:
    - Explain what it does.
    - Point out any security issues (e.g., unsafe input, DoS risk).
    - Suggest improvements.
    Code:
    {code}
    """

    llm_response = query_model(model, prompt)

    # Also run/compile code
    run_result = run_code(language, code)

    return {
        "analysis": llm_response,
        "compile_output": run_result.get("compile_output", ""),
        "run_output": run_result.get("run_output", ""),
        "exit_code": run_result.get("exit_code", 0)
    }