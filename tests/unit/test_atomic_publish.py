import json
import os
from pathlib import Path
import shutil

import pytest

from ecommerce_dataops.pipeline import _atomic_publish, _sync_committed_run_manifest
from ecommerce_dataops.settings import RunPaths


def test_atomic_publish_replaces_current_only_with_complete_candidate(tmp_path):
    paths = RunPaths(tmp_path, "run-001")
    paths.create()
    paths.current_dir.mkdir(parents=True)
    (paths.current_dir / "old.csv").write_text("last-good", encoding="utf-8")
    (paths.export_dir / "new.csv").write_text("candidate", encoding="utf-8")
    manifest = {"status": "success", "published": False}

    _atomic_publish(paths, manifest)

    assert paths.current_dir.is_symlink()
    assert not (paths.current_dir / "old.csv").exists()
    assert (paths.current_dir / "new.csv").read_text(encoding="utf-8") == "candidate"
    assert json.loads((paths.current_dir / "manifest.json").read_text(encoding="utf-8"))["status"] == "success"
    assert json.loads((paths.current_dir / "manifest.json").read_text(encoding="utf-8"))["published"] is True


def test_atomic_pointer_failure_preserves_previous_release(tmp_path, monkeypatch):
    first = RunPaths(tmp_path, "run-001")
    first.create()
    (first.export_dir / "version.csv").write_text("last-good", encoding="utf-8")
    _atomic_publish(first, {"status": "success", "published": False})
    previous_target = os.readlink(first.current_dir)

    second = RunPaths(tmp_path, "run-002")
    second.create()
    (second.export_dir / "version.csv").write_text("candidate", encoding="utf-8")
    real_replace = os.replace

    def fail_pointer_switch(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if source_path.name.startswith(".current-link-") and destination_path == second.current_dir:
            raise OSError("simulated pointer switch failure")
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_pointer_switch)
    with pytest.raises(OSError, match="pointer switch failure"):
        _atomic_publish(second, {"status": "success", "published": False})

    assert second.current_dir.is_symlink()
    assert os.readlink(second.current_dir) == previous_target
    assert (second.current_dir / "version.csv").read_text(encoding="utf-8") == "last-good"
    assert not (tmp_path / "bi_exports" / "releases" / "run-002").exists()


def test_post_commit_legacy_cleanup_failure_does_not_flip_publication(tmp_path, monkeypatch):
    paths = RunPaths(tmp_path, "run-001")
    paths.create()
    paths.current_dir.mkdir(parents=True)
    (paths.current_dir / "old.csv").write_text("last-good", encoding="utf-8")
    (paths.export_dir / "new.csv").write_text("candidate", encoding="utf-8")
    real_rmtree = shutil.rmtree

    def fail_legacy_cleanup(path, *args, **kwargs):
        if Path(path).name.startswith("_legacy-"):
            raise OSError("simulated best-effort cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr("ecommerce_dataops.pipeline.shutil.rmtree", fail_legacy_cleanup)
    _atomic_publish(paths, {"status": "success", "published": False})

    assert paths.current_dir.is_symlink()
    assert (paths.current_dir / "new.csv").read_text(encoding="utf-8") == "candidate"


def test_committed_run_manifest_sync_failure_is_non_blocking(tmp_path, monkeypatch):
    paths = RunPaths(tmp_path, "run-001")
    paths.create()
    manifest = {"status": "success", "published": True}

    def fail_secondary_manifest(*_args, **_kwargs):
        raise OSError("simulated run-artifact sync failure")

    monkeypatch.setattr("ecommerce_dataops.pipeline._write_json", fail_secondary_manifest)
    _sync_committed_run_manifest(paths, manifest)

    assert manifest["status"] == "success"
    assert manifest["published"] is True
    assert "sync failure" in manifest["run_manifest_sync_warning"]
