# -*- coding: utf-8 -*-
"""外部 AI API を扱うクライアント。"""

from __future__ import annotations

import json

import requests

from src.config import Config


class LLMClient:
    """OpenAI 互換 API へ接続する。"""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    def is_enabled(self) -> bool:
        """AI API の有効設定を返す。"""
        return self.config.get_bool("AIAPI", "enabled", fallback=False)

    def is_configured(self) -> bool:
        """API Key が設定済みかを返す。"""
        return bool(self.config.get("AIAPI", "api_key", fallback="").strip())

    def analyze(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """AI API に問い合わせて文章を得る。"""
        if not self.is_enabled() or not self.is_configured():
            raise RuntimeError("AI API が未設定です。")

        provider = self.config.get("AIAPI", "provider", fallback="openrouter").strip().lower()
        base_url = self.config.get(
            "AIAPI",
            "base_url",
            fallback="https://openrouter.ai/api/v1/chat/completions",
        ).strip()
        model = self.config.get("AIAPI", "model", fallback="openrouter/free").strip()
        api_key = self.config.get("AIAPI", "api_key", fallback="").strip()
        timeout = int(self.config.get("AIAPI", "timeout", fallback="45"))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://local.office-ai-assistant"
            headers["X-Title"] = "Office AI Assistant"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        response = requests.post(base_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def summarize_to_html(self, title: str, prompt: str) -> str:
        """分析結果を HTML レポートへ整形する。"""
        system_prompt = (
            "あなたは日本語の業務レポート作成アシスタントです。"
            "要点、重要数値、次アクションがひと目で分かる HTML を返してください。"
            "見出し、短い要約、表や箇条書き風の構造を使い、body タグ内だけを返してください。"
        )
        user_prompt = f"タイトル: {title}\n\n次の内容を、視認性の高い HTML レポートに整形してください。\n\n{prompt}"
        return self.analyze(system_prompt=system_prompt, user_prompt=user_prompt)

    def explain_chart(self, chart_context: str) -> str:
        """グラフの読み取りコメントを生成する。"""
        system_prompt = (
            "あなたは日本語のデータ分析アシスタントです。"
            "グラフから読み取れる傾向、異常、示唆を短く明確に説明してください。"
        )
        return self.analyze(system_prompt=system_prompt, user_prompt=chart_context)

    def debug_summary(self) -> str:
        """現在の API 設定概要を返す。"""
        return json.dumps(
            {
                "enabled": self.is_enabled(),
                "provider": self.config.get("AIAPI", "provider", fallback="openrouter"),
                "base_url": self.config.get("AIAPI", "base_url", fallback=""),
                "model": self.config.get("AIAPI", "model", fallback=""),
                "has_api_key": bool(self.config.get("AIAPI", "api_key", fallback="").strip()),
            },
            ensure_ascii=False,
            indent=2,
        )
