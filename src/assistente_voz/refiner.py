"""Refinamento da transcrição via LLM de chat (Groq/OpenAI/Gemini).

Recebe o texto transcrito + um prompt de sistema + contexto opcional e devolve
uma versão revisada. Cada provedor tem sua implementação; ``make_refiner`` cria
a certa. As chaves são as mesmas dos provedores (reaproveitadas).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Refiner(Protocol):
    def refine(self, text: str, system_prompt: str, context: str = "") -> str: ...


def _user_content(text: str, context: str) -> str:
    if context:
        return (
            "CONTEXTO (referência para entender o assunto; não repita, não "
            f"comente):\n{context}\n\n---\nTEXTO A REVISAR:\n{text}"
        )
    return text


class GroqRefiner:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        if not api_key:
            raise ValueError("Chave da Groq ausente")
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model

    def refine(self, text: str, system_prompt: str, context: str = "") -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _user_content(text, context)},
            ],
        )
        return (resp.choices[0].message.content or "").strip()


class OpenAIRefiner:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("Chave da OpenAI ausente")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def refine(self, text: str, system_prompt: str, context: str = "") -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _user_content(text, context)},
            ],
        )
        return (resp.choices[0].message.content or "").strip()


class GeminiRefiner:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError("Chave do Gemini ausente")
        self._key = api_key
        self._model = model

    def refine(self, text: str, system_prompt: str, context: str = "") -> str:
        import json
        import urllib.request

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._key}"
        )
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": _user_content(text, context)}]}],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def make_refiner(provider: str, api_key: str, model: str) -> Refiner:
    if provider == "openai":
        return OpenAIRefiner(api_key, model)
    if provider == "gemini":
        return GeminiRefiner(api_key, model)
    return GroqRefiner(api_key, model)
