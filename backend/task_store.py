import json
import sqlite3
import uuid
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

from config import AppConfig

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    current_step INTEGER DEFAULT 0,
    current_step_name TEXT,
    params TEXT,
    pipeline_state TEXT,
    steps TEXT,
    log_lines TEXT,
    report TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT
);
"""


class TaskStore:
    def __init__(self, config: AppConfig):
        db_dir = Path(config.tmp_dir)
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_dir / "tasks.db")
        self._lock = Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            conn.executescript(SCHEMA)
            conn.commit()
            conn.close()

    def create_task(self, params: dict) -> str:
        task_id = uuid.uuid4().hex[:12]
        now = datetime.utcnow().isoformat() + "Z"
        steps = [
            {"step": 1, "name": "检索信息", "status": "pending"},
            {"step": 2, "name": "下载 PDF", "status": "pending"},
            {"step": 3, "name": "OCR PDF", "status": "pending"},
            {"step": 3.5, "name": "PDF 压缩", "status": "pending"},
            {"step": 4, "name": "生成书签", "status": "pending"},
            {"step": 5, "name": "保存到本地", "status": "pending"},
            {"step": 6, "name": "生成报告", "status": "pending"},
        ]
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO tasks (task_id, status, params, steps, log_lines, created_at, updated_at)
                   VALUES (?, 'pending', ?, ?, '[]', ?, ?)""",
                (task_id, json.dumps(params), json.dumps(steps), now, now),
            )
            conn.commit()
            conn.close()
        return task_id

    def get_task(self, task_id: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_dict(row)

    def update_status(self, task_id: str, status: str, current_step: int = None,
                      current_step_name: str = None, error: str = None):
        now = datetime.utcnow().isoformat() + "Z"
        fields = ["status = ?", "updated_at = ?"]
        values = [status, now]
        if current_step is not None:
            fields.append("current_step = ?")
            values.append(current_step)
        if current_step_name:
            fields.append("current_step_name = ?")
            values.append(current_step_name)
        if error:
            fields.append("error = ?")
            values.append(error)
        values.append(task_id)
        with self._lock:
            conn = self._get_conn()
            conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE task_id = ?", values)
            conn.commit()
            conn.close()

    def update_step(self, task_id: str, step_num: float, step_name: str, step_status: str,
                    elapsed_ms: int = None, progress_pct: int = None):
        task = self.get_task(task_id)
        if not task:
            return
        steps = json.loads(task["steps"]) if isinstance(task.get("steps"), str) else task["steps"]
        for s in steps:
            if s["step"] == step_num:
                s["status"] = step_status
                if elapsed_ms is not None:
                    s["elapsed_ms"] = elapsed_ms
                if progress_pct is not None:
                    s["progress_pct"] = progress_pct
                break
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET steps = ?, current_step = ?, current_step_name = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(steps), step_num, step_name, now, task_id),
            )
            conn.commit()
            conn.close()

    def append_log(self, task_id: str, message: str):
        task = self.get_task(task_id)
        if not task:
            return
        logs = json.loads(task["log_lines"]) if isinstance(task.get("log_lines"), str) else task["log_lines"]
        if logs is None:
            logs = []
        logs.append(message)
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET log_lines = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(logs), now, task_id),
            )
            conn.commit()
            conn.close()

    def save_pipeline_state(self, task_id: str, state: dict):
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET pipeline_state = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(state, default=str), now, task_id),
            )
            conn.commit()
            conn.close()

    def save_report(self, task_id: str, report: dict):
        now = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "UPDATE tasks SET report = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(report, default=str), now, task_id),
            )
            conn.commit()
            conn.close()

    def list_tasks(self, limit: int = 50) -> list:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT task_id, status, current_step, current_step_name, params, created_at, updated_at "
            "FROM tasks ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            deleted = conn.total_changes > 0
            conn.commit()
            conn.close()
        return deleted

    def delete_completed_tasks(self) -> int:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM tasks WHERE status IN ('completed', 'failed')")
            count = conn.total_changes
            conn.commit()
            conn.close()
        return count

    def delete_all_tasks(self) -> int:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM tasks")
            count = conn.total_changes
            conn.commit()
            conn.close()
        return count

    def _row_to_dict(self, row) -> dict:
        d = dict(row)
        for field in ["steps", "log_lines", "report", "pipeline_state", "params"]:
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
