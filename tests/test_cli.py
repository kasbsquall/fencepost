from fencepost.adversarial import CodexCliAdversarialTestGenerator
from fencepost.cli import _build_generator, _build_probe_agent, _parser
from fencepost.probe import CodexCliComprehensionProbeAgent


def test_cli_defaults_to_chatgpt_authenticated_codex_model(monkeypatch) -> None:
    monkeypatch.delenv("FENCEPOST_ADVERSARIAL_MODEL", raising=False)
    args = _parser().parse_args(
        [
            "student-repo",
            "--student-email",
            "student@example.edu",
            "--output",
            "artifact",
        ]
    )

    assert args.generator == "codex"
    assert args.adversarial_model == "gpt-5.6-terra"
    assert args.triage_attempts == 3
    assert args.max_survivors_triaged is None
    generator = _build_generator(args)
    assert isinstance(generator, CodexCliAdversarialTestGenerator)
    assert generator.model == "gpt-5.6-terra"
    probe_agent = _build_probe_agent(args, generator)
    assert isinstance(probe_agent, CodexCliComprehensionProbeAgent)
    assert probe_agent.client is generator.client
