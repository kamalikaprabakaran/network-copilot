# app/utils.py
import os
import tempfile
import subprocess
import uuid
import re
from typing import Dict, Any, List

# -----------------------------
# Code File Management
# -----------------------------
def save_code_to_tempfile(code: str, language: str, filename_hint: str | None = None) -> str:
    """
    Save code to a temporary file and return its full path.
    
    Java:
        - If a public class exists, name file after the class.
        - Otherwise, use filename_hint or default 'Main.java'.
    
    Python:
        - Use filename_hint or default 'script.py'.
    
    Other:
        - Save as generic text file 'code.txt' or filename_hint.
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
    elif language.lower().startswith("py"):
        fname = filename_hint if filename_hint and filename_hint.endswith(".py") else "script.py"
    else:
        fname = filename_hint or "code.txt"
    
    path = os.path.join(tmpdir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# -----------------------------
# Compilation & Syntax Check
# -----------------------------
def compile_java(java_path: str) -> Dict[str, Any]:
    """
    Compile Java code using javac.
    
    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str
        }
    """
    try:
        proc = subprocess.run(["javac", java_path], capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "javac not found on PATH. Install JDK."}
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

# -----------------------------
# Run Code
# -----------------------------
def run_code(language: str, code: str) -> Dict[str, Any]:
    """
    Run/compile code depending on the language and return structured output:
    
    Returns:
        {
            "compile_output": str,
            "run_output": str,
            "exit_code": int
        }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        if language.lower() == "java":
            file_path = os.path.join(tmpdir, "Main.java")
            with open(file_path, "w") as f:
                f.write(code)

            # Compile Java
            compile_proc = subprocess.run(["javac", file_path], capture_output=True, text=True)
            if compile_proc.returncode != 0:
                return {"compile_output": compile_proc.stderr, "run_output": "", "exit_code": compile_proc.returncode}

            # Run Java
            run_proc = subprocess.run(["java", "-cp", tmpdir, "Main"], capture_output=True, text=True)
            return {"compile_output": compile_proc.stdout + compile_proc.stderr,
                    "run_output": run_proc.stdout + run_proc.stderr,
                    "exit_code": run_proc.returncode}

        elif language.lower().startswith("py"):
            file_path = os.path.join(tmpdir, "script.py")
            with open(file_path, "w") as f:
                f.write(code)

            run_proc = subprocess.run(["python", file_path], capture_output=True, text=True)
            return {"compile_output": "", "run_output": run_proc.stdout + run_proc.stderr, "exit_code": run_proc.returncode}

        else:
            return {"compile_output": "", "run_output": f"Language {language} not supported.", "exit_code": -1}

# -----------------------------
# Parse LLM Analysis Response
# -----------------------------
def parse_analysis_response(text: str) -> Dict[str, Any]:
    """
    Converts raw LLM text analysis into structured JSON.
    
    Expected LLM sections:
        - **What it does:**
        - **Security issues:**
        - **Suggestions for improvement:**
    
    Returns:
        {
            "what_it_does": str,
            "security_issues": List[str],
            "suggestions": List[str]
        }
    """
    sections = {"what_it_does": "", "security_issues": [], "suggestions": []}
    current_section = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Detect section headers
        if "**What it does:**" in line:
            current_section = "what_it_does"
            continue
        elif "**Security issues:**" in line:
            current_section = "security_issues"
            continue
        elif "**Improvement suggestions:**" in line or "**Suggestions for improvement:**" in line:
            current_section = "suggestions"
            continue

        # Append content to appropriate section
        if current_section == "what_it_does":
            sections["what_it_does"] += line + " "
        elif current_section == "security_issues":
            if line.startswith(("*", "-")):
                sections["security_issues"].append(line[1:].strip())
            else:
                sections["security_issues"].append(line)
        elif current_section == "suggestions":
            if line.startswith(("*", "-", "1.", "2.", "3.")):
                sections["suggestions"].append(line.lstrip("*-1234567890. ").strip())
            else:
                sections["suggestions"].append(line)

    sections["what_it_does"] = sections["what_it_does"].strip()
    return sections

# -----------------------------
# Analyze Code (LLM + Run)
# -----------------------------
from app.adapters.ollama_adapter import query_model

def analyze_code(language: str, code: str, model: str = "llama3"):
    """
    Analyze code using the LLM and also run/compile it.
    Returns structured JSON with analysis, compile output, run output, and exit code.
    """
    prompt = f"""
You are a code analyzer. Analyze the following {language} code:
- Explain what it does.
- Point out any security issues (e.g., unsafe input, DoS risk).
- Suggest improvements.
Code:
{code}
    """

    try:
        llm_response = query_model(model, prompt)  # could return dict or string

        # 🧠 Handle both dict and string responses safely
        if isinstance(llm_response, dict):
            # try extracting the text part
            llm_response_text = llm_response.get("response") or llm_response.get("text") or str(llm_response)
        else:
            llm_response_text = str(llm_response)

    except Exception as e:
        llm_response_text = f"[Error generating analysis] {str(e)}"

    # Parse structured analysis
    structured_analysis = parse_analysis_response(llm_response_text)

    # Compile or run the code
    run_result = run_code(language, code)

    return {
        "analysis": structured_analysis,
        "compile_output": run_result.get("compile_output", ""),
        "run_output": run_result.get("run_output", ""),
        "exit_code": run_result.get("exit_code", 0)
    }
