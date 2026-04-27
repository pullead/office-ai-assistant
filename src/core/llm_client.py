# -*- coding: utf-8 -*-
"""外部 AI API クライアント。"""

from __future__ import annotations

import json
from urllib.parse import urlparse

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

        runtime = self._get_runtime_settings()

        headers = self._build_headers(runtime["provider"], runtime["api_key"])
        payload = self._build_payload(
            runtime["provider"],
            runtime["model"],
            system_prompt,
            user_prompt,
            temperature,
            max_tokens=runtime["max_tokens"],
        )

        try:
            response = requests.post(runtime["base_url"], headers=headers, json=payload, timeout=runtime["timeout"])
            response.raise_for_status()
            data = response.json()
            return self._extract_content(runtime["provider"], data)
        except HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            raise RuntimeError(
                self._format_http_error(runtime["provider"], runtime["base_url"], runtime["model"], status_code)
            ) from error
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
        runtime = self._get_runtime_settings()
        return json.dumps(
            {
                "enabled": self.is_enabled(),
                "provider": runtime["provider"],
                "base_url": runtime["base_url"],
                "model": runtime["model"],
                "has_api_key": bool(runtime["api_key"]),
            },
            ensure_ascii=False,
            indent=2,
        )

    def diagnose_connection(
        self,
        provider: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> dict:
        """接続設定を段階的に診断する。"""
        runtime = self._get_runtime_settings(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
            max_tokens=24,
        )
        items: list[dict[str, str]] = []
        suggestions: list[str] = []

        self._append_local_diagnostics(runtime, items, suggestions)
        if any(item["status"] == "error" for item in items):
            return self._build_diagnostic_result(runtime, items, suggestions, "", [])

        available_models: list[str] = []
        models_url = self._derive_models_url(runtime["base_url"])
        if models_url:
            model_result = self._fetch_model_catalog(runtime, models_url)
            items.append(model_result["item"])
            available_models = model_result["models"]
            if model_result["suggestion"]:
                suggestions.append(model_result["suggestion"])

        inference_result = self._run_inference_probe(runtime)
        items.append(inference_result["item"])
        if inference_result["suggestion"]:
            suggestions.append(inference_result["suggestion"])

        if available_models and runtime["model"] not in available_models:
            items.append(
                {
                    "name": "モデル名",
                    "status": "warning",
                    "message": "モデル一覧取得には成功しましたが、指定モデルは一覧で確認できませんでした。",
                }
            )
            suggestions.append("モデル名を公式ドキュメントまたは一覧取得結果と照合してください。")
        else:
            items.append(
                {
                    "name": "モデル名",
                    "status": "ok",
                    "message": "指定モデル名は形式上問題ありません。",
                }
            )

        return self._build_diagnostic_result(
            runtime,
            items,
            suggestions,
            inference_result["preview"],
            available_models[:12],
        )

    def test_connection(
        self,
        provider: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> tuple[bool, str]:
        """接続確認だけを簡潔に返す。"""
        result = self.diagnose_connection(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
        )
        return result["success"], result["summary"]

    def _get_runtime_settings(
        self,
        provider: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        max_tokens: int = 128,
    ) -> dict:
        """設定値と上書き値から実行時設定を組み立てる。"""
        provider_value = (
            provider if provider is not None else self.config.get("AIAPI", "provider", fallback="openrouter")
        ).strip().lower()
        base_url_value = (
            base_url
            if base_url is not None
            else self.config.get(
                "AIAPI",
                "base_url",
                fallback="https://openrouter.ai/api/v1/chat/completions",
            )
        ).strip()
        model_value = (
            model if model is not None else self.config.get("AIAPI", "model", fallback="openrouter/auto")
        ).strip()
        api_key_value = (
            api_key if api_key is not None else self.config.get("AIAPI", "api_key", fallback="")
        ).strip()
        timeout_value = timeout if timeout is not None else int(self.config.get("AIAPI", "timeout", fallback="60"))
        return {
            "provider": provider_value,
            "base_url": self._normalize_chat_completions_url(base_url_value),
            "model": model_value,
            "api_key": api_key_value,
            "timeout": timeout_value,
            "max_tokens": max_tokens,
        }

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
        max_tokens: int | None = None,
    ) -> dict:
        """プロバイダー別リクエスト本体を作る。"""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if provider == "siliconflow":
            payload["stream"] = False
        return payload

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

    def _append_local_diagnostics(self, runtime: dict, items: list[dict[str, str]], suggestions: list[str]):
        """ネットワーク送信前の基本チェックを追加する。"""
        if runtime["api_key"]:
            masked = f"{runtime['api_key'][:6]}...{runtime['api_key'][-4:]}" if len(runtime["api_key"]) >= 12 else "設定済み"
            items.append({"name": "API Key", "status": "ok", "message": f"API Key は入力済みです。({masked})"})
        else:
            items.append({"name": "API Key", "status": "error", "message": "API Key が未入力です。"})
            suggestions.append("各プロバイダーの管理画面で API Key を発行して入力してください。")

        parsed = urlparse(runtime["base_url"])
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            items.append({"name": "Base URL", "status": "ok", "message": runtime["base_url"]})
        else:
            items.append({"name": "Base URL", "status": "error", "message": "Base URL の形式が正しくありません。"})
            suggestions.append("https:// から始まるエンドポイントを指定してください。")

        if runtime["model"]:
            items.append({"name": "モデル", "status": "ok", "message": runtime["model"]})
        else:
            items.append({"name": "モデル", "status": "error", "message": "モデル名が未入力です。"})
            suggestions.append("モデル欄に有効なモデル ID を入力してください。")

    def _fetch_model_catalog(self, runtime: dict, models_url: str) -> dict:
        """モデル一覧を取得して診断に使う。"""
        headers = self._build_headers(runtime["provider"], runtime["api_key"])
        try:
            response = requests.get(models_url, headers=headers, timeout=min(runtime["timeout"], 20))
            response.raise_for_status()
            data = response.json()
            models = self._extract_model_ids(data)
            message = "モデル一覧の取得に成功しました。"
            if models:
                message += f" 利用可能モデル例: {', '.join(models[:5])}"
            return {
                "item": {"name": "モデル一覧取得", "status": "ok", "message": message},
                "models": models,
                "suggestion": "",
            }
        except HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            return {
                "item": {
                    "name": "モデル一覧取得",
                    "status": "warning",
                    "message": self._format_http_error(runtime["provider"], models_url, runtime["model"], status_code),
                },
                "models": [],
                "suggestion": "モデル一覧の取得ができない場合でも、推論テスト結果は継続して確認してください。",
            }
        except RequestException:
            return {
                "item": {
                    "name": "モデル一覧取得",
                    "status": "warning",
                    "message": "モデル一覧の取得に失敗しました。ネットワークまたはエンドポイント設定を確認してください。",
                },
                "models": [],
                "suggestion": "社内ネットワークやプロキシ利用時は接続制限の可能性も確認してください。",
            }

    def _run_inference_probe(self, runtime: dict) -> dict:
        """最小推論で実際に応答できるかを検証する。"""
        headers = self._build_headers(runtime["provider"], runtime["api_key"])
        payload = self._build_payload(
            runtime["provider"],
            runtime["model"],
            "あなたは接続テスト用のアシスタントです。短く答えてください。",
            "接続テストです。OK とだけ返してください。",
            0.0,
            max_tokens=runtime["max_tokens"],
        )
        try:
            response = requests.post(runtime["base_url"], headers=headers, json=payload, timeout=runtime["timeout"])
            response.raise_for_status()
            data = response.json()
            preview = self._extract_content(runtime["provider"], data)[:240]
            return {
                "item": {"name": "推論テスト", "status": "ok", "message": "推論リクエストに成功しました。"},
                "preview": preview,
                "suggestion": "",
            }
        except HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            return {
                "item": {
                    "name": "推論テスト",
                    "status": "error",
                    "message": self._format_http_error(
                        runtime["provider"], runtime["base_url"], runtime["model"], status_code
                    ),
                },
                "preview": "",
                "suggestion": "認証・権限・残高・モデル名のいずれかに問題がある可能性があります。",
            }
        except RequestException:
            return {
                "item": {
                    "name": "推論テスト",
                    "status": "error",
                    "message": "推論テストで通信エラーが発生しました。",
                },
                "preview": "",
                "suggestion": "ネットワーク接続、VPN、社内プロキシ、タイムアウト秒数を確認してください。",
            }
        except Exception as error:
            return {
                "item": {
                    "name": "推論テスト",
                    "status": "error",
                    "message": f"応答解析に失敗しました: {error}",
                },
                "preview": "",
                "suggestion": "互換 API の応答形式が異なる場合は、OpenAI 互換設定と実際の API 仕様を照合してください。",
            }

    def _build_diagnostic_result(
        self,
        runtime: dict,
        items: list[dict[str, str]],
        suggestions: list[str],
        preview: str,
        available_models: list[str],
    ) -> dict:
        """診断結果全体をまとめる。"""
        has_error = any(item["status"] == "error" for item in items)
        has_warning = any(item["status"] == "warning" for item in items)
        if has_error:
            summary = "接続テストは未完了または失敗です。エラー項目を優先して修正してください。"
        elif has_warning:
            summary = "一部警告がありますが、設定の一部は有効です。詳細を確認してください。"
        else:
            summary = "接続テストは成功しました。現在の設定で API 連携できる見込みです。"
        return {
            "success": not has_error,
            "summary": summary,
            "provider": runtime["provider"],
            "base_url": runtime["base_url"],
            "model": runtime["model"],
            "items": items,
            "suggestions": list(dict.fromkeys(suggestions)),
            "preview": preview,
            "available_models": available_models,
        }

    def _normalize_chat_completions_url(self, base_url: str) -> str:
        """入力値から chat/completions URL を補正する。"""
        url = base_url.strip().rstrip("/")
        if not url:
            return url
        if url.endswith("/chat/completions") or url.endswith("/text/chatcompletion_v2"):
            return url
        if url.endswith("/v1") or url.endswith("/v4") or url.endswith("/compatible-mode/v1"):
            return f"{url}/chat/completions"
        if url.endswith("/api"):
            return f"{url}/v1/chat/completions"
        return url

    def _derive_models_url(self, base_url: str) -> str | None:
        """chat/completions から models URL を推定する。"""
        if not base_url:
            return None
        if base_url.endswith("/chat/completions"):
            return base_url[: -len("/chat/completions")] + "/models"
        if base_url.endswith("/completions"):
            return base_url[: -len("/completions")] + "/models"
        return None

    def _extract_model_ids(self, data: dict) -> list[str]:
        """モデル一覧レスポンスから ID を抽出する。"""
        entries = data.get("data")
        if not isinstance(entries, list):
            return []
        models: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            model_id = entry.get("id")
            if isinstance(model_id, str) and model_id:
                models.append(model_id)
        return models
