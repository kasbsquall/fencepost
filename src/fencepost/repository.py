"""Git snapshot and attribution helpers.

The source revision analysed here is the exact revision later copied into each
Docker sandbox.  Blame coordinates are therefore never taken from generated
``ast.unparse`` output.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tarfile
import tokenize
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath

from .models import AttributionIdentity, BlameLine


class RepositoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceFile:
    path: str
    text: str
    sha256: str


@dataclass(frozen=True)
class _RawBlameLine:
    commit: str
    original_line: int | None
    final_line: int
    metadata: dict[str, str]


_CO_AUTHOR_TRAILER = re.compile(
    r"^co-authored-by:\s*(?P<name>.*?)\s*<(?P<email>[^<>\s]+)>\s*$",
    re.IGNORECASE,
)

ATTRIBUTION_LIMITATION = (
    "Git blame attributes lines to the commit history it can trace, not to the "
    "person who was at the keyboard. Pair programming, a partner pushing from "
    "another machine, squash merges, and rebases can therefore make a line look "
    "solely student-authored when Git cannot prove that. Fencepost records "
    "co-author trailers, author/committer differences, and -M/-C matches, but "
    "those signals do not establish intent or authorship."
)


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


def _blame_output(repo: Path, commit: str, path: str, *options: str) -> str:
    blamed = _git(repo, "blame", *options, "--line-porcelain", commit, "--", path)
    if blamed.returncode != 0:
        raise RepositoryError(blamed.stderr.strip())
    return blamed.stdout


def _parse_blame(output: str) -> tuple[_RawBlameLine, ...]:
    lines: list[_RawBlameLine] = []
    current: dict[str, str] = {}
    header = re.compile(r"^([0-9a-f]{40})\s+(\d+)\s+(\d+)(?:\s+\d+)?$")
    for raw in output.splitlines():
        if raw.startswith("\t"):
            try:
                final_line = int(current["final-line"])
            except (KeyError, ValueError):
                continue
            original = current.get("original-line")
            lines.append(
                _RawBlameLine(
                    commit=current.get("commit", ""),
                    original_line=int(original) if original is not None else None,
                    final_line=final_line,
                    metadata=current,
                )
            )
            current = {}
            continue
        matched = header.match(raw)
        if matched:
            current = {
                "commit": matched.group(1),
                "original-line": matched.group(2),
                "final-line": matched.group(3),
            }
            continue
        if not raw or " " not in raw:
            continue
        key, value = raw.split(" ", 1)
        current[key] = value
    return tuple(lines)


def _line_identity(line: _RawBlameLine) -> tuple[str, int | None, str]:
    return (line.commit, line.original_line, line.metadata.get("filename", ""))


def _commit_coauthors(
    repo: Path, commit: str, cache: dict[str, tuple[AttributionIdentity, ...]]
) -> tuple[AttributionIdentity, ...]:
    if commit in cache:
        return cache[commit]
    shown = _git(repo, "show", "-s", "--format=%B", commit)
    if shown.returncode != 0:
        raise RepositoryError(shown.stderr.strip())
    seen: set[tuple[str, str]] = set()
    coauthors: list[AttributionIdentity] = []
    for raw in shown.stdout.splitlines():
        matched = _CO_AUTHOR_TRAILER.match(raw)
        if matched is None:
            continue
        name = matched.group("name").strip()
        email = matched.group("email").strip()
        identity = (name.casefold(), email.casefold())
        if identity in seen:
            continue
        seen.add(identity)
        coauthors.append(AttributionIdentity(name=name, email=email))
    cache[commit] = tuple(coauthors)
    return cache[commit]


def _author_date(metadata: dict[str, str]) -> str:
    try:
        raw_offset = metadata.get("author-tz", "+0000")
        sign = -1 if raw_offset.startswith("-") else 1
        hours = int(raw_offset[1:3])
        minutes = int(raw_offset[3:5])
        zone = timezone(sign * timedelta(hours=hours, minutes=minutes))
        return datetime.fromtimestamp(int(metadata["author-time"]), tz=zone).date().isoformat()
    except (KeyError, TypeError, ValueError):
        return "unknown"


def _identities_match(metadata: dict[str, str]) -> bool:
    author = (
        metadata.get("author", "").strip().casefold(),
        metadata.get("author-mail", "").strip("<>").casefold(),
    )
    committer = (
        metadata.get("committer", "").strip().casefold(),
        metadata.get("committer-mail", "").strip("<>").casefold(),
    )
    return author == committer


def _history_signals(metadata: dict[str, str], author_matches_committer: bool) -> tuple[str, ...]:
    signals = []
    if not author_matches_committer:
        signals.append("author_committer_identity_mismatch")
    author_time = metadata.get("author-time")
    committer_time = metadata.get("committer-time")
    if author_time and committer_time and author_time != committer_time:
        signals.append("author_committer_time_mismatch")
    return tuple(signals)


def repository_history_signals(repo: Path) -> tuple[str, ...]:
    """Return observable repository history conditions without inferring intent."""
    signals: list[str] = []
    shallow = _git(repo, "rev-parse", "--is-shallow-repository")
    if shallow.returncode == 0 and shallow.stdout.strip() == "true":
        signals.append("shallow_repository")
    replacements = _git(repo, "replace", "-l")
    if replacements.returncode == 0 and replacements.stdout.strip():
        signals.append("replace_refs_present")
    return tuple(signals)


def blame_file(
    repo: Path, commit: str, path: str, student_email: str
) -> tuple[BlameLine, ...]:
    """Blame a file and record the observable limits of that attribution.

    The first invocation is Fencepost's authoritative ``-M -C -C -w`` result.
    Two comparison runs identify whether that result actually depended on Git's
    move or copy heuristics; porcelain alone does not label those matches.
    """
    full = _parse_blame(_blame_output(repo, commit, path, "-M", "-C", "-C", "-w"))
    move_only = _parse_blame(_blame_output(repo, commit, path, "-M", "-w"))
    plain = _parse_blame(_blame_output(repo, commit, path, "-w"))
    if not (len(full) == len(move_only) == len(plain)):
        raise RepositoryError(f"inconsistent blame output for {path}")

    lines: list[BlameLine] = []
    coauthor_cache: dict[str, tuple[AttributionIdentity, ...]] = {}
    for full_line, move_line, plain_line in zip(full, move_only, plain):
        metadata = full_line.metadata
        email = metadata.get("author-mail", "").strip("<>")
        author_matches_committer = _identities_match(metadata)
        lines.append(
            BlameLine(
                path=path,
                line=full_line.final_line,
                commit=full_line.commit,
                author_name=metadata.get("author", ""),
                author_email=email,
                author_date=_author_date(metadata),
                summary=metadata.get("summary", ""),
                is_student=email.casefold() == student_email.casefold(),
                committer_name=metadata.get("committer", ""),
                committer_email=metadata.get("committer-mail", "").strip("<>"),
                author_matches_committer=author_matches_committer,
                co_authors=_commit_coauthors(repo, full_line.commit, coauthor_cache),
                history_rewrite_signals=_history_signals(
                    metadata, author_matches_committer
                ),
                moved_by_blame=_line_identity(move_line) != _line_identity(plain_line),
                copied_by_blame=_line_identity(full_line) != _line_identity(move_line),
                origin_path=metadata.get("filename") or None,
                origin_line=full_line.original_line,
            )
        )
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
