"""Run with a bundled Python: python3 macos/test_desktop.py [app-code-root]."""
import http.cookiejar
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import desktop

CODE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
if (CODE.parent / "desktop.py").is_file():
    import importlib.util
    spec = importlib.util.spec_from_file_location("desktop", CODE.parent / "desktop.py")
    desktop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(desktop)


def start(data):
    proc = subprocess.Popen([sys.executable, "-I", "-B", str(Path(desktop.__file__).resolve()),
                             "--code", str(CODE), "--data", str(data), "--parent", str(os.getpid())],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    try:
        assert sel.select(95), "Startup timed out"
        event = json.loads(proc.stdout.readline())
        assert event["event"] == "ready", event
        return proc, event["url"]
    except BaseException:
        proc.terminate()
        proc.wait(timeout=45)
        raise
    finally:
        sel.close()


def finish(proc, data):
    workers = json.loads((data / "state/desktop-processes.json").read_text())["workers"]
    descendants = subprocess.check_output(["ps", "-axo", "pid=,pgid="], text=True)
    pids = [int(row.split()[0]) for row in descendants.splitlines() if int(row.split()[1]) in workers]
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=45) == 0, "Unclean shutdown"
    deadline = time.monotonic() + 3
    for pid in pids:
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            raise AssertionError(f"Service {pid} survived shutdown")


def main():
    with tempfile.TemporaryDirectory(prefix="tj_mac_check_") as tmp:
        data = Path(tmp) / "Private Journal"
        desktop.prepare(CODE, data)
        config = json.loads((data / "config.json").read_text())
        config["desktop_test"] = "preserve me"
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0)); occupied.listen()
            config["web"]["port"] = occupied.getsockname()[1]
            desktop.write_json(data / "config.json", config)
            port = desktop.prepare(CODE, data)
            assert port != config["web"]["port"], "Occupied port was reused"
        assert (data / "config.json").stat().st_mode & 0o777 == 0o600
        assert data.stat().st_mode & 0o777 == 0o700
        assert (data / "web/v2/index.html").is_file(), "Bundled UI missing"
        assert json.loads((data / "config.json").read_text())["desktop_test"] == "preserve me"

        proc, url = start(data)
        try:
            duplicate = subprocess.run([sys.executable, "-I", "-B", str(Path(desktop.__file__).resolve()),
                                       "--code", str(CODE), "--data", str(data)], capture_output=True, text=True, timeout=5)
            assert duplicate.returncode == 1 and "already running" in duplicate.stdout
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                         urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            with opener.open(url + "/api/auth/status") as response:
                auth = json.load(response)
            assert auth["enabled"] and auth["canSetup"] and not auth["passwordSet"]
            code = (data / "state/auth_setup_code").read_text().strip()

            def post(setup_code):
                request = urllib.request.Request(url + "/api/auth/setup",
                          data=json.dumps({"password": "Test-Journal-2026-Local", "code": setup_code}).encode(),
                          headers={"Content-Type": "application/json", "Origin": url})
                return opener.open(request)

            try:
                post("WRONG-CODE")
                raise AssertionError("Wrong setup code was accepted")
            except urllib.error.HTTPError as error:
                assert error.code == 403
            with post(code) as response:
                assert json.load(response)["ok"]
            with opener.open(url + "/api/auth/status") as response:
                assert json.load(response)["authed"]
            for path, expected in (("/", b"<html"), ("/v2/setup.js", b"")):
                with opener.open(url + path) as response:
                    body = response.read()
                    assert response.status == 200 and len(body) > 100
                    assert expected in body
            assert (data / "state/ledger.db").exists(), "Journal was not initialized"
        finally:
            finish(proc, data)
        auth_before = (data / "state/auth.json").read_bytes()
        proc, url = start(data)
        try:
            assert (data / "state/auth.json").read_bytes() == auth_before, "Saved password changed"
            assert json.loads((data / "config.json").read_text())["desktop_test"] == "preserve me"
            reset = subprocess.run([sys.executable, "-E", "-B", str(CODE / "tools/reset_password.py"), "-y"],
                                   env=dict(os.environ, TJ_BASE=str(data)), capture_output=True, timeout=10)
            assert reset.returncode == 0, reset.stderr
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url + "/api/auth/status") as response:
                auth = json.load(response)
            assert auth["canSetup"] and not auth["passwordSet"], "Password reset did not take effect"
            assert (data / "state/ledger.db").exists(), "Password reset removed the journal"
        finally:
            finish(proc, data)
    print("PASS: first launch, occupied port, private permissions, duplicate guard, authentication, UI assets, persistence, password reset and complete shutdown")


if __name__ == "__main__":
    main()
