from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws_manager import WebSocketManager
from task_store import TaskStore

router = APIRouter()

ws_manager: WebSocketManager = None
task_store: TaskStore = None


def init(store: TaskStore, ws: WebSocketManager):
    global task_store, ws_manager
    task_store = store
    ws_manager = ws


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task(ws: WebSocket, task_id: str):
    await ws_manager.connect(task_id, ws)

    task = task_store.get_task(task_id)
    if task:
        await ws.send_json({
            "type": "sync",
            "task_id": task_id,
            "status": task.get("status"),
            "steps": task.get("steps", []),
            "log_lines": task.get("log_lines", []),
            "report": task.get("report"),
        })

    try:
        while True:
            data = await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, ws)
    except Exception:
        ws_manager.disconnect(task_id, ws)
