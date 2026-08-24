from app.models import Citation
from app.services.llm import LLMClient
from app.services.support_tools import CustomerRepository, brl


class SupportAgent:
    def __init__(self, llm: LLMClient, customers: CustomerRepository):
        self.llm = llm
        self.customers = customers

    async def answer(self, question: str, user_id: str) -> tuple[str, float, list[Citation], dict]:
        profile = self.customers.get_customer_profile(user_id)
        if not profile:
            return "Não localizei esse usuário. Confira o identificador ou peça atendimento humano para validar o cadastro com segurança.", 0.3, [], {"tools": ["get_customer_profile"], "customer_found": False}
        lower = question.lower()
        tools = ["get_customer_profile"]
        if any(term in lower for term in ("receber", "depósito", "depositado", "ontem", "agenda")):
            receivables = self.customers.get_receivables(user_id)
            tools.append("get_receivables")
            if receivables:
                item = receivables[0]
                answer = f"Encontrei a venda de ontem na sua agenda: valor bruto de R$ {brl(item['gross_amount'])}, líquido previsto de R$ {brl(item['net_amount'])}, com depósito no {item['expected_date']}. O status está como agendado."
            else:
                answer = "Não encontrei recebíveis agendados nesse cadastro. Como a agenda pode levar alguns minutos para atualizar, confira novamente no app; se a venda continuar ausente, encaminho para análise."
            return answer, 0.95, [], {"tools": tools, "records": len(receivables)}
        if any(term in lower for term in ("internet", "conecta", "conexão", "erro", "recusada", "máquina", "maquininha")):
            diagnosis = self.customers.diagnose_terminal(user_id, question)
            tools.append("diagnose_terminal")
            terminal = diagnosis["terminal"]
            answer = f"A {terminal['model']} {terminal['id']} aparece {terminal['status']} via {terminal['connection']}. Faça este teste: 1) verifique o sinal e a energia; 2) alterne entre Wi-Fi e chip; 3) reinicie e tente uma venda de baixo valor."
            if "recus" in lower:
                answer += " Se a recusa continuar, anote a mensagem e oriente o portador a consultar o banco emissor; não repita a mesma cobrança várias vezes."
            if diagnosis.get("existing_ticket"):
                answer += f" Já existe o chamado {diagnosis['existing_ticket']['id']} {diagnosis['existing_ticket']['status']}."
            return answer, 0.91, [Citation(title="Ajuda Getnet", url="https://site.getnet.com.br/get-ajuda/", excerpt="Orientações de suporte e conectividade")], {"tools": tools, "terminal_status": terminal["status"]}
        if "pix" in lower:
            tools.append("get_customer_profile")
            status = "já está habilitado" if profile["pix_enabled"] else "ainda não está habilitado"
            return f"No seu cadastro, o Pix {status}. Você recebe pela {profile['plan']}. Se quiser alterar a configuração, faça isso no Aplicativo Getnet Brasil ou peça ajuda ao atendimento.", 0.94, [], {"tools": list(dict.fromkeys(tools)), "pix_enabled": profile["pix_enabled"]}
        safe_profile = {"name": profile["name"], "plan": profile["plan"], "terminal": profile["terminal"], "pix_enabled": profile["pix_enabled"], "auto_advance": profile["auto_advance"]}
        try:
            answer = await self.llm.complete("Você é o Customer Support Agent da Getnet. Use os dados fornecidos, jamais invente. Não revele documentos completos. Responda em português brasileiro com uma ação clara.", f"DADOS SEGUROS: {safe_profile}\nPERGUNTA: {question}")
        except Exception:
            answer = f"Olá, {profile['name'].split()[0]}. Seu plano é {profile['plan']} e seu terminal está {profile['terminal']['status']}. Conte qual operação você quer consultar para eu verificar os dados certos."
        return answer, 0.82, [], {"tools": tools}
