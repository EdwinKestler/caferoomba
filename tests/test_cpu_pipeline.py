from pathlib import Path

from caferoomba.control.adapters.dry_run import DryRunAdapter
from caferoomba.control.intents import intent_from_policy
from caferoomba.data.fixtures import build_synthetic_clips
from caferoomba.deployment.export_onnx import export_onnx
from caferoomba.deployment.inference import OnboardPolicy
from caferoomba.learning.dataset import load_clip_stack
from caferoomba.learning.evaluate import evaluate_clips
from caferoomba.learning.train import load_checkpoint, train_steps
from caferoomba.teacher.cosmos import annotate


def test_cpu_fixture_train_export_replay(tmp_path):
    clips = build_synthetic_clips(tmp_path / "frames")
    notes = [annotate(clip, backend="mock") for clip in clips]
    assert all(item.is_mock for item in notes)
    report = train_steps(clips, output_dir=tmp_path / "train", steps=1, device="cpu")
    assert Path(report["checkpoint"]).is_file()
    assert report["is_synthetic"] is True
    model = load_checkpoint(Path(report["checkpoint"]))
    metrics = evaluate_clips(model, clips, image_size=64)
    assert metrics["n"] == len(clips)
    assert metrics["is_synthetic"] is True
    exported = export_onnx(Path(report["checkpoint"]), tmp_path / "student.onnx")
    assert exported["agrees"] is True
    policy = OnboardPolicy(Path(exported["onnx"]))
    frames = load_clip_stack(clips[0], size=64)[None, ...]
    prediction = policy.predict(frames)
    assert prediction["requires_cosmos"] is False
    assert prediction["requires_cloud"] is False
    intent = intent_from_policy(
        action=prediction["action_label"], now_ms=0, turn180_score=prediction["turn180_score"]
    )
    decision = DryRunAdapter().apply(intent, now_ms=0, observation_age_ms=5)
    assert decision.fail_closed is True
