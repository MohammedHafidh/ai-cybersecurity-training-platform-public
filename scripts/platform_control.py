"""Windows-friendly operator lifecycle. Starting the platform never starts an exercise."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.training.lab import data_root, verified_bundle, prepare_images, readiness

DATABASE = (
    "postgresql+psycopg://capstone_training:local_training_only@127.0.0.1:55435/capstone_training"
)
STATE = data_root() / "platform.json"


def run(args, **kwargs):
    subprocess.run(args, check=True, cwd=kwargs.pop("cwd", ROOT), **kwargs)


def get(url, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers.update({"Origin": url, "X-Capstone-Token": token})
    request = Request(
        url + path,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
        method="GET" if body is None else "POST",
    )
    with urlopen(request, timeout=8) as response:
        return json.load(response)


def hidden(args, env, log):
    options = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=log, **options)


def ensure_docker():
    try:
        run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
        return
    except (subprocess.SubprocessError, OSError):
        pass
    binary = shutil.which("docker")
    desktop = Path(binary).parents[2] / "Docker Desktop.exe" if binary else Path("not-installed")
    if os.name == "nt" and desktop.is_file():
        with (data_root() / "docker-start.txt").open("a") as log:
            hidden([str(desktop)], os.environ.copy(), log)
        print("Starting Docker Desktop; waiting for its Linux engine…", flush=True)
        for _ in range(60):
            try:
                run(
                    ["docker", "info"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
                return
            except (subprocess.SubprocessError, OSError):
                time.sleep(2)
    raise RuntimeError(
        "Docker Linux engine is unavailable. Open Docker Desktop and wait until it is ready, then retry."
    )


def configure(args):
    folder = data_root()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "operator.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    if args.lab_root:
        previous["lab_root"] = str(Path(args.lab_root).resolve())
    previous["python"] = sys.executable
    if args.node:
        previous["node"] = str(Path(args.node).resolve())
    path.write_text(json.dumps(previous, indent=2), encoding="utf-8")
    verified_bundle()
    ensure_docker()
    prepare_images()
    print("Approved private lab prepared. No exercise was executed.")


def start(args):
    folder = data_root()
    folder.mkdir(parents=True, exist_ok=True)
    url = f"http://localhost:{args.port}"
    try:
        existing = get(url, "/training/session")
    except (URLError, ValueError, TimeoutError):
        existing = None
    if existing:
        if (
            STATE.exists()
            and json.loads(STATE.read_text()).get("instance")
            == hashlib.sha256(existing["token"].encode()).hexdigest()
        ):
            print("Platform already running: " + url)
            return
        raise RuntimeError(
            "The selected port is occupied by another platform. Choose another port; no process was stopped."
        )
    config = (
        json.loads((folder / "operator.json").read_text())
        if (folder / "operator.json").exists()
        else {}
    )
    node = args.node or config.get("node") or shutil.which("node")
    if not node:
        raise RuntimeError("Node.js 22 is required. Run setup with its executable path.")
    if not subprocess.check_output([node, "--version"], text=True).startswith("v22."):
        raise RuntimeError("Use Node.js 22; set -NodePath during operator setup.")
    env = dict(
        os.environ,
        DATABASE_URL=DATABASE,
        CAPSTONE_TRAINING_ENABLED="1",
        CAPSTONE_SERVE_FRONTEND="1",
        FRONTEND_ORIGIN=url,
        CAPSTONE_OLLAMA_ENABLED="1",
        HF_HOME=os.environ.get("HF_HOME", str(folder / "models")),
        OMP_NUM_THREADS="1",
    )
    env["PATH"] = (
        str(Path(node).parent)
        + os.pathsep
        + str(Path(sys.executable).parent)
        + os.pathsep
        + env.get("PATH", "")
    )
    ensure_docker()
    run(["docker", "compose", "-f", "compose.training.yml", "up", "-d", "--wait"])
    from app.persistence.core import setup_core_schema
    from app.persistence.database import build_engine
    from app.training.storage import setup_training

    engine = build_engine(DATABASE)
    try:
        setup_core_schema(engine)
        setup_training(engine)
    finally:
        engine.dispose()
    if args.prepare_lab:
        verified_bundle()
        prepare_images()
    print(readiness()["message"])
    try:
        get("http://127.0.0.1:11434", "/api/tags")
    except (URLError, ValueError, TimeoutError):
        ollama = shutil.which("ollama")
        if ollama:
            with (folder / "ollama.txt").open("a") as log:
                hidden([ollama, "serve"], env, log)
        else:
            print(
                "Ollama is unavailable. Lessons, detectors and the clearly labeled explanation fallback remain usable."
            )
    if not (ROOT / "frontend/node_modules").exists():
        run(["npm.cmd" if os.name == "nt" else "npm", "ci"], cwd=ROOT / "frontend", env=env)
    build_env = dict(env, VITE_API_BASE_URL=url)
    run(
        ["npm.cmd" if os.name == "nt" else "npm", "run", "build"],
        cwd=ROOT / "frontend",
        env=build_env,
    )
    with (folder / "platform.log").open("a", encoding="utf-8") as log:
        process = hidden(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                "backend",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
            ],
            env,
            log,
        )
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError(
                    "Backend startup failed. See the operator platform.log; no exercise has started."
                )
            try:
                session = get(url, "/training/session")
                get(url, "/health/database")
                break
            except (URLError, ValueError, TimeoutError):
                time.sleep(0.5)
        else:
            raise RuntimeError("Backend readiness timed out; inspect platform.log.")
    except Exception:
        process.terminate()
        process.wait()
        raise
    STATE.write_text(
        json.dumps(
            {
                "url": url,
                "pid": session["pid"],
                "instance": hashlib.sha256(session["token"].encode()).hexdigest(),
            },
            indent=2,
        )
    )
    print(
        "Platform ready: "
        + url
        + "\nNo attack was started. Students choose exercises in the browser."
    )
    if args.open:
        import webbrowser

        webbrowser.open(url)


def stop(args):
    if not STATE.exists():
        raise RuntimeError("No recorded platform instance. Nothing was stopped.")
    state = json.loads(STATE.read_text())
    url = state["url"]
    session = get(url, "/training/session")
    if (
        session["pid"] != state["pid"]
        or hashlib.sha256(session["token"].encode()).hexdigest() != state["instance"]
    ):
        raise RuntimeError("Instance identity differs; refusing to terminate an unrelated process.")
    get(url, "/training/cancel-all", {}, session["token"])
    for _ in range(90):
        if not get(url, "/training/active")["ids"]:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError(
            "Exercise cancellation has not completed. Platform left running to allow safe recovery."
        )
    os.kill(state["pid"], signal.SIGTERM)
    run(["docker", "compose", "-f", "compose.training.yml", "down"])
    STATE.unlink()
    print(
        "Platform stopped. Database volume, private evidence, Docker Desktop and Ollama were preserved."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["configure", "start", "stop"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--node")
    parser.add_argument("--lab-root")
    parser.add_argument("--prepare-lab", action="store_true")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a local unprivileged port")
    try:
        {"configure": configure, "start": start, "stop": stop}[args.action](args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit("Platform error: " + str(error)) from None
