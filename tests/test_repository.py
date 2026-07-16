from __future__ import annotations

import io
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from fencepost.repository import (
    RepositoryError,
    blame_file,
    extract_archive,
    is_test_path,
    load_source_files,
    resolve_commit,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "path",
    (
        "conftest.py",
        "package/conftest.py",
        "test/helpers.py",
        "package/test/helpers.py",
        "tests/helpers.py",
        "test_module.py",
        "module_test.py",
    ),
)
def test_test_paths_are_never_loaded_as_production_source(path: str) -> None:
    assert is_test_path(path)


@pytest.mark.parametrize(
    "path", ("contest/module.py", "package/latest_module.py", "production.py")
)
def test_production_paths_are_not_mistaken_for_tests(path: str) -> None:
    assert not is_test_path(path)


def test_extract_archive_rejects_symlink_traversal(tmp_path: Path, monkeypatch) -> None:
    outside = tmp_path / "outside"
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = str(outside)
        archive.addfile(link)

        payload = b"forged\n"
        through_link = tarfile.TarInfo("link/result.json")
        through_link.size = len(payload)
        archive.addfile(through_link, io.BytesIO(payload))

    monkeypatch.setattr(
        "fencepost.repository._git",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=archive_bytes.getvalue(), stderr=b""
        ),
    )

    with pytest.raises(RepositoryError, match="links are not allowed"):
        extract_archive(tmp_path, "HEAD", tmp_path / "snapshot")

    assert not outside.exists()


def test_blame_uses_student_authorship_for_mutation_targets(tmp_path: Path) -> None:
    repo = tmp_path / "student-repo"
    subprocess.run(
        [sys.executable, str(ROOT / "demo" / "build_demo_repo.py"), str(repo)],
        check=True,
        cwd=ROOT,
    )
    commit = resolve_commit(repo, "HEAD")
    source = next(
        item
        for item in load_source_files(repo, commit)
        if item.path == "gradebook/analytics.py"
    )
    blame = blame_file(repo, commit, source.path, "d.ramos@alumnos.ejemplo.edu")

    boundary_line = next(
        index + 1
        for index, line in enumerate(source.text.splitlines())
        if "score >= 60" in line
    )
    assert blame[boundary_line - 1].is_student
    assert blame[boundary_line - 1].summary == "implement letter_grade"
