# -*- coding: utf-8 -*-
"""外部 AI API クライアント。"""

from __future__ import annotations

import json

import requests
from requests import HTTPError, RequestException

from src.config import Config


class LLMClient:
    """OpenAI 互換 API を中心に複数プロバイダーを扱う。"""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    def is_enabled(self) -> bool:
        """AI API の有効設定を返す。"""
        return self.config.get_bool("AIAPI", "enabled", fallback=False)

    def is_configured(self) -> bool:
        """API Key が設定済みかを返す。"""
        return bool(self.config.get("AIAPI", "api_key", fallback="").strip())

    def analyze(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """AI API に問い合わせてテキストを生成する。"""
        if not self.is_enabled() or not self.is_configured():
            raise RuntimeError("AI API が未設定です。")

        provider = self.config.get("AIAPI", "provider", fallback="openrouter").strip().lower()
        base_url = self.config.get(
            "AIAPI",
            "base_url",
            fallback="https://openrouter.ai/api/v1/chat/completions",
        ).strip()
        model = self.config.get("AIAPI", "model", fallback="openrouter/auto").strip()
        api_key = self.config.get("AIAPI", "api_key", fallback="").strip()
        timeout = int(self.config.get("AIAPI", "timeout", fallback="60"))

        headers = self._build_headers(provider, api_key)
        payload = self._build_payload(provider, model, system_prompt, user_prompt, temperature)

        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return self._extract_content(provider, data)
        except HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            raise RuntimeError(self._format_http_error(provider, base_url, model, status_code)) from error
        except RequestException as error:
            raise RuntimeError(
                "AI API 通信エラーが発生しました。ネットワーク接続、Base URL、タイムアウト設定を確認してください。"
            ) from error
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                "AI API の応答形式を解析できませんでした。モデル設定またはプロバイダー設定を確認してください。"
            ) from error

    def summarize_to_html(self, title: str, prompt: str) -> str:
        """分析結果を HTML レポート形式へ整形する。"""
        system_prompt = (
            "あなたは日本語の業務レポート作成アシスタントです。"
            "要点、重要数値、次アクションがひと目で分かる HTML を返してください。"
            "見出し、短い要約、表や箇条書きを使い、body タグ内だけを返してください。"
        )
        user_prompt = f"タイトル: {title}\n\n次の内容を、視認性の高い HTML レポートに整形してください。\n\n{prompt}"
        return self.analyze(system_prompt=system_prompt, user_prompt=user_prompt)

    def explain_chart(self, chart_context: str) -> str:
        """グラフ解説を生成する。"""
        system_prompt = (
            "あなたは日本語のデータ分析アシスタントです。"
            "グラフから読み取れる傾向、異常、示唆を簡潔に説明してください。"
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

    def _build_headers(self, provider: str, api_key: str) -> dict[str, str]:
        """プロバイダー別ヘッダーを作る。"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://local.office-ai-assistant"
            headers["X-Title"] = "Office AI Assistant"
        return headers

    def _build_payload(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict:
        """プロバイダー別リクエスト本体を作る。"""
        if provider == "minimax":
            return {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

    def _extract_content(self, provider: str, response_json: dict) -> str:
        """プロバイダー別レスポンスから本文を取り出す。"""
        if provider == "minimax":
            if "choices" in response_json:
                content = response_json["choices"][0]["message"]["content"]
                return self._normalize_content(content)
            # 一部互換レスポンス向けフォールバック
            if "reply" in response_json:
                return str(response_json["reply"]).strip()
        content = response_json["choices"][0]["message"]["content"]
        return self._normalize_content(content)

    def _format_http_error(self, provider: str, base_url: str, model: str, status_code: int | None) -> str:
        """HTTP ステータスに応じたエラーメッセージを返す。"""
        common = (
            f"AI API エラー: provider={provider}, model={model}, endpoint={base_url}"
        )
        if status_code in {401, 403}:
            return (
                "AI API の認証に失敗しました。API Key、モデル権限、Base URL の組み合わせを確認してください。"
                f" ({common})"
            )
        if status_code == 404:
            return (
                "AI API のエンドポイントまたはモデル名が見つかりません。"
                "プロバイダー選択と Base URL / model を再確認してください。"
                f" ({common})"
            )
        if status_code == 429:
            return (
                "AI API の利用上限に達しました。無料枠やレート制限を確認し、少し時間をおいて再実行してください。"
                f" ({common})"
            )
        if status_code and status_code >= 500:
            return (
                "AI API 側で一時的な障害が発生しています。時間をおいて再試行してください。"
                f" ({common})"
            )
        return f"AI API 呼び出しで HTTP エラーが発生しました。({common})"

    def _normalize_content(self, content) -> str:
        """レスポンス本文を文字列へ正規化する。"""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            pieces = []
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        pieces.append(text_value)
                elif isinstance(item, str):
                    pieces.append(item)
            return "\n".join(piece.strip() for piece in pieces if piece.strip()).strip()
        return str(content).strip()
