from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
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
class AskRequest(BaseModel):
    query: str
    model: Optional[str] = None

class CodeGenRequest(BaseModel):
    task: str
    language: str = "java"
    model: Optional[str] = None

class AnalyzeRequest(BaseModel):
    language: str
    code: str
    model: str = "llama3"  # default

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None

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

@app.post("/chat")
def chat(req: ChatRequest):
    adapter = get_adapter()
    if req.message.lower().startswith("generate code"):
        prompt = code_generation_prompt(req.message, "python")
        resp = adapter.generate(prompt, model=req.model, max_tokens=1000)
        return {"type": "code", "response": resp}
    else:
        prompt = networking_prompt(req.message)
        resp = adapter.generate(prompt, model=req.model, max_tokens=700)
        return {"type": "text", "response": resp}

@app.post("/ask")
def ask(req: AskRequest):
    adapter = get_adapter()
    prompt = networking_prompt(req.query)
    resp = adapter.generate(prompt, model=req.model, max_tokens=700)
    return {"answer": resp}

@app.post("/generate_code")
def generate_code(req: CodeGenRequest):
    adapter = get_adapter()
    prompt = code_generation_prompt(req.task, req.language)
    resp = adapter.generate(prompt, model=req.model, max_tokens=1200)
    return {"code": resp}

@app.get("/")
def root():
    return {"message": "Network Copilot API (Ollama) is running. Use /docs to see endpoints."}

@app.get("/ping")
def ping():
    return {"message": "pong"}
