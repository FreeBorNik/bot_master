"""Блокировка второго экземпляра bot_master (атомарная, Windows + Unix)."""
import os
import sys
from pathlib import Path
from typing import IO, TextIO

_LOCK_FILE = Path(__file__).resolve().parents[2] / "logs" / "bot_master.pid"
_lock_handle: TextIO | None = None


def _read_lock_pid() -> int | None:
    if not _LOCK_FILE.exists():
        return None
    try:
        return int(_LOCK_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _lock_file_handle(handle: IO[str]) -> None:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file_handle(handle: IO[str]) -> None:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def acquire_instance_lock() -> None:
    """Запретить запуск, если другой bot_master уже работает."""
    global _lock_handle

    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    old_pid = _read_lock_pid()

    handle = open(_LOCK_FILE, "a+", encoding="utf-8")
    try:
        _lock_file_handle(handle)
    except OSError:
        handle.close()
        if old_pid and _is_process_alive(old_pid):
            print(
                f"bot_master уже запущен (PID {old_pid}).\n"
                "Остановите предыдущий процесс перед новым запуском.\n"
                f"  Stop-Process -Id {old_pid} -Force",
                file=sys.stderr,
            )
        else:
            print(
                "bot_master уже запущен другим процессом.\n"
                "Проверьте: Get-CimInstance Win32_Process -Filter \"Name='python.exe'\"",
                file=sys.stderr,
            )
        sys.exit(1)

    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    _lock_handle = handle


def release_instance_lock() -> None:
    """Снять lock при остановке."""
    global _lock_handle

    if _lock_handle is None:
        return

    try:
        _unlock_file_handle(_lock_handle)
        _lock_handle.close()
    except OSError:
        pass
    finally:
        _lock_handle = None

    if _LOCK_FILE.exists():
        try:
            if int(_LOCK_FILE.read_text(encoding="utf-8").strip()) == os.getpid():
                _LOCK_FILE.unlink(missing_ok=True)
        except (ValueError, OSError):
            pass
