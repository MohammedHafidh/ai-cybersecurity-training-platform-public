"""Allowlisted local Docker adapter. Student data never becomes execution arguments."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "docs/training-lab-manifest.json"
PAIRS = {"brute-force": ("auth-target", "auth-client"), "sql-injection": ("sql-target", "web-client"), "reconnaissance": ("recon-target", "recon-client")}


def data_root():
    return Path(os.environ.get("CAPSTONE_TRAINING_HOME", Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "CapstoneTraining")).resolve()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_bundle():
    config = json.loads((data_root() / "operator.json").read_text(encoding="utf-8"))
    root = Path(config["lab_root"]).resolve()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or digest(path) != expected:
            raise ValueError("Approved private lab bundle differs from the reviewed manifest")
    return root, digest(MANIFEST)


def command(args, *, input=None, timeout=60, cancel=None):
    """Bounded child; logs remain private. No shell, arbitrary command strings or output reflection."""
    import tempfile
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(args, stdin=subprocess.PIPE if input else subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        if input:
            process.stdin.write(input); process.stdin.close()
        started = time.monotonic()
        try:
            while process.poll() is None:
                if cancel and cancel.is_set(): raise InterruptedError("Exercise cancelled")
                if time.monotonic() - started > timeout: raise TimeoutError("Approved operation timed out")
                if stdout.tell() + stderr.tell() > 2_000_000: raise ValueError("Operation output limit exceeded")
                time.sleep(.1)
            if process.returncode: raise RuntimeError("Approved Docker operation failed; check operator readiness")
            stdout.seek(0); output = stdout.read(2_000_001)
            if len(output) > 2_000_000: raise ValueError("Operation output limit exceeded")
            return output
        finally:
            if process.poll() is None: process.kill()
            process.wait()


def image(service, signature):
    return f"capstone-training-{service}:{signature[:16]}"


def prepare_images():
    root, signature = verified_bundle()
    for service in ("auth-target", "auth-client", "sql-target", "web-client", "recon-target", "recon-client"):
        context = root if service in ("web-client", "recon-client") else root / service
        command(["docker", "build", "--label", f"capstone.approved={signature}", "-t", image(service, signature), "-f", str(root / service / "Dockerfile"), str(context)], timeout=300)


def readiness():
    try:
        _, signature = verified_bundle()
        command(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=8)
        for service in (s for pair in PAIRS.values() for s in pair):
            info = json.loads(command(["docker", "image", "inspect", image(service, signature)], timeout=8))[0]
            if info["Config"].get("Labels", {}).get("capstone.approved") != signature: raise ValueError("Image approval mismatch")
        return {"ready": True, "message": "Approved isolated lab is ready."}
    except (OSError, ValueError, KeyError, RuntimeError, TimeoutError):
        return {"ready": False, "message": "The approved local lab is not ready. Ask the operator to run platform setup. No exercise has started."}


def utc():
    return datetime.now(timezone.utc)


def project_name(exercise):
    if not re.fullmatch(r"[a-f0-9]{32}", exercise): raise ValueError("Invalid server exercise identity")
    return "capstone-training-" + exercise


def validate_isolation(containers, network, exercise):
    if len(containers) != 2 or not network.get("Internal") or len(network.get("Containers", {})) != 2:
        raise ValueError("Expected two containers on one internal network")
    attachments = set()
    for container in containers:
        host = container["HostConfig"]
        labels = container["Config"].get("Labels", {})
        if labels.get("capstone.exercise") != exercise or labels.get("com.docker.compose.project") != project_name(exercise):
            raise ValueError("Unexpected container ownership")
        if host.get("PortBindings") or host.get("Privileged") or host.get("Binds") or host.get("NetworkMode") == "host":
            raise ValueError("Unsafe container configuration")
        nets = container["NetworkSettings"]["Networks"]
        if len(nets) != 1: raise ValueError("Unexpected network attachment")
        attachments.update(nets)
    if len(attachments) != 1 or network.get("Name") not in attachments:
        raise ValueError("Unexpected network topology")


def cleanup(exercise):
    project = project_name(exercise)
    # Scope comes from a server-generated ID, never a request-supplied project name.
    ids = command(["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"], timeout=10).decode().split()
    if ids: command(["docker", "rm", "-f", *ids], timeout=20)
    nets = command(["docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"], timeout=10).decode().split()
    if nets: command(["docker", "network", "rm", *nets], timeout=20)


def capture(exercise, scenario, stage, cancel):
    root, signature = verified_bundle()
    target, client = PAIRS[scenario]
    folder = data_root() / "evidence" / exercise
    folder.mkdir(parents=True, exist_ok=False)
    run_id = "training-" + exercise
    compose = {"services": {s: {"image": image(s, signature), "networks": ["lab"], "restart": "no", "labels": {"capstone.exercise": exercise}, **({"command": ["sh", "-c", "sleep infinity"]} if s == client else {})} for s in (target, client)}, "networks": {"lab": {"internal": True}}}
    if scenario == "reconnaissance": compose["services"][target]["environment"] = {"LAB_RUN_ID": run_id}
    file = folder / "compose.json"; file.write_text(json.dumps(compose), encoding="utf-8")
    base = ["docker", "compose", "-f", str(file), "-p", project_name(exercise)]
    def run(*args, **kwargs): return command([*base, *args], cancel=cancel, **kwargs)
    try:
        stage("starting")
        run("up", "-d", "--no-build", "--pull", "never", timeout=45)
        ids = run("ps", "-q").decode().split()
        if len(ids) != 2: raise ValueError("Expected exactly two owned lab containers")
        inspected = json.loads(command(["docker", "inspect", *ids], timeout=10))
        networks = set()
        for container in inspected:
            host = container["HostConfig"]
            if host.get("PortBindings") or host.get("Privileged") or host.get("Binds") or host.get("NetworkMode") == "host": raise ValueError("Unsafe container configuration")
            nets = container["NetworkSettings"]["Networks"]
            if len(nets) != 1: raise ValueError("Unexpected network attachment")
            networks.update(nets)
        if len(networks) != 1: raise ValueError("Unexpected lab topology")
        net = json.loads(command(["docker", "network", "inspect", *networks], timeout=10))[0]
        validate_isolation(inspected, net, exercise)
        for _ in range(40):
            logs = run("logs", "--no-color", target).lower()
            if b"listening" in logs or b"server_start" in logs: break
            time.sleep(.2)
        else: raise TimeoutError("Target did not become ready")
        # Record the controlled activity window after target startup; never choose based on predictions.
        start = utc(); stage("activity")
        if scenario == "brute-force":
            run("exec", "-T", client, "sh", "-s", "--", "1", input=(root / "scripts/run-bruteforce-auth.sh").read_bytes().replace(b"\r\n", b"\n"), timeout=45)
        elif scenario == "sql-injection":
            run("exec", "-T", client, "/usr/local/bin/run-sql-requests", "malicious", run_id, "1", timeout=20)
        else:
            run("exec", "-T", client, "/usr/local/bin/run-recon-scan", "1", timeout=25)
            # The target logs after its bounded receive timeout; allow that real log to complete.
            time.sleep(1.3)
        end = utc(); stage("capturing")
        raw = run("logs", "--timestamps", "--no-color", target)
        log = folder / "capture.log"; log.write_bytes(raw)
        if scenario == "reconnaissance":
            for name in ("nmap-scan.txt", "nmap-scan.xml"):
                run("cp", f"{client}:/tmp/day6-recon/{name}", str(folder / name))
        metadata = {"run_id": run_id, "scenario": {"brute-force":"brute_force", "sql-injection":"sql_injection", "reconnaissance":"reconnaissance"}[scenario], "expected_label":"malicious", "start_time":start.isoformat(), "end_time":end.isoformat(), "source":client, "target":target, "tool_or_method":"Approved isolated controlled activity, variant 1", "log_sources":["capture.log"], "notes":"Fresh live controlled exercise; label assigned by collection protocol before detection."}
        (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return folder, metadata
    finally:
        cleanup(exercise)
