from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.adapters.ollama_adapter import OllamaAdapter
from app.prompts import networking_prompt, code_generation_prompt
from app.utils import run_code, analyze_code

app = FastAPI(title="Network Copilot API")

# -----------------------------
# Adapter
# -----------------------------
def get_adapter():
    return OllamaAdapter()

# -----------------------------
# Request Schemas
# -----------------------------
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class AskRequest(BaseModel):
    query: str
    model: Optional[str] = "llama3"
    messages: Optional[List[Message]] = None

class CodeGenRequest(BaseModel):
    task: str
    language: str = "java"
    model: Optional[str] = None

class AnalyzeRequest(BaseModel):
    language: str
    code: str
    model: str = "llama3"  # default

class CodeRequest(BaseModel):
    language: str
    code: str
    model: str = "llama3"  # default

# -----------------------------
# Endpoints
# -----------------------------
@app.post("/run_code")
async def run_code_endpoint(req: CodeRequest):
    return run_code(req.language, req.code)

@app.post("/analyze_code")
async def analyze_code_endpoint(req: AnalyzeRequest):
    return analyze_code(req.language, req.code, req.model)

@app.post("/ask")
def ask(req: AskRequest):
    adapter = get_adapter()

    # Handle both chat-style input and single query
    if req.messages and len(req.messages) > 0:
        # Combine the conversation context properly
        conversation_context = "\n".join(
            [f"{msg.role.capitalize()}: {msg.content}" for msg in req.messages]
        )
        prompt = f"{conversation_context}\nUser: {req.query}\nAssistant:"
    else:
        # Default to networking question mode
        prompt = networking_prompt(req.query)

    try:
        resp = adapter.generate(prompt, model=req.model, max_tokens=700)
    except Exception as e:
        resp = f"[Error generating response] {str(e)}"

    return {
        "answer": resp,
        "model_used": req.model or "default",
        "mode": "chat" if req.messages else "ask"
    }

@app.post("/generate_code")
def generate_code(req: CodeGenRequest):
    adapter = get_adapter()
    prompt = code_generation_prompt(req.task, req.language)
    raw_code = adapter.generate(prompt, model=req.model, max_tokens=1200)

    formatted_code = [line for line in raw_code.splitlines() if line.strip() != ""]

    return {
        "language": req.language,
        "model_used": req.model or "default",
        "generated_code": formatted_code
    }

@app.get("/")
def root():
    return {"message": "🚀 Network Copilot API (Ollama) is running. Visit /docs for the endpoints."}
