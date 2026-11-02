"""Telegram channel: talk to your agent from your phone.

Uses the Bot API over HTTPS long polling, so no public URL or webhook is
needed. Only chat IDs listed in channels.telegram.allowed_chat_ids are
served; messages from anyone else are ignored and their chat ID is logged so
you can add your own.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any

import requests

from agentic.approvals import ApprovalRequest, PendingApprovals
from agentic.config import TelegramConfig

if TYPE_CHECKING:
    from agentic.runtime import Runtime

API = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE = 4000
log = logging.getLogger("agentic.telegram")


def chunk(text: str, size: int = MAX_MESSAGE) -> list[str]:
    text = text or "(empty)"
    parts = []
    while text:
        if len(text) <= size:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, size)
        cut = cut if cut > size // 2 else size
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


class TelegramChannel:
    def __init__(self, runtime: Runtime, config: TelegramConfig, approvals: PendingApprovals):
        token = os.getenv(config.token_env)
        if not token:
            raise RuntimeError(f"Set {config.token_env} to enable the Telegram channel")
        self.runtime = runtime
        self.token = token
        self.allowed = set(config.allowed_chat_ids)
        self.approvals = approvals
        self.session = requests.Session()
        self._offset = 0
        self._stopped = False

    def _call(self, method: str, timeout: float = 40, **payload: Any) -> Any:
        response = self.session.post(
            API.format(token=self.token, method=method), json=payload, timeout=timeout
        )
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {data.get('description')}")
        return data["result"]

    async def send(self, chat_id: int | str, text: str) -> None:
        for part in chunk(text):
            await asyncio.to_thread(self._call, "sendMessage", 20, chat_id=chat_id, text=part)

    async def notify(self, target: str, text: str) -> None:
        """Deliver to a 'telegram:<chat_id>' target (used by the scheduler)."""
        if target.startswith("telegram:"):
            await self.send(target.split(":", 1)[1], text)

    def on_approval_request(self, request: ApprovalRequest) -> None:
        if not request.origin.startswith("telegram:"):
            return
        chat_id = request.origin.split(":", 1)[1]
        text = (
            f"🔐 Approval needed [{request.id}]\n{request.summary()}\n\n"
            f"Reply /approve {request.id} or /deny {request.id}"
        )
        asyncio.get_running_loop().create_task(self.send(chat_id, text))

    async def _handle(self, message: dict[str, Any]) -> None:
        chat_id = message.get("chat", {}).get("id")
        text = (message.get("text") or "").strip()
        if chat_id is None or not text:
            return
        if chat_id not in self.allowed:
            log.warning("Ignoring Telegram chat %s (add it to allowed_chat_ids)", chat_id)
            return
        command, _, rest = text.partition(" ")
        command = command.split("@", 1)[0]
        if command in {"/approve", "/deny"}:
            found = self.approvals.resolve(rest.strip(), command == "/approve")
            await self.send(chat_id, "Done." if found else "No pending approval with that id.")
            return
        if command == "/start":
            text = "/help"
        await asyncio.to_thread(self._call, "sendChatAction", 10, chat_id=chat_id, action="typing")
        reply = await self.runtime.chat(f"telegram:{chat_id}", text, origin=f"telegram:{chat_id}")
        await self.send(chat_id, reply)

    async def loop(self) -> None:
        me = await asyncio.to_thread(self._call, "getMe", 15)
        log.info("Telegram channel online as @%s", me.get("username"))
        while not self._stopped:
            try:
                updates = await asyncio.to_thread(
                    self._call,
                    "getUpdates",
                    40,
                    offset=self._offset,
                    timeout=30,
                    allowed_updates=["message"],
                )
            except Exception as exc:
                log.warning("Telegram polling error: %s", exc)
                await asyncio.sleep(5)
                continue
            for update in updates:
                self._offset = update["update_id"] + 1
                if "message" in update:
                    # Each message runs independently so approvals can arrive mid-run.
                    asyncio.create_task(self._safe_handle(update["message"]))

    async def _safe_handle(self, message: dict[str, Any]) -> None:
        try:
            await self._handle(message)
        except Exception:
            log.exception("Telegram message handling failed")

    def stop(self) -> None:
        self._stopped = True
