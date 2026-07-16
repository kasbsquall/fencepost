"""Git snapshot and attribution helpers.

The source revision analysed here is the exact revision later copied into each
Docker sandbox.  Blame coordinates are therefore never taken from generated
``ast.unparse`` output.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
import tokenize
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

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
    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else ""
    directories = parts[:-1]
    return (
        any(part in {"test", "tests"} for part in directories)
        or name == "conftest.py"
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


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
    root = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
        members = archive.getmembers()
        safe_members: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
        for member in members:
            relative = PurePosixPath(member.name)
            if (
                relative.is_absolute()
                or not relative.parts
                or ".." in relative.parts
                or "\\" in member.name
            ):
                raise RepositoryError(
                    f"unsafe path in Git archive: {member.name!r}"
                )
            # Git preserves symbolic links in archives.  Extracting them before
            # a later member creates a classic TOCTOU tar-slip: the later write
            # follows a link that did not exist during lexical validation.
            # Fencepost snapshots need only directories and regular files, so
            # reject links (and every other special member) outright.
            if member.issym() or member.islnk():
                raise RepositoryError(
                    f"links are not allowed in Git archives: {member.name!r}"
                )
            if not (member.isdir() or member.isreg()):
                raise RepositoryError(
                    f"unsupported member in Git archive: {member.name!r}"
                )
            safe_members.append((member, relative))

        directories: list[tuple[Path, int]] = []
        for member, relative in safe_members:
            target = destination.joinpath(*relative.parts)
            resolved = target.resolve(strict=False)
            if resolved != root and root not in resolved.parents:
                raise RepositoryError(
                    f"unsafe path in Git archive: {member.name!r}"
                )
            if target.is_symlink():
                raise RepositoryError(
                    f"archive destination contains a link: {member.name!r}"
                )
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                directories.append((target, member.mode))
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            parent = target.parent.resolve(strict=True)
            if parent != root and root not in parent.parents:
                raise RepositoryError(
                    f"unsafe parent in Git archive: {member.name!r}"
                )
            source = archive.extractfile(member)
            if source is None:
                raise RepositoryError(
                    f"cannot read regular archive member: {member.name!r}"
                )
            try:
                with source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
            except FileExistsError as exc:
                raise RepositoryError(
                    f"archive member would overwrite an existing path: {member.name!r}"
                ) from exc
            target.chmod(member.mode & 0o777)

        # Apply directory modes after their children have been materialized.
        for directory, mode in reversed(directories):
            directory.chmod(mode & 0o777)
