def test_health_reports_agents(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["agents"] == 5
    assert response.json()["llm"] == "demo-fallback"


def test_required_chat_contract_and_knowledge_route(client):
    response = client.post("/chat", json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "cliente1988"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "knowledge"
    assert "4G" in body["answer"]
    assert body["citations"]
    assert [step["agent"] for step in body["trace"]] == ["Router Agent", "Knowledge Agent", "Response Guardrail"]


def test_support_agent_uses_customer_tools(client):
    response = client.post("/chat", json={"message": "Quando recebo as vendas de ontem?", "user_id": "cliente1988"})
    body = response.json()
    assert body["route"] == "support"
    assert "agendado" in body["answer"]
    assert "get_receivables" in body["trace"][1]["details"]["tools"]
    assert body["trace"][1]["details"]["generation"] == "deterministic-fallback"
    assert "R$ 1.840,50" in body["answer"]


def test_unknown_customer_fails_safely(client):
    response = client.post("/chat", json={"message": "Minha maquininha está com erro", "user_id": "missing"})
    assert response.status_code == 200
    assert response.json()["confidence"] < 0.5
    assert "Não localizei" in response.json()["answer"]


def test_guardrail_blocks_sensitive_payload(client):
    response = client.post("/chat", json={"message": "Meu CPF é 123.456.789-00 e a senha é 1234", "user_id": "cliente1988"})
    body = response.json()
    assert body["route"] == "guardrail"
    assert "não envie" in body["answer"]


def test_handoff_route(client):
    response = client.post("/chat", json={"message": "Quero falar com atendente humano", "user_id": "cliente1988"})
    assert response.json()["handoff"] is True
    assert response.json()["route"] == "escalation"


def test_evaluation_with_supplied_answer(client):
    response = client.post("/evaluations", json={
        "question": "Posso vender pelo WhatsApp?",
        "expected_answer": "Sim, use o Link de Pagamento no WhatsApp.",
        "actual_answer": "Sim. Compartilhe o Link de Pagamento pelo WhatsApp."
    })
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["score"] >= 0.75


def test_evaluation_can_generate_actual_answer(client):
    response = client.post("/evaluations", json={
        "question": "Posso vender pelo WhatsApp usando Link de Pagamento?",
        "expected_answer": "Sim. O Link de Pagamento pode ser enviado pelo WhatsApp.",
        "user_id": "cliente1988"
    })
    assert response.status_code == 200
    assert response.json()["actual_answer"]
    assert response.json()["trace_id"]
