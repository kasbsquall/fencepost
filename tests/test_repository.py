from __future__ import annotations

import io
import os
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
STUDENT = ("Diego Student", "diego@student.edu")
INSTRUCTOR = ("Ana Prof", "ana@school.edu")
PARTNER = ("Sam Partner", "sam@school.edu")


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


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    completed = subprocess.run(
        ["git", *args],
        check=True,
        cwd=repo,
        env=command_env,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def _identity_env(
    author: tuple[str, str],
    committer: tuple[str, str] | None = None,
    *,
    author_date: str = "2026-01-01T12:00:00+00:00",
    committer_date: str | None = None,
) -> dict[str, str]:
    committer = committer or author
    return {
        "GIT_AUTHOR_NAME": author[0],
        "GIT_AUTHOR_EMAIL": author[1],
        "GIT_AUTHOR_DATE": author_date,
        "GIT_COMMITTER_NAME": committer[0],
        "GIT_COMMITTER_EMAIL": committer[1],
        "GIT_COMMITTER_DATE": committer_date or author_date,
    }


def _history_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "checkout", "-qb", "main")
    _git(repo, "config", "user.name", STUDENT[0])
    _git(repo, "config", "user.email", STUDENT[1])
    (repo / "module.py").write_text("# instructor scaffold\n", encoding="utf-8")
    _commit(repo, "instructor scaffold", INSTRUCTOR)
    return repo


def _commit(
    repo: Path,
    message: str,
    author: tuple[str, str],
    committer: tuple[str, str] | None = None,
    *,
    author_date: str = "2026-01-01T12:00:00+00:00",
    committer_date: str | None = None,
) -> str:
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        message,
        env=_identity_env(
            author,
            committer,
            author_date=author_date,
            committer_date=committer_date,
        ),
    )
    return _git(repo, "rev-parse", "HEAD")


def _blamed_line(repo: Path, snippet: str):
    commit = resolve_commit(repo, "HEAD")
    source = next(item for item in load_source_files(repo, commit) if item.path == "module.py")
    line_number = next(
        index + 1 for index, line in enumerate(source.text.splitlines()) if snippet in line
    )
    return blame_file(repo, commit, source.path, STUDENT[1])[line_number - 1]


