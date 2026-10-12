"""Own the existing tj-bot services for the lifetime of the Mac window."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

UNITS = ("core", "web", "evm", "sol", "bsc", "tron", "sui", "ton", "btc")
DIRECT = ("upbit_link.py", "ex_foreign.py", "alert_bot.py")


def emit(event, **values):
    print(json.dumps(dict(event=event, **values)), flush=True)


def write_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.chmod(0o600)
    tmp.replace(path)


def prepare(code, data):
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    data.chmod(0o700)
    (data / "state").mkdir(exist_ok=True, mode=0o700)
    (data / "state").chmod(0o700)
    # Reuse upstream's single base directory, keeping its writable files outside the app.
    for name in ("src", "web", "seed", "tools", "VERSION"):
        link = data / name
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            raise RuntimeError(f"Please move the existing '{name}' out of the app data folder and reopen the app.")
        link.symlink_to(code / name, target_is_directory=(code / name).is_dir())
    config_path = data / "config.json"
    if not config_path.exists():
        config_path.write_bytes((code / "config.example.json").read_bytes())
    config_path.chmod(0o600)
    env_path = data / ".env"
    if not env_path.exists():
        env_path.write_bytes((code / ".env.example").read_bytes())
    env_path.chmod(0o600)
    config = json.loads(config_path.read_text())
    web = config.setdefault("web", {})
    port = web.get("port", 8023)
    if not isinstance(port, int) or isinstance(port, bool) or not 0 < port < 65536:
        raise RuntimeError("The saved web port is invalid. Restore config.json from a backup in the app data folder.")
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
    web["port"] = port
    web["bind"] = "loopback"
    write_json(config_path, config)
    return port


def stop(children):
    for proc in children:
        try:
            os.killpg(proc.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 35
    while any(proc.poll() is None for proc in children) and time.monotonic() < deadline:
        time.sleep(0.1)
    # Also clear descendants if their runner exited before they did.
    for proc in children:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--parent", type=int, default=os.getppid())
    args = parser.parse_args()
    os.umask(0o077)
    args.data.mkdir(parents=True, exist_ok=True, mode=0o700)
    children, logs = [], []
    lock = None
    stopping = False

    def request_stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        lock = (args.data / "desktop.lock").open("a")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Trading Journal is already running. Close the other copy, then reopen this app.")
        port = prepare(args.code.resolve(), args.data.resolve())
        env = dict(os.environ, TJ_BASE=str(args.data.resolve()), PYTHONUNBUFFERED="1",
                   PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        log_dir = args.data / "state" / "desktop-logs"
        log_dir.mkdir(exist_ok=True, mode=0o700)
        scripts = [(unit, ["src/unit_runner.py", unit]) for unit in UNITS]
        scripts += [(Path(script).stem, ["src/" + script]) for script in DIRECT]
        if env.get("TJ_ENABLE_REVIEW") == "1":
            scripts.append(("review", ["src/review_daily.py"]))
        for name, command in scripts:
            log = (log_dir / ("tj-" + name + ".log")).open("ab", buffering=0)
            logs.append(log)
            children.append(subprocess.Popen([sys.executable, "-E", "-B", *command],
                            cwd=args.data, env=env, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=log, start_new_session=True))
        write_json(args.data / "state" / "desktop-processes.json",
                   dict(supervisor=os.getpid(), workers=[p.pid for p in children], port=port))
        url = f"http://127.0.0.1:{port}"
        ready, start, rotated = False, time.monotonic(), 0
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while not stopping and os.getppid() == args.parent:
            for i, proc in enumerate(children):
                if proc.poll() is not None:
                    raise RuntimeError(f"The {scripts[i][0]} service stopped. Reopen the app; details are in Open Logs.")
            if not ready:
                try:
                    with opener.open(url + "/api/auth/status", timeout=1) as response:
                        status = json.load(response)
                    if status.get("ok") is True:
                        emit("ready", url=url)
                        ready = True
                except (OSError, ValueError):
                    if time.monotonic() - start > 90:
                        raise RuntimeError("The journal could not start. Reopen the app; details are in Open Logs.")
            if time.monotonic() - rotated > 60:
                subprocess.run(["/bin/bash", str(args.code / "tools/rotate_logs.sh"), str(log_dir)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                rotated = time.monotonic()
            time.sleep(0.4)
        stop(children)
        children.clear()
    except Exception as exc:
        emit("error", message=str(exc))
        return 1
    finally:
        stop(children)
        for log in logs:
            log.close()
        if lock is not None:
            lock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
