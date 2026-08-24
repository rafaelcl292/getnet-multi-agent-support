import re

from app.services.llm import LLMClient


ROUTES = {"knowledge", "support", "external", "escalation"}


class RouterAgent:
    SUPPORT = ("minha", "meu", "ontem", "depósito", "depositado", "receber", "máquina", "maquininha", "erro", "recusada", "conecta", "internet", "pix habilitado", "chamado")
    KNOWLEDGE = ("get smart", "get clássica", "get classica", "getnet", "link de pagamento", "crediário", "crediario", "antecipação", "antecipacao", "pix")
    EXTERNAL = ("tempo", "clima", "previsão", "euro", "dólar", "dolar", "câmbio", "cambio")
    ESCALATION = ("humano", "atendente", "reclamação", "reclamacao", "cancelar contrato", "fraude")

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def route(self, message: str) -> tuple[str, float, str]:
        lower = message.lower()
        if any(term in lower for term in self.ESCALATION):
            return "escalation", 0.96, "Solicitação sensível ou explícita de atendimento humano"
        if any(term in lower for term in self.EXTERNAL):
            return "external", 0.94, "Pergunta geral que requer dados públicos atuais"
        support_score = sum(term in lower for term in self.SUPPORT)
        knowledge_score = sum(term in lower for term in self.KNOWLEDGE)
        if support_score or knowledge_score:
            route = "support" if support_score >= knowledge_score else "knowledge"
            return route, min(0.97, 0.77 + max(support_score, knowledge_score) * 0.05), "Classificação por intenção e necessidade de dados do cliente"
        try:
            data = await self.llm.json(
                "Você é o Router Agent da Getnet. Responda JSON com route (knowledge, support, external ou escalation), confidence de 0 a 1 e reason curta. Support usa dados privados; knowledge usa documentação Getnet; external usa dados públicos; escalation quando precisa humano.",
                message,
            )
            route = data.get("route", "escalation")
            return (route if route in ROUTES else "escalation"), float(data.get("confidence", 0.6)), data.get("reason", "Classificação semântica")
        except Exception:
            return "escalation", 0.45, "Intenção incerta; fallback seguro"


def contains_sensitive_data(message: str) -> bool:
    digits = re.sub(r"\D", "", message)
    return len(digits) >= 11 or bool(re.search(r"senha|password|cvv", message, re.I))