def test_blame_uses_student_authorship_for_mutation_targets_and_documents_adversarial_histories(
    tmp_path: Path,
) -> None:
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
    assert blame[boundary_line - 1].author_date == "2026-07-07"

    # Pair programming is intentionally unobservable to Git: Sam wrote this code,
    # but Diego made the commit. Fencepost currently and incorrectly accepts it.
    pair = _history_repo(tmp_path, "pair")
    (pair / "module.py").write_text(
        "# instructor scaffold\n\ndef pair_work(value):\n    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(pair, "pair work", STUDENT)
    pair_line = _blamed_line(pair, "return value >= 70")
    assert pair_line.is_student and pair_line.solely_student_attributed
    assert not pair_line.co_authors
    assert pair_line.author_matches_committer

    # Co-authored-by is detectable. The commit author is Diego, but the line is
    # explicitly not solely attributable and must be excluded by selection.
    coauthored = _history_repo(tmp_path, "coauthored")
    (coauthored / "module.py").write_text(
        "# instructor scaffold\n\ndef shared_work(value):\n    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(
        coauthored,
        "shared work\n\nCo-authored-by: Sam Partner <sam@school.edu>",
        STUDENT,
    )
    coauthored_line = _blamed_line(coauthored, "return value >= 70")
    assert coauthored_line.is_student
    assert not coauthored_line.solely_student_attributed
    assert [person.email for person in coauthored_line.co_authors] == [PARTNER[1]]

    # A squash merge erases Sam's original commit from blame. Git accepts Diego's
    # squash commit with no signal, so this is another known-wrong attribution.
    squash = _history_repo(tmp_path, "squash")
    _git(squash, "checkout", "-qb", "partner-feature")
    (squash / "module.py").write_text(
        "# instructor scaffold\n\ndef squashed_work(value):\n    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(squash, "partner feature", PARTNER)
    _git(squash, "checkout", "main")
    _git(squash, "merge", "--squash", "partner-feature")
    _commit(squash, "squash partner feature", STUDENT)
    squash_line = _blamed_line(squash, "return value >= 70")
    assert squash_line.is_student and squash_line.solely_student_attributed
    assert squash_line.author_matches_committer
    assert not squash_line.history_rewrite_signals

    # A rebase can preserve Diego as author while recording Ana as committer.
    # Fencepost retains the line but records the observable provenance warning.
    rebase = _history_repo(tmp_path, "rebase")
    _git(rebase, "checkout", "-qb", "student-topic")
    (rebase / "module.py").write_text(
        "# instructor scaffold\n\ndef rebased_work(value):\n    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(rebase, "student topic", STUDENT, author_date="2026-01-02T12:00:00+00:00")
    _git(rebase, "checkout", "main")
    (rebase / "README.md").write_text("main advanced\n", encoding="utf-8")
    _commit(rebase, "advance main", INSTRUCTOR, author_date="2026-01-03T12:00:00+00:00")
    _git(rebase, "checkout", "student-topic")
    _git(
        rebase,
        "rebase",
        "main",
        env={
            "GIT_COMMITTER_NAME": INSTRUCTOR[0],
            "GIT_COMMITTER_EMAIL": INSTRUCTOR[1],
            "GIT_COMMITTER_DATE": "2026-01-04T12:00:00+00:00",
        },
    )
    rebase_line = _blamed_line(rebase, "return value >= 70")
    assert rebase_line.is_student and rebase_line.solely_student_attributed
    assert not rebase_line.author_matches_committer
    assert "author_committer_identity_mismatch" in rebase_line.history_rewrite_signals
    assert "author_committer_time_mismatch" in rebase_line.history_rewrite_signals

    # A cherry-pick preserves Sam as author while Diego becomes committer. This
    # current attribution excludes Diego and records the mismatch signal.
    cherry = _history_repo(tmp_path, "cherry")
    _git(cherry, "checkout", "-qb", "partner-feature")
    (cherry / "module.py").write_text(
        "# instructor scaffold\n\ndef cherry_work(value):\n    return value >= 70\n",
        encoding="utf-8",
    )
    partner_commit = _commit(
        cherry, "partner implementation", PARTNER, author_date="2026-01-02T12:00:00+00:00"
    )
    _git(cherry, "checkout", "main")
    _git(
        cherry,
        "cherry-pick",
        partner_commit,
        env={
            "GIT_COMMITTER_NAME": STUDENT[0],
            "GIT_COMMITTER_EMAIL": STUDENT[1],
            "GIT_COMMITTER_DATE": "2026-01-04T12:00:00+00:00",
        },
    )
    cherry_line = _blamed_line(cherry, "return value >= 70")
    assert not cherry_line.is_student
    assert not cherry_line.solely_student_attributed
    assert not cherry_line.author_matches_committer

    # Git traces this unchanged same-file movement back to Ana. Its ordinary
    # line matching is enough here, so the differential -M signal is false;
    # this is deliberately recorded rather than relabeled as proof of keyboard work.
    moved = _history_repo(tmp_path, "moved")
    (moved / "module.py").write_text(
        "def instructor_scaffold(value):\n"
        "    very_long_instructor_marker = 'this scaffold line is deliberately long enough for git move detection'\n"
        "    return value >= 70\n\n"
        "def student_entry(value):\n"
        "    return value\n",
        encoding="utf-8",
    )
    _commit(moved, "add instructor scaffold", INSTRUCTOR)
    (moved / "module.py").write_text(
        "def student_entry(value):\n"
        "    return value\n\n"
        "def instructor_scaffold(value):\n"
        "    very_long_instructor_marker = 'this scaffold line is deliberately long enough for git move detection'\n"
        "    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(moved, "reorganize module", STUDENT)
    moved_line = _blamed_line(moved, "very_long_instructor_marker")
    assert not moved_line.is_student
    assert not moved_line.moved_by_blame
    assert moved_line.origin_path == "module.py"
    assert moved_line.origin_line == 2

    # Even a deliberate cross-file copy is a known blind spot in this small
    # history: Git attributes it to Diego and reports no -C match. Keeping this
    # assertion documents the current behavior rather than implying -C proves
    # who wrote the copied code.
    copied = _history_repo(tmp_path, "copied")
    (copied / "scaffold.py").write_text(
        "def instructor_helper(value):\n"
        "    copied_marker_one = 'this instructor scaffold is deliberately long enough for git copy detection one'\n"
        "    copied_marker_two = 'this instructor scaffold is deliberately long enough for git copy detection two'\n"
        "    copied_marker_three = 'this instructor scaffold is deliberately long enough for git copy detection three'\n"
        "    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(copied, "add instructor helper", INSTRUCTOR)
    (copied / "module.py").write_text(
        "# instructor scaffold\n\n"
        "def instructor_helper(value):\n"
        "    copied_marker_one = 'this instructor scaffold is deliberately long enough for git copy detection one'\n"
        "    copied_marker_two = 'this instructor scaffold is deliberately long enough for git copy detection two'\n"
        "    copied_marker_three = 'this instructor scaffold is deliberately long enough for git copy detection three'\n"
        "    return value >= 70\n",
        encoding="utf-8",
    )
    _commit(copied, "reuse helper", STUDENT)
    copied_line = _blamed_line(copied, "copied_marker_two")
    assert copied_line.is_student
    assert copied_line.solely_student_attributed
    assert not copied_line.copied_by_blame
    assert copied_line.origin_path == "module.py"
