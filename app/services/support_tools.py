import json
from pathlib import Path
from typing import Any


class CustomerRepository:
    def __init__(self, path: Path):
        self.customers = json.loads(path.read_text(encoding="utf-8"))

    def get_customer_profile(self, user_id: str) -> dict[str, Any] | None:
        """Tool 1: returns a privacy-safe customer and terminal profile."""
        return self.customers.get(user_id)

    def get_receivables(self, user_id: str) -> list[dict[str, Any]]:
        """Tool 2: returns the customer's upcoming settlement schedule."""
        customer = self.customers.get(user_id, {})
        return customer.get("receivables", [])

    def diagnose_terminal(self, user_id: str, symptom: str) -> dict[str, Any]:
        """Tool 3: combines terminal telemetry with a safe troubleshooting runbook."""
        customer = self.customers.get(user_id)
        if not customer:
            return {"known_customer": False, "steps": ["Confirme o CPF/CNPJ cadastrado", "Contate o suporte Getnet"]}
        terminal = customer["terminal"]
        return {
            "known_customer": True,
            "terminal": terminal,
            "symptom": symptom,
            "steps": ["Verifique energia e intensidade do sinal", "Alterne entre Wi-Fi e chip", "Reinicie a maquininha e faça uma venda teste"],
            "existing_ticket": next(iter(customer.get("open_tickets", [])), None),
        }


def brl(value: float) -> str:
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
