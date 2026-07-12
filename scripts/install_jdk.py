#!/usr/bin/env python3
"""Install a checksum-verified project-local Temurin JDK 17."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / ".tools"
INSTALL_DIR = TOOLS_DIR / "jdk-17"
JAVA_HOME_FILE = TOOLS_DIR / "java_home"
API_URL = "https://api.adoptium.net/v3/assets/latest/17/hotspot"


def _architecture() -> str:
    machine = platform.machine().lower()
    mapping = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x64", "amd64": "x64"}
    try:
        return mapping[machine]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported macOS architecture: {machine}") from exc


def _request_json(url: str) -> list[dict[str, object]]:
    request = urllib.request.Request(url, headers={"User-Agent": "ecommerce-dataops-bootstrap/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "ecommerce-dataops-bootstrap/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        resolved = (destination / member.name).resolve()
        if resolved != root and root not in resolved.parents:
            raise RuntimeError(f"Unsafe path in JDK archive: {member.name}")
        if member.isdev() or member.isfifo():
            raise RuntimeError(f"Unsupported special file in JDK archive: {member.name}")
        if member.issym():
            link_target = (resolved.parent / member.linkname).resolve()
            if link_target != root and root not in link_target.parents:
                raise RuntimeError(f"Unsafe symlink in JDK archive: {member.name} -> {member.linkname}")
        if member.islnk():
            link_target = (destination / member.linkname).resolve()
            if link_target != root and root not in link_target.parents:
                raise RuntimeError(f"Unsafe hardlink in JDK archive: {member.name} -> {member.linkname}")
    archive.extractall(destination)


def _existing_java_home() -> Path | None:
    if not JAVA_HOME_FILE.exists():
        return None
    candidate = Path(JAVA_HOME_FILE.read_text(encoding="utf-8").strip())
    return candidate if (candidate / "bin" / "java").exists() else None


def main() -> None:
    existing = _existing_java_home()
    if existing:
        print(existing)
        return

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode(
        {
            "architecture": _architecture(),
            "heap_size": "normal",
            "image_type": "jdk",
            "os": "mac",
            "page_size": 1,
            "project": "jdk",
            "release_type": "ga",
            "vendor": "eclipse",
        }
    )
    assets = _request_json(f"{API_URL}?{query}")
    if not assets:
        raise RuntimeError("Adoptium returned no matching JDK 17 asset")

    package = assets[0]["binary"]["package"]  # type: ignore[index]
    download_url = str(package["link"])  # type: ignore[index]
    expected_checksum = str(package["checksum"]).lower()  # type: ignore[index]

    with tempfile.TemporaryDirectory(prefix="ecommerce-jdk-") as tmp:
        tmp_path = Path(tmp)
        archive_path = tmp_path / "temurin17.tar.gz"
        extract_path = tmp_path / "extract"
        extract_path.mkdir()
        print("Downloading checksum-verified Temurin JDK 17...", flush=True)
        _download(download_url, archive_path)
        actual_checksum = _sha256(archive_path)
        if actual_checksum != expected_checksum:
            raise RuntimeError(
                f"JDK checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
            )
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, extract_path)

        candidates = sorted(extract_path.glob("**/Contents/Home/bin/java"))
        if not candidates:
            candidates = sorted(extract_path.glob("**/bin/java"))
        if not candidates:
            raise RuntimeError("Downloaded JDK archive did not contain bin/java")
        extracted_home = candidates[0].parent.parent
        if INSTALL_DIR.exists():
            shutil.rmtree(INSTALL_DIR)
        shutil.copytree(extracted_home, INSTALL_DIR, symlinks=True)

    JAVA_HOME_FILE.write_text(str(INSTALL_DIR.resolve()), encoding="utf-8")
    os.chmod(INSTALL_DIR / "bin" / "java", 0o755)
    print(INSTALL_DIR.resolve())


if __name__ == "__main__":
    main()
