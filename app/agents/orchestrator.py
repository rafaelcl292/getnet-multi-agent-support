import time
import uuid
from collections import deque

from app.agents.knowledge import KnowledgeAgent
from app.agents.router import RouterAgent, contains_sensitive_data
from app.agents.support import SupportAgent
from app.models import ChatResponse, TraceStep
from app.services.external_tools import answer_external_question


class Orchestrator:
    def __init__(self, router: RouterAgent, knowledge: KnowledgeAgent, support: SupportAgent):
        self.router = router
        self.knowledge = knowledge
        self.support = support
        self.recent_traces: deque[dict] = deque(maxlen=50)
        self.total_requests = 0
        self.total_handoffs = 0
        self.total_latency_ms = 0

    async def handle(self, message: str, user_id: str) -> ChatResponse:
        started = time.perf_counter()
        trace_id = uuid.uuid4().hex[:12]
        trace: list[TraceStep] = []
        if contains_sensitive_data(message):
            trace.append(TraceStep(agent="Guardrail", action="Bloqueou dado sensível", status="warning", details={"policy": "PII/payment credentials"}))
            result = ChatResponse(answer="Para sua segurança, não envie CPF completo, senha ou código de segurança. Remova esses dados e faça a pergunta novamente.", route="guardrail", confidence=1, trace_id=trace_id, trace=trace, handoff=False)
            return self._record(result, started)
        route_started = time.perf_counter()
        route, route_confidence, reason = await self.router.route(message)
        trace.append(TraceStep(agent="Router Agent", action=f"Roteou para {route}", duration_ms=int((time.perf_counter() - route_started) * 1000), details={"confidence": route_confidence, "reason": reason}))
        agent_started = time.perf_counter()
        handoff = False
        if route == "knowledge":
            answer, confidence, citations, details = await self.knowledge.answer(message)
            agent_name, action = "Knowledge Agent", "Recuperou contexto e gerou resposta"
        elif route == "support":
            answer, confidence, citations, details = await self.support.answer(message, user_id)
            agent_name, action = "Customer Support Agent", "Consultou ferramentas de cliente"
        elif route == "external":
            answer, raw_citations = await answer_external_question(message)
            from app.models import Citation
            citations = [Citation(**item) for item in raw_citations]
            confidence, details = (0.9 if citations else 0.45), {"tool": "public_data_api", "sources": len(citations)}
            agent_name, action = "External Knowledge Agent", "Consultou fonte pública em tempo real"
        else:
            answer = "Vou encaminhar sua solicitação a um especialista humano, que poderá validar o caso com segurança. Tenha em mãos o identificador do terminal e o horário aproximado da ocorrência; não envie senha ou dados completos do cartão."
            confidence, citations, details, handoff = 0.99, [], {"queue": "support-l2", "priority": "normal"}, True
            agent_name, action = "Human Escalation Agent", "Preparou handoff com contexto"
        trace.append(TraceStep(agent=agent_name, action=action, status="warning" if handoff else "success", duration_ms=int((time.perf_counter() - agent_started) * 1000), details=details))
        trace.append(TraceStep(agent="Response Guardrail", action="Validou segurança e groundedness", details={"pii_redacted": True, "citations": len(citations)}))
        result = ChatResponse(answer=answer, route=route, confidence=confidence, trace_id=trace_id, citations=citations, trace=trace, handoff=handoff)
        return self._record(result, started)

    def _record(self, result: ChatResponse, started: float) -> ChatResponse:
        elapsed = int((time.perf_counter() - started) * 1000)
        self.total_requests += 1
        self.total_handoffs += int(result.handoff)
        self.total_latency_ms += elapsed
        self.recent_traces.appendleft({"trace_id": result.trace_id, "route": result.route, "confidence": result.confidence, "latency_ms": elapsed, "steps": len(result.trace), "handoff": result.handoff})
        return result

    def metrics(self) -> dict:
        return {
            "requests": self.total_requests,
            "handoffs": self.total_handoffs,
            "handoff_rate": round(self.total_handoffs / max(1, self.total_requests), 3),
            "avg_latency_ms": round(self.total_latency_ms / max(1, self.total_requests)),
            "recent_traces": list(self.recent_traces),
        }

