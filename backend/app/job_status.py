import threading

_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def start_job(name: str) -> None:
    with _lock:
        _jobs[name] = {"status": "running", "result": None}


def finish_job(name: str, result: dict) -> None:
    with _lock:
        _jobs[name] = {"status": "done", "result": result}


def fail_job(name: str, error: str) -> None:
    with _lock:
        _jobs[name] = {"status": "error", "result": {"error": error}}


def get_job(name: str) -> dict:
    with _lock:
        return _jobs.get(name, {"status": "idle", "result": None})


def is_running(name: str) -> bool:
    with _lock:
        return _jobs.get(name, {}).get("status") == "running"
