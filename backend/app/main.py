from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RAG Knowledge Base API")

class ChatRequest(BaseModel):
    query: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    return {"answer": "Mock answer"}