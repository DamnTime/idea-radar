import asyncio
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from src.models import ScoredIdea
from src.notifiers.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    def __init__(self, config: dict):
        self.smtp_host = config.get("smtp_host", os.getenv("SMTP_HOST", "smtp.gmail.com"))
        self.smtp_port = config.get("smtp_port", int(os.getenv("SMTP_PORT", "587")))
        self.smtp_user = config.get("smtp_user", os.getenv("SMTP_USER", ""))
        self.smtp_pass = config.get("smtp_pass", os.getenv("SMTP_PASS", ""))
        raw_from = config.get("from_addr", os.getenv("EMAIL_FROM", ""))
        if raw_from and "${" not in raw_from:
            self.from_addr = raw_from
        else:
            self.from_addr = self.smtp_user
        recipients_raw = config.get("to_addrs", os.getenv("EMAIL_RECIPIENTS", ""))
        self.to_addrs = [r.strip() for r in recipients_raw.split(",") if r.strip()]
        self._custom_template = self._load_template()

    @staticmethod
    def _load_template() -> str | None:
        template_path = Path("templates/email.html")
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return None

    async def send(self, ideas: list[ScoredIdea]) -> bool:
        if not self.to_addrs:
            print("[EmailNotifier] No recipients configured, skipping")
            return False

        html = self._render(ideas)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 今日创业点子推荐 ({date.today().isoformat()})"
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg.attach(MIMEText(html, "html", "utf-8"))

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._send_sync, msg)
            print(f"[EmailNotifier] Sent to {len(self.to_addrs)} recipients, {len(ideas)} ideas")
            return True
        except Exception as e:
            print(f"[EmailNotifier] Failed to send email: {e}")
            return False

    def _send_sync(self, msg: MIMEMultipart):
        if self.smtp_port == 465:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.starttls()
        with server:
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())

    def _render(self, ideas: list[ScoredIdea]) -> str:
        if self._custom_template:
            items_html = "".join(
                self._render_item(i) for i in ideas
            )
            return self._custom_template.replace("{{items}}", items_html) \
                                        .replace("{{date}}", date.today().isoformat()) \
                                        .replace("{{count}}", str(len(ideas)))

        items_html = "".join(self._render_item(i) for i in ideas)
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="max-width:600px;margin:0 auto;padding:20px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <h1 style="color:#333;border-bottom:2px solid #1a73e8;padding-bottom:12px;font-size:22px;">
        🚀 今日创业点子推荐
    </h1>
    <p style="color:#666;font-size:14px;">{date.today().isoformat()} | 共 {len(ideas)} 条</p>
    {items_html}
    <hr style="margin:32px 0;border:none;border-top:1px solid #eee;">
    <p style="color:#aaa;font-size:12px;text-align:center;">
        🤖 由 AI 轻创业日报自动生成<br>
        数据源: Reddit + 知乎 + RSS
    </p>
</body>
</html>"""

    @staticmethod
    def _render_item(i: ScoredIdea) -> str:
        color = "#1a73e8" if i.overall_score >= 7 else "#e8a71a" if i.overall_score >= 5 else "#999"
        return f"""<div style="margin-bottom:20px;padding:16px;border-radius:8px;background:#f8f9fa;border-left:4px solid {color};">
    <h3 style="margin:0 0 6px;font-size:16px;">
        <a href="{i.item.url}" style="color:#1a73e8;text-decoration:none;" target="_blank">
            {i.item.title}
        </a>
    </h3>
    <div style="margin:6px 0;">
        <span style="display:inline-block;background:{color};color:#fff;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:600;">
            综合评分: {i.overall_score}/10
        </span>
        <span style="margin-left:8px;color:#888;font-size:13px;">
            来源: {i.item.source}
        </span>
    </div>
    <p style="color:#444;font-size:14px;line-height:1.6;margin:8px 0 0;">{i.analysis}</p>
    <p style="color:#aaa;font-size:12px;margin:6px 0 0;">
        {i.item.author or "匿名"} · {i.item.published_at.strftime("%m-%d %H:%M") if i.item.published_at else ""}
    </p>
</div>"""
