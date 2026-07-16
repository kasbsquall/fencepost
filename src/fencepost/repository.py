"""Git snapshot and attribution helpers.

The source revision analysed here is the exact revision later copied into each
Docker sandbox.  Blame coordinates are therefore never taken from generated
``ast.unparse`` output.
"""

from __future__ import annotations

import io
import subprocess
import tarfile
import tokenize
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .models import BlameLine


class RepositoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceFile:
    path: str
    text: str
    sha256: str


def _git(repo: Path, *args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=text,
        capture_output=True,
        check=False,
    )


def resolve_commit(repo: Path, requested: str) -> str:
    repo = repo.resolve()
    check = _git(repo, "rev-parse", "--is-inside-work-tree")
    if check.returncode != 0 or check.stdout.strip() != "true":
        raise RepositoryError(f"not a Git working tree: {repo}")

    dirty = _git(repo, "status", "--porcelain")
    if dirty.returncode != 0:
        raise RepositoryError(dirty.stderr.strip())
    if dirty.stdout.strip():
        raise RepositoryError(
            "target repository has uncommitted changes; Fencepost analyses a committed snapshot"
        )

    resolved = _git(repo, "rev-parse", "--verify", f"{requested}^{{commit}}")
    if resolved.returncode != 0:
        raise RepositoryError(resolved.stderr.strip() or f"unknown revision {requested}")
    return resolved.stdout.strip()


def tracked_python_files(repo: Path, commit: str) -> tuple[str, ...]:
    listed = _git(repo, "ls-tree", "-r", "--name-only", commit)
    if listed.returncode != 0:
        raise RepositoryError(listed.stderr.strip())
    return tuple(path for path in listed.stdout.splitlines() if path.endswith(".py"))


def is_test_path(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")


def load_source_files(repo: Path, commit: str) -> tuple[SourceFile, ...]:
    result: list[SourceFile] = []
    for path in tracked_python_files(repo, commit):
        if is_test_path(path):
            continue
        shown = _git(repo, "show", f"{commit}:{path}", text=False)
        if shown.returncode != 0:
            raise RepositoryError(shown.stderr.decode("utf-8", "replace"))
        raw = shown.stdout
        try:
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
            source = raw.decode(encoding)
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise RepositoryError(f"cannot decode {path}: {exc}") from exc
        result.append(SourceFile(path=path, text=source, sha256=sha256(raw).hexdigest()))
    return tuple(result)


def blame_file(
    repo: Path, commit: str, path: str, student_email: str
) -> tuple[BlameLine, ...]:
    blamed = _git(
        repo,
        "blame",
        "-M",
        "-C",
        "-C",
        "-w",
        "--line-porcelain",
        commit,
        "--",
        path,
    )
    if blamed.returncode != 0:
        raise RepositoryError(blamed.stderr.strip())

    lines: list[BlameLine] = []
    current: dict[str, str] = {}
    line_number = 0
    for raw in blamed.stdout.splitlines():
        if raw.startswith("\t"):
            line_number += 1
            email = current.get("author-mail", "").strip("<>")
            lines.append(
                BlameLine(
                    path=path,
                    line=line_number,
                    commit=current.get("commit", ""),
                    author_name=current.get("author", ""),
                    author_email=email,
                    summary=current.get("summary", ""),
                    is_student=email.casefold() == student_email.casefold(),
                )
            )
            current = {}
            continue
        if not raw:
            continue
        if " " not in raw:
            continue
        key, value = raw.split(" ", 1)
        if len(key) == 40 and all(char in "0123456789abcdef" for char in key):
            current["commit"] = key
        else:
            current[key] = value
    return tuple(lines)


def extract_archive(repo: Path, commit: str, destination: Path) -> None:
    archived = _git(repo, "archive", "--format=tar", commit, text=False)
    if archived.returncode != 0:
        raise RepositoryError(archived.stderr.decode("utf-8", "replace"))
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if destination.resolve() not in target.parents and target != destination.resolve():
                raise RepositoryError("unsafe member in Git archive")
        # Members were validated above.  Extract individually to retain the
        # Python 3.9 compatibility required by the AST mutator.
        for member in archive.getmembers():
            archive.extract(member, destination)
