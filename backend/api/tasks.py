import asyncio
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import AppConfig
from task_store import TaskStore
from ws_manager import WebSocketManager

router = APIRouter()
config = AppConfig.load()

_executor = ThreadPoolExecutor(max_workers=4)

task_store: TaskStore = None
ws_manager: WebSocketManager = None


def init(store: TaskStore, ws: WebSocketManager):
    global task_store, ws_manager
    task_store = store
    ws_manager = ws


class TaskCreateRequest(BaseModel):
    book_id: str = ""
    title: str = ""
    isbn: str = ""
    ss_code: str = ""
    source: str = "DX_6.0"
    bookmark: str | None = None
    authors: list[str] = []
    publisher: str = ""


@router.post("/api/v1/tasks")
async def create_task(req: TaskCreateRequest):
    task_id = task_store.create_task({
        "book_id": req.book_id,
        "title": req.title,
        "isbn": req.isbn,
        "ss_code": req.ss_code,
        "source": req.source,
        "bookmark": req.bookmark,
        "authors": req.authors,
        "publisher": req.publisher,
    })
    return {"task_id": task_id, "status": "pending"}


@router.get("/api/v1/tasks")
async def list_tasks():
    tasks = task_store.list_tasks()
    return {"tasks": tasks}


@router.delete("/api/v1/tasks/completed")
async def clear_completed_tasks():
    count = task_store.delete_completed_tasks()
    return {"status": "deleted", "count": count}


@router.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/api/v1/tasks/{task_id}/report")
async def get_task_report(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task not yet completed")
    return task.get("report", {})


@router.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    task_store.update_status(task_id, "cancelled")
    await ws_manager.send_log(task_id, "[SYSTEM] 任务已取消")
    return {"status": "cancelled"}


@router.post("/api/v1/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    from engine.pipeline import execute_pipeline
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    params = task.get("params", {})
    if isinstance(params, str):
        params = json.loads(params)

    new_task_id = task_store.create_task(params)

    _executor.submit(
        lambda: asyncio.run(execute_pipeline(new_task_id, params, task_store, ws_manager, config))
    )

    return {"task_id": new_task_id, "status": "started"}


@router.post("/api/v1/tasks/{task_id}/start")
async def start_task(task_id: str):
    """Start the 7-step pipeline for a task."""
    from engine.pipeline import execute_pipeline
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    params = task.get("params", {})
    if isinstance(params, str):
        import json
        params = json.loads(params)

    _executor.submit(
        lambda: asyncio.run(execute_pipeline(task_id, params, task_store, ws_manager, config))
    )

    return {"task_id": task_id, "status": "started"}


@router.delete("/api/v1/tasks/{task_id}")
async def delete_task(task_id: str):
    if not task_store.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted"}


@router.delete("/api/v1/tasks")
async def clear_all_tasks():
    count = task_store.delete_all_tasks()
    return {"status": "deleted", "count": count}


@router.get("/api/v1/tasks/{task_id}/open")
async def open_pdf(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    pipeline_state = task.get("pipeline_state")
    if isinstance(pipeline_state, str):
        pipeline_state = json.loads(pipeline_state)

    finished_path = None
    if isinstance(pipeline_state, dict):
        finished_path = pipeline_state.get("finished_path") or \
                        pipeline_state.get("bookmarked_pdf_path") or \
                        pipeline_state.get("compressed_pdf_path") or \
                        pipeline_state.get("ocr_pdf_path") or \
                        pipeline_state.get("pdf_path")

    if not finished_path or not os.path.exists(finished_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(finished_path, media_type="application/pdf", filename=os.path.basename(finished_path))


@router.get("/api/v1/tasks/{task_id}/open-folder")
async def open_folder(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    pipeline_state = task.get("pipeline_state")
    if isinstance(pipeline_state, str):
        pipeline_state = json.loads(pipeline_state)

    finished_path = None
    if isinstance(pipeline_state, dict):
        finished_path = pipeline_state.get("finished_path") or \
                        pipeline_state.get("bookmarked_pdf_path") or \
                        pipeline_state.get("compressed_pdf_path") or \
                        pipeline_state.get("ocr_pdf_path") or \
                        pipeline_state.get("pdf_path")

    if not finished_path or not os.path.exists(finished_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    folder = os.path.dirname(finished_path)
    try:
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {e}")

    return {"status": "ok", "folder": folder}
