import json

import httpx

from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(self.settings.openrouter_api_key) and not self.settings.demo_mode

    async def complete(self, system: str, user: str, *, temperature: float = 0.1, json_mode: bool = False) -> str:
        if not self.available:
            raise RuntimeError("LLM indisponível em modo demo")
        payload = {
            "model": self.settings.openrouter_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": self.settings.app_name,
        }
        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def json(self, system: str, user: str) -> dict:
        raw = await self.complete(system, user, json_mode=True)
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)

