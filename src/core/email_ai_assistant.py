# -*- coding: utf-8 -*-
"""AI メールアシスタント用の解析と下書き生成。"""

from __future__ import annotations

import re
from email import policy
from email.parser import BytesParser
from pathlib import Path


class EmailAIAssistant:
    """メール内容の抽出、要約、返信草案生成を担当する。"""

    def parse_email_text(self, raw_text: str, fallback_subject: str = "", fallback_sender: str = "") -> dict[str, str]:
        """貼り付けテキストからメール要素を抽出する。"""
        text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
        lines = text.splitlines()

        subject = fallback_subject.strip()
        sender = fallback_sender.strip()
        recipient = ""
        body_lines: list[str] = []
        in_body = False

        for line in lines:
            if not in_body and not line.strip():
                in_body = True
                continue
            lowered = line.lower()
            if lowered.startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                continue
            if lowered.startswith("from:"):
                sender = line.split(":", 1)[1].strip()
                continue
            if lowered.startswith("to:"):
                recipient = line.split(":", 1)[1].strip()
                continue
            if in_body:
                body_lines.append(line)

        if not body_lines:
            body_lines = [line for line in lines if not self._looks_like_header(line)]

        body = "\n".join(body_lines).strip()
        return {
            "subject": subject or "件名未抽出",
            "sender": sender or "送信者未抽出",
            "recipient": recipient or "",
            "body": body or text.strip(),
            "keywords": self._extract_keywords(body or text),
            "action_items": self._extract_action_items(body or text),
            "tone": self._detect_tone(body or text),
        }

    def parse_email_file(self, file_path: str) -> dict[str, str]:
        """EML またはテキストファイルからメール内容を抽出する。"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".eml":
            with open(path, "rb") as handle:
                message = BytesParser(policy=policy.default).parse(handle)
            body = self._extract_body_from_message(message)
            return {
                "subject": message.get("Subject", "件名未抽出"),
                "sender": message.get("From", "送信者未抽出"),
                "recipient": message.get("To", ""),
                "body": body,
                "keywords": self._extract_keywords(body),
                "action_items": self._extract_action_items(body),
                "tone": self._detect_tone(body),
            }
        return self.parse_email_text(self._read_text_with_fallback(path))

    def build_local_analysis_html(self, parsed: dict[str, str]) -> str:
        """ローカル解析結果を HTML 化する。"""
        keywords = parsed.get("keywords") or "なし"
        action_items = parsed.get("action_items") or "なし"
        body_preview = self._escape_html(parsed.get("body", "")[:1800]).replace("\n", "<br>")
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>メール分析レポート</h2>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:12px;'>"
            f"{self._table_row('件名', parsed.get('subject', ''))}"
            f"{self._table_row('送信者', parsed.get('sender', ''))}"
            f"{self._table_row('宛先', parsed.get('recipient', '未抽出'))}"
            f"{self._table_row('文体', parsed.get('tone', '標準'))}"
            f"{self._table_row('要点語', keywords)}"
            f"{self._table_row('アクション候補', action_items)}"
            "</table>"
            "<h3>本文プレビュー</h3>"
            f"<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:16px;line-height:1.7;'>{body_preview}</div>"
            "</div>"
        )

    def build_local_reply(self, parsed: dict[str, str], purpose: str, tone: str, extra_request: str = "") -> dict[str, str]:
        """ローカル返信草案を生成する。"""
        subject = parsed.get("subject", "").strip()
        sender = parsed.get("sender", "").strip()
        keywords = parsed.get("keywords", "")
        actions = parsed.get("action_items", "")
        purpose_text = {
            "reply": "お問い合わせへの返信",
            "accept": "依頼受諾の返信",
            "followup": "追加確認の返信",
        }.get(purpose, "メール返信")
        tone_prefix = {
            "formal": "丁寧で正式な文体",
            "friendly": "親しみやすく丁寧な文体",
            "brief": "簡潔で要点重視の文体",
        }.get(tone, "丁寧な文体")

        reply_subject = f"Re: {subject}" if subject and not subject.lower().startswith("re:") else (subject or "ご連絡ありがとうございます")
        body_lines = [
            f"{sender} 様",
            "",
            "いつもお世話になっております。",
            "ご連絡ありがとうございます。",
            "",
            f"メール内容を確認し、{purpose_text}として以下の通りご返信いたします。",
            "",
            f"要点: {keywords or 'ご依頼内容を確認しました。'}",
        ]
        if actions:
            body_lines.append(f"確認事項: {actions}")
        body_lines.extend(
            [
                "",
                "詳細につきましては、必要に応じて追加でご案内いたします。",
                "何卒よろしくお願いいたします。",
            ]
        )
        if extra_request.strip():
            body_lines.extend(["", f"補足要望: {extra_request.strip()}"])

        return {
            "subject": reply_subject,
            "body": "\n".join(body_lines),
            "style_note": tone_prefix,
        }

    def build_refined_reply(self, draft_body: str, instruction: str) -> str:
        """既存返信文をローカルルールで調整する。"""
        body = draft_body.strip()
        if not instruction.strip():
            return body
        return (
            body
            + "\n\n"
            + "-----\n"
            + "修正指示メモ\n"
            + instruction.strip()
        )

    def build_ai_analysis_prompt(self, parsed: dict[str, str]) -> str:
        """AI 分析用プロンプトを返す。"""
        return (
            "以下のメールを分析し、重要点、依頼内容、緊急度、返信時の注意点を整理してください。\n\n"
            f"件名: {parsed.get('subject', '')}\n"
            f"送信者: {parsed.get('sender', '')}\n"
            f"宛先: {parsed.get('recipient', '')}\n"
            f"本文:\n{parsed.get('body', '')}"
        )

    def build_ai_reply_prompt(self, parsed: dict[str, str], purpose: str, tone: str, extra_request: str) -> str:
        """AI 返信生成用プロンプトを返す。"""
        return (
            "以下のメールに対して、日本語で業務向けの返信文を作成してください。"
            "件名案、要点、完成返信文を含めてください。\n\n"
            f"返信目的: {purpose}\n"
            f"文体: {tone}\n"
            f"追加要望: {extra_request or 'なし'}\n"
            f"件名: {parsed.get('subject', '')}\n"
            f"送信者: {parsed.get('sender', '')}\n"
            f"本文:\n{parsed.get('body', '')}"
        )

    def build_ai_refine_prompt(self, draft_subject: str, draft_body: str, instruction: str) -> str:
        """AI 返信修正用プロンプトを返す。"""
        return (
            "以下の返信草案を修正してください。件名案と本文を返してください。\n\n"
            f"現在の件名: {draft_subject}\n"
            f"現在の本文:\n{draft_body}\n\n"
            f"修正要望:\n{instruction}"
        )

    def _extract_body_from_message(self, message) -> str:
        """EML から本文を取り出す。"""
        if message.is_multipart():
            bodies = []
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        bodies.append(part.get_content())
                    except Exception:
                        continue
            return "\n".join(body.strip() for body in bodies if body.strip())
        try:
            return str(message.get_content()).strip()
        except Exception:
            return ""

    def _extract_keywords(self, text: str) -> str:
        """簡易的に重要語を抽出する。"""
        tokens = re.findall(r"[A-Za-z0-9_\u3041-\u30ff\u4e00-\u9fff]{2,}", text)
        counts: dict[str, int] = {}
        stopwords = {"です", "ます", "こと", "ため", "こちら", "いつも", "お世話", "よろしく"}
        for token in tokens:
            if token in stopwords:
                continue
            counts[token] = counts.get(token, 0) + 1
        top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:6]
        return " / ".join(token for token, _count in top)

    def _extract_action_items(self, text: str) -> str:
        """メール内の依頼や確認事項を拾う。"""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        candidates = []
        markers = ("お願い", "確認", "依頼", "希望", "ください", "ご対応", "ご連絡")
        for line in lines:
            if any(marker in line for marker in markers):
                candidates.append(line)
        return " / ".join(candidates[:4])

    def _detect_tone(self, text: str) -> str:
        """本文の雰囲気を推定する。"""
        if any(token in text for token in ("至急", "緊急", "急ぎ")):
            return "緊急"
        if any(token in text for token in ("お問い合わせ", "ご相談", "お願い")):
            return "丁寧"
        return "標準"

    def _looks_like_header(self, line: str) -> bool:
        """ヘッダーらしい行かを判定する。"""
        lowered = line.lower().strip()
        return lowered.startswith(("subject:", "from:", "to:", "date:", "cc:"))

    def _read_text_with_fallback(self, path: Path) -> str:
        """文字コード候補を切り替えて読む。"""
        for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return ""

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _table_row(self, label: str, value: str) -> str:
        """2列テーブル行を返す。"""
        return (
            "<tr>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;width:22%;'>{self._escape_html(label)}</td>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(value)}</td>"
            "</tr>"
        )
