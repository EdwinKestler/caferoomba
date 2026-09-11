"""Real CafeRoomba commands. Placeholders that only print success are forbidden."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from caferoomba.schemas import EvidenceState, RunManifest

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@app.command()
def doctor(json_out: Optional[Path] = typer.Option(None, "--json-out")) -> None:
    from caferoomba.environment import report

    payload = report()
    typer.echo(json.dumps(payload, indent=2))
    if json_out:
        _write_manifest(json_out, payload)


@app.command("demo-fixture")
def demo_fixture(
    workdir: Path = typer.Option(Path("artifacts/cpu-smoke"), "--workdir"),
    steps: int = typer.Option(2, "--steps"),
) -> None:
    """CPU-only vertical slice on synthetic fixtures. Not Cosmos/cloud/Jetson evidence."""
    from caferoomba.control.adapters.dry_run import DryRunAdapter
    from caferoomba.control.intents import intent_from_policy
    from caferoomba.data.fixtures import build_synthetic_clips
    from caferoomba.deployment.export_onnx import export_onnx
    from caferoomba.deployment.inference import OnboardPolicy
    from caferoomba.learning.dataset import load_clip_stack
    from caferoomba.learning.evaluate import evaluate_clips
    from caferoomba.learning.train import load_checkpoint, train_steps
    from caferoomba.teacher.cosmos import annotate

    clips = build_synthetic_clips(workdir / "frames")
    teacher = [annotate(clip, backend="mock").model_dump() for clip in clips]
    if any(not item["is_mock"] for item in teacher):
        raise typer.Exit("mock teacher produced is_mock=false")
    train_report = train_steps(clips, output_dir=workdir / "train", steps=steps, device="cpu")
    model = load_checkpoint(Path(train_report["checkpoint"]))
    metrics = evaluate_clips(model, clips, image_size=64)
    export_report = export_onnx(Path(train_report["checkpoint"]), workdir / "student.onnx")
    policy = OnboardPolicy(Path(export_report["onnx"]))
    stack = load_clip_stack(clips[0], size=64)[None, ...]
    prediction = policy.predict(stack)
    intent = intent_from_policy(
        action=prediction["action_label"],
        now_ms=clips[0].source.decision_timestamp_ms,
        turn180_score=prediction["turn180_score"],
    )
    adapter = DryRunAdapter()
    decision = adapter.apply(
        intent,
        now_ms=intent.issued_at_ms,
        observation_age_ms=10,
        heartbeat_ok=True,
    )
    manifest = RunManifest(
        kind="cpu_smoke",
        is_synthetic=True,
        evidence_state=EvidenceState.tested_offline,
        command="caferoomba demo-fixture",
        extras={
            "train": train_report,
            "metrics": metrics,
            "export": export_report,
            "prediction": {
                "action": prediction["action"],
                "requires_cosmos": prediction["requires_cosmos"],
            },
            "safety": decision.model_dump(),
            "teacher_mock_count": len(teacher),
            "disclaimer": "SYNTHETIC FIXTURE — not Cosmos, Colab, Jetson, or robot performance",
        },
    )
    out = workdir / "manifest.json"
    _write_manifest(out, json.loads(manifest.model_dump_json()))
    typer.echo(json.dumps({"manifest": str(out), "synthetic": True, "ok": True}, indent=2))


@app.command()
def preflight(
    config: Path = typer.Option(Path("config/companion.yaml"), "--config"),
    camera: Optional[str] = typer.Option(None, "--camera", help="fake | realsense | imx219"),
    vehicle: Optional[str] = typer.Option(None, "--vehicle", help="dry-run"),
) -> None:
    """Check companion config. Does not open Cube serial or arm."""
    from caferoomba.app.config import load_config
    from caferoomba.app.loop import apply_overrides, build_camera, build_vehicle

    cfg = apply_overrides(load_config(config), camera=camera, vehicle=vehicle)
    payload = {
        "python": str(Path(__import__("sys").executable)),
        "camera": cfg.camera.backend,
        "vehicle": cfg.vehicle.backend,
        "allow_commands": cfg.vehicle.allow_commands,
        "fence_required": cfg.fence.required,
        "onnx": cfg.policy.onnx_path,
        "ok": True,
        "camera_open": False,
    }
    cam = None
    try:
        build_vehicle(cfg)
        cam = build_camera(cfg)
        cam.open()
        sample = cam.read()
        payload["camera_open"] = True
        payload["frame_shape"] = list(sample.color.shape)
        payload["has_depth"] = sample.depth is not None
    except Exception as exc:
        payload["ok"] = False
        payload["error"] = str(exc)
        raise typer.Exit(code=1) from None
    finally:
        if cam is not None:
            try:
                cam.close()
            except Exception:
                pass
        typer.echo(json.dumps(payload, indent=2))


@app.command("run-companion")
def run_companion(
    config: Path = typer.Option(Path("config/companion.yaml"), "--config"),
    camera: Optional[str] = typer.Option(None, "--camera"),
    vehicle: Optional[str] = typer.Option(None, "--vehicle"),
    cycles: int = typer.Option(12, "--cycles"),
) -> None:
    """Mission loop. Default dry-run. Never arms. Not Jetson evidence."""
    from caferoomba.app.config import load_config
    from caferoomba.app.loop import CompanionLoop, apply_overrides

    cfg = apply_overrides(load_config(config), camera=camera, vehicle=vehicle)
    rows = CompanionLoop(cfg).run(cycles=cycles)
    typer.echo(
        json.dumps(
            {
                "cycles": len(rows),
                "final_state": rows[-1]["state"] if rows else None,
                "states": [row["state"] for row in rows],
                "armed": False,
                "vehicle": cfg.vehicle.backend,
                "camera": cfg.camera.backend,
                "ok": True,
            },
            indent=2,
        )
    )
