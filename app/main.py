from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents.evaluator import EvaluatorAgent
from app.agents.knowledge import KnowledgeAgent
from app.agents.orchestrator import Orchestrator
from app.agents.router import RouterAgent
from app.agents.support import SupportAgent
from app.config import get_settings
from app.models import ChatRequest, ChatResponse, EvalCase, EvaluationResult
from app.services.llm import LLMClient
from app.services.rag import KnowledgeBase
from app.services.support_tools import CustomerRepository

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "app" / "data"
STATIC = ROOT / "static"


def create_dependencies():
    settings = get_settings()
    llm = LLMClient(settings)
    kb = KnowledgeBase(DATA / "knowledge.json")
    customers = CustomerRepository(DATA / "customers.json")
    orchestrator = Orchestrator(RouterAgent(llm), KnowledgeAgent(llm, kb), SupportAgent(llm, customers))
    return settings, llm, orchestrator, EvaluatorAgent(llm)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings, app.state.llm, app.state.orchestrator, app.state.evaluator = create_dependencies()
    yield


app = FastAPI(title="Getnet Agent Ops API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"] , allow_methods=["*"] , allow_headers=["*"])
app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/", include_in_schema=False)
async def console():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "llm": "connected" if app.state.llm.available else "demo-fallback", "model": app.state.settings.openrouter_model, "agents": 5}


@app.post("/chat", response_model=ChatResponse, tags=["orchestration"])
@app.post("/api/chat", response_model=ChatResponse, include_in_schema=False)
async def chat(request: ChatRequest):
    return await app.state.orchestrator.handle(request.message, request.user_id)


@app.post("/evaluations", response_model=EvaluationResult, tags=["evaluation"])
@app.post("/api/evaluations", response_model=EvaluationResult, include_in_schema=False)
async def evaluate(case: EvalCase):
    actual, trace_id = case.actual_answer, None
    if actual is None:
        response = await app.state.orchestrator.handle(case.question, case.user_id)
        actual, trace_id = response.answer, response.trace_id
    return await app.state.evaluator.evaluate(case.question, case.expected_answer, actual, trace_id)


@app.get("/metrics", tags=["observability"])
@app.get("/api/metrics", include_in_schema=False)
async def metrics():
    return app.state.orchestrator.metrics()


@app.get("/api/demo-cases", include_in_schema=False)
async def demo_cases():
    return [
        {"label": "Comparar máquinas", "message": "Qual é a diferença entre a Get Clássica e a Get Smart?", "user_id": "cliente1988"},
        {"label": "Consultar recebível", "message": "Quando o dinheiro das vendas de ontem será depositado?", "user_id": "cliente1988"},
        {"label": "Diagnosticar terminal", "message": "Minha maquininha não conecta à internet. O que faço?", "user_id": "cliente_demo2"},
        {"label": "Cotação em tempo real", "message": "Qual é a cotação do euro hoje?", "user_id": "cliente1988"},
        {"label": "Handoff humano", "message": "Quero falar com um atendente para cancelar o contrato", "user_id": "cliente1988"},
    ]

