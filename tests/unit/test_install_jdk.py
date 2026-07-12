import io
import tarfile

import pytest

from scripts.install_jdk import _safe_extract


def test_safe_extract_rejects_parent_traversal(tmp_path):
    archive_path = tmp_path / "traversal.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("../escape.txt")
        payload = b"blocked"
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with tarfile.open(archive_path, "r:gz") as archive:
        with pytest.raises(RuntimeError, match="Unsafe path"):
            _safe_extract(archive, tmp_path / "extract")


def test_safe_extract_rejects_escaping_symlink(tmp_path):
    archive_path = tmp_path / "symlink.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("jdk/bin/java")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../../outside"
        archive.addfile(member)

    destination = tmp_path / "extract"
    destination.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        with pytest.raises(RuntimeError, match="Unsafe symlink"):
            _safe_extract(archive, destination)

