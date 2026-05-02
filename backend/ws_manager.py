import asyncio
import json
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket):
        await ws.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(ws)

    def disconnect(self, task_id: str, ws: WebSocket):
        if task_id in self._connections:
            try:
                self._connections[task_id].remove(ws)
            except ValueError:
                pass
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def broadcast(self, task_id: str, message: dict):
        if task_id not in self._connections:
            return
        dead = []
        data = json.dumps(message, default=str)
        for ws in self._connections[task_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(task_id, ws)

    async def send_step_start(self, task_id: str, step: float, step_name: str):
        await self.broadcast(task_id, {
            "type": "step_start",
            "task_id": task_id,
            "step": step,
            "step_name": step_name,
        })

    async def send_step_progress(self, task_id: str, step: float, step_name: str,
                                  progress_pct: int, message: str = ""):
        await self.broadcast(task_id, {
            "type": "step_progress",
            "task_id": task_id,
            "step": step,
            "step_name": step_name,
            "progress_pct": progress_pct,
            "message": message,
        })

    async def send_step_complete(self, task_id: str, step: float, step_name: str,
                                  elapsed_ms: int = 0, output: Any = None):
        await self.broadcast(task_id, {
            "type": "step_complete",
            "task_id": task_id,
            "step": step,
            "step_name": step_name,
            "elapsed_ms": elapsed_ms,
            "output": output,
        })

    async def send_log(self, task_id: str, message: str):
        await self.broadcast(task_id, {
            "type": "log",
            "task_id": task_id,
            "message": message,
        })

    async def send_task_complete(self, task_id: str, report: dict):
        await self.broadcast(task_id, {
            "type": "task_complete",
            "task_id": task_id,
            "report": report,
        })

    async def send_task_error(self, task_id: str, step: float, error: str):
        await self.broadcast(task_id, {
            "type": "task_error",
            "task_id": task_id,
            "step": step,
            "error": error,
        })

    def has_connections(self, task_id: str) -> bool:
        return task_id in self._connections and len(self._connections[task_id]) > 0
