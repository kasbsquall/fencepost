from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fencepost.repository import blame_file, load_source_files, resolve_commit


ROOT = Path(__file__).resolve().parents[1]


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
