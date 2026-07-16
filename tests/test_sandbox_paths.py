from __future__ import annotations

from fencepost.sandbox import DockerSandbox


def test_pythonpath_includes_repo_src_and_detected_package_roots(tmp_path) -> None:
    (tmp_path / "gradebook").mkdir()
    (tmp_path / "gradebook" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "coursework").mkdir(parents=True)
    (tmp_path / "src" / "coursework" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "backend" / "service").mkdir(parents=True)
    (tmp_path / "backend" / "service" / "__init__.py").write_text("", encoding="utf-8")

    roots = DockerSandbox._pythonpath(tmp_path).split(":")

    assert roots == ["/workspace", "/workspace/src", "/workspace/backend"]
