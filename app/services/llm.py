import json
import logging
import time

import httpx

from app.config import Settings


logger = logging.getLogger("uvicorn.error")


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
        started = time.perf_counter()
        logger.info("openrouter.request model=%s json_mode=%s", self.settings.openrouter_model, json_mode)
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
            usage = body.get("usage", {})
            logger.info(
                "openrouter.response model=%s status=%s latency_ms=%s prompt_tokens=%s completion_tokens=%s",
                body.get("model", self.settings.openrouter_model),
                response.status_code,
                int((time.perf_counter() - started) * 1000),
                usage.get("prompt_tokens", "n/a"),
                usage.get("completion_tokens", "n/a"),
            )
            return body["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning(
                "openrouter.error model=%s latency_ms=%s error=%s",
                self.settings.openrouter_model,
                int((time.perf_counter() - started) * 1000),
                type(exc).__name__,
            )
            raise

    async def json(self, system: str, user: str) -> dict:
        raw = await self.complete(system, user, json_mode=True)
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)
