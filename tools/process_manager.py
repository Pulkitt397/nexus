import logging
import os
import signal
import subprocess
import sys

import psutil

logger = logging.getLogger("nexus.tools.process")


def process_list() -> str:
    """List running processes sorted by memory usage (top 20)."""
    try:
        procs = []
        for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "status"]):
            try:
                info = proc.info
                mem_mb = (info["memory_info"].rss / (1024 * 1024)) if info["memory_info"] else 0
                if mem_mb > 1:
                    procs.append((info["name"] or "?", info["pid"], mem_mb, info["status"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x[2], reverse=True)
        lines = [f"  {'PID':<7} {'Name':<25} {'Memory':<10} {'Status':<10}",
                 f"  {'---':<7} {'----':<25} {'------':<10} {'------':<10}"]
        for name, pid, mem, status in procs[:25]:
            lines.append(f"  {pid:<7} {name[:24]:<25} {mem:<10.0f}MB {status:<10}")
        return "Running processes (top 25 by memory):\n" + "\n".join(lines)
    except Exception as exc:
        return f"Failed to list processes: {exc}"


def process_kill(pid_or_name: str) -> str:
    """Kill a process by PID or name.

    Args:
        pid_or_name: Numeric PID or process name (e.g. '1234' or 'notepad.exe').
    """
    killed = 0
    try:
        if pid_or_name.isdigit():
            pid = int(pid_or_name)
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            proc.wait(timeout=5)
            logger.info("Killed process %d (%s)", pid, name)
            return f"Killed process {pid} ({name})."
        else:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pname = (proc.info["name"] or "").lower()
                    if pid_or_name.lower() in pname:
                        proc.terminate()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if killed == 0:
                return f"No running process found matching '{pid_or_name}'."
            return f"Terminated {killed} process(es) matching '{pid_or_name}'."
    except psutil.NoSuchProcess:
        return f"Process '{pid_or_name}' not found."
    except psutil.TimeoutExpired:
        return f"Process '{pid_or_name}' did not terminate in time. Try force_kill."
    except Exception as exc:
        return f"Failed to kill process: {exc}"


def process_force_kill(pid_or_name: str) -> str:
    """Force-kill a process by PID or name (SIGKILL equivalent on Windows).

    Args:
        pid_or_name: Numeric PID or process name.
    """
    killed = 0
    try:
        if pid_or_name.isdigit():
            pid = int(pid_or_name)
            proc = psutil.Process(pid)
            name = proc.name()
            proc.kill()
            logger.info("Force-killed process %d (%s)", pid, name)
            return f"Force-killed process {pid} ({name})."
        else:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pname = (proc.info["name"] or "").lower()
                    if pid_or_name.lower() in pname:
                        proc.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if killed == 0:
                return f"No process found matching '{pid_or_name}'."
            return f"Force-killed {killed} process(es)."
    except psutil.NoSuchProcess:
        return f"Process '{pid_or_name}' not found."
    except Exception as exc:
        return f"Failed to force-kill: {exc}"


def process_start(path: str) -> str:
    """Start a new process.

    Args:
        path: Path to executable, or a system command (e.g. 'notepad.exe', 'C:\\Path\\to\\app.exe').
    """
    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        logger.info("Started process: %s", path)
        return f"Started: {path}."
    except FileNotFoundError:
        return f"Executable not found: {path}"
    except Exception as exc:
        return f"Failed to start process: {exc}"


def process_info(pid: int) -> str:
    """Get detailed information about a running process.

    Args:
        pid: Process ID number.
    """
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            name = proc.name()
            status = proc.status()
            cpu = proc.cpu_percent(interval=0.1)
            mem = proc.memory_info().rss / (1024 * 1024)
            create_time = proc.create_time()
            num_threads = proc.num_threads()
            exe = proc.exe()
        import datetime
        created = datetime.datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"Process {pid}:\n"
            f"  Name: {name}\n"
            f"  Status: {status}\n"
            f"  CPU: {cpu:.1f}%\n"
            f"  Memory: {mem:.0f} MB\n"
            f"  Threads: {num_threads}\n"
            f"  Started: {created}\n"
            f"  Path: {exe}"
        )
    except psutil.NoSuchProcess:
        return f"Process {pid} not found."
    except Exception as exc:
        return f"Failed to get process info: {exc}"


def process_wait(name: str, timeout: int = 30) -> str:
    """Wait for a process to start or exit.

    Args:
        name: Process name to watch for (e.g. 'notepad.exe').
        timeout: Maximum seconds to wait.
    """
    name_lower = name.lower()
    start = __import__("time").time()
    try:
        while (__import__("time").time() - start) < timeout:
            for proc in psutil.process_iter(["name"]):
                try:
                    if (proc.info["name"] or "").lower() == name_lower:
                        return f"Process '{name}' is now running."
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            __import__("time").sleep(0.5)
        return f"Timed out waiting for '{name}' to start."
    except Exception as exc:
        return f"Error waiting for process: {exc}"
