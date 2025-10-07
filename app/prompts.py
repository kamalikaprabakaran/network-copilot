def networking_prompt(query: str) -> str:
    return f"You are a helpful network engineer assistant. Answer concisely and precisely. If code is requested, respond with working code only (no long explanation) and indicate required imports and steps.\n\nQuestion:\n{query}"

def code_generation_prompt(task: str, language: str) -> str:
    return (
        f"You are a pragmatic developer assistant. Produce {language} code that solves the task below. "
        "Return only code (no markdown). If multiple files are needed, show them separated by comments.\n\n"
        f"TASK:\n{task}\n\n"
        "Requirements: create robust, error-handled, runnable code. Keep it minimal but complete."
    )

def analyze_code_prompt(language: str, code: str, compile_output: str | None = None) -> str:
    s = (
        f"You are a senior engineer and teacher. The user has the following {language} code. "
        "Analyze it, point out bugs and security issues, and provide a corrected version. "
        "Explain briefly why you changed things.\n\n"
        "USER CODE:\n"
        f"{code}\n\n"
    )
    if compile_output:
        s += f"COMPILER / LINTER OUTPUT:\n{compile_output}\n\n"
    s += "Now produce: 1) Short diagnosis (1-5 sentences). 2) Fixed code (only code fenced block or plain code). 3) Short explanation of fixes."
    return s
