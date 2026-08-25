import re
import logging
from html.parser import HTMLParser
from urllib.parse import quote_plus

import httpx


logger = logging.getLogger("uvicorn.error")


async def answer_external_question(question: str) -> tuple[str, list[dict]]:
    """Narrow, auditable public-data tools for common general questions."""
    lower = question.lower()
    if any(word in lower for word in ("euro", "dólar", "dolar", "câmbio", "cambio")):
        symbol = "EUR" if "euro" in lower else "USD"
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                response = await client.get(f"https://api.frankfurter.dev/v1/latest?from={symbol}&to=BRL")
                response.raise_for_status()
                data = response.json()
            rate = data["rates"]["BRL"]
            formatted_rate = f"{rate:.4f}".replace(".", ",")
            logger.info("exchange.response provider=frankfurter pair=%s/BRL date=%s", symbol, data["date"])
            return f"Na cotação de referência mais recente ({data['date']}), 1 {symbol} equivale a R$ {formatted_rate}. A taxa efetiva do banco ou casa de câmbio pode incluir spread e tarifas.", [{"title": "Frankfurter — câmbio de referência", "url": "https://frankfurter.dev/", "excerpt": f"{symbol}/BRL em {data['date']}"}]
        except Exception as exc:
            logger.warning("exchange.error provider=frankfurter pair=%s/BRL error=%s", symbol, type(exc).__name__)
            return "Não consegui consultar a cotação agora. Tente novamente em instantes ou consulte seu banco para a taxa efetiva.", []
    if any(word in lower for word in ("tempo", "clima", "previsão", "weather")):
        city_match = re.search(r"(?:em|de)\s+([A-Za-zÀ-ú ]+?)(?:\s+amanhã|\?|$)", question, re.I)
        city = (city_match.group(1).strip() if city_match else "Porto Alegre")
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"https://wttr.in/{city}", params={"format": "j1"})
                response.raise_for_status()
                forecast = response.json()["weather"][1]
            return f"A previsão para amanhã em {city} indica mínima de {forecast['mintempC']}°C e máxima de {forecast['maxtempC']}°C. Como previsões mudam, vale conferir novamente mais perto do horário.", [{"title": "wttr.in — previsão do tempo", "url": f"https://wttr.in/{city}", "excerpt": "Previsão para amanhã"}]
        except Exception:
            return f"Não consegui consultar a previsão para {city} agora. Tente novamente em instantes.", []
    results = await web_search(question)
    if results:
        bullets = "\n".join(f"• {item['title']}: {item['snippet']}" for item in results[:3])
        return f"Encontrei estas referências públicas sobre o tema:\n{bullets}\n\nComo é uma busca aberta, confirme informações críticas na fonte original.", results[:3]
    return "Essa pergunta foge do suporte Getnet e não encontrei uma fonte pública confiável agora. Posso ajudar com produtos, vendas, recebimentos ou sua maquininha.", []


class _SearchParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results, self.current, self.capture = [], {}, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "")
        if tag == "a" and "result__a" in classes:
            self.current = {"title": "", "url": attrs.get("href", ""), "snippet": "", "excerpt": ""}
            self.capture = "title"
        elif self.current is not None and "result__snippet" in classes:
            self.capture = "snippet"

    def handle_data(self, data):
        if self.current is not None and self.capture:
            self.current[self.capture] += data.strip() + " "

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None and self.capture == "title":
            self.capture = None
        elif tag in {"a", "div"} and self.current is not None and self.capture == "snippet":
            self.current["title"] = self.current["title"].strip()
            self.current["snippet"] = self.current["snippet"].strip()
            self.current["excerpt"] = self.current["snippet"]
            if self.current["title"] and self.current["url"]:
                self.results.append(self.current)
            self.current, self.capture = None, None


async def web_search(query: str) -> list[dict]:
    """Keyless search tool. Failures are contained and trigger safe handoff copy."""
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            response = await client.get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
            response.raise_for_status()
        parser = _SearchParser()
        parser.feed(response.text)
        return parser.results[:5]
    except Exception:
        return []
