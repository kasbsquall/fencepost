"""Capture the film's Codex shot: the real stage-5 call, on a real survivor.

Scene 7 claims Codex runs *inside* the product, writing adversarial tests at runtime. The
cheap way to shoot that is to type a plausible-looking codex command and film it. That would
be a recreation of a claim the rest of the film insists on proving, in the one scene whose
whole subject is that the claim is true.

So this builds the request with fencepost's own code — the product's instructions, the
product's payload, the product's schema — and runs the exact argv that adversarial.py runs.
No paraphrase between what ships and what the camera sees.

The mutant is 92261c57ed4e3d56 from .fp_demo: `p > 100` -> `p >= 100` in a clamp, which
survived the student's suite. It is the one from the README, where GPT-5.6 refuted two
humans with a negative-zero witness. Whatever it writes this time is what the film shows.

Usage:
    python tools/capture_codex_shot.py [--mode STRICT] [--mutant <id>]
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fencepost.adversarial import (
    _CODEX_OUTPUT_SCHEMA,
    _instructions_for,
    _request_payload,
)
from fencepost.models import AdversarialTestRequest

RUN = Path(".fp_demo")
CLAMP = "92261c57ed4e3d56"


def build_request(mutant_id, mode):
    """Rebuild the request the pipeline made for this survivor."""
    meta = json.loads((RUN / "mutants" / mutant_id / "result.json").read_text("utf-8"))
    original = (RUN / "mutants" / mutant_id / "original.py").read_text("utf-8")
    mutated = (RUN / "mutants" / mutant_id / "mutated.py").read_text("utf-8")

    import difflib
    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True), mutated.splitlines(keepends=True),
        fromfile="original", tofile="mutated",
    ))

    # The pipeline passes live objects; here we only need the fields _request_payload reads.
    cand = meta["candidate"]
    from types import SimpleNamespace
    mutant = SimpleNamespace(candidate=SimpleNamespace(**cand))

    from fencepost.contract import contract_rules_payload
    module_path = cand["path"]
    return AdversarialTestRequest(
        mutant=mutant,
        attempt=1,
        valid_attempts_completed=0,
        module_path=module_path,
        qualified_function_name="clamp_percent",
        original_function=original,
        mutated_function=mutated,
        unified_diff=diff,
        mode=mode,
        contract_rules=contract_rules_payload(module_path) if mode == "CONTRACT" else None,
        prior_attempts=(),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutant", default=CLAMP)
    ap.add_argument("--mode", default="STRICT", choices=["STRICT", "CONTRACT"])
    ap.add_argument("--model", default="gpt-5.6-terra")
    ap.add_argument("--out", default="docs/video/casts/codex_exec.json")
    args = ap.parse_args()

    req = build_request(args.mutant, args.mode)
    prompt = (
        _instructions_for(req)
        + "\nThe response schema names the Python field test_source.\n\n"
        + json.dumps(_request_payload(req), indent=2, sort_keys=True)
    )

    tmp = Path(tempfile.mkdtemp(prefix="fencepost-shot-"))
    schema_path = tmp / "schema.json"
    last_path = tmp / "last-message.json"
    schema_path.write_text(json.dumps(_CODEX_OUTPUT_SCHEMA, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")

    # Exactly adversarial.py's argv. Paths are shortened for display only; the run uses the
    # real ones. Nothing else is touched.
    # On Windows `codex` is a .cmd shim, so CreateProcess cannot find it by bare name.
    # adversarial.py resolves it the same way; matching that keeps the shot honest.
    import shutil
    executable = shutil.which("codex") or "codex"
    argv = [
        executable, "exec", "-m", args.model,
        "-c", "mcp_servers={}", "-c", 'sandbox_mode="read-only"',
        "--output-schema", str(schema_path), "--json",
        "--output-last-message", str(last_path),
        "--skip-git-repo-check", "-",
    ]
    display = (f"codex exec -m {args.model} -c mcp_servers={{}} "
               f"-c sandbox_mode=\"read-only\" \\\n"
               f"  --output-schema schema.json --json \\\n"
               f"  --output-last-message last-message.json --skip-git-repo-check -")

    print(f"  mutant   {args.mutant}  {req.mutant.candidate.source_segment} "
          f"({req.mutant.candidate.before} -> {req.mutant.candidate.after})")
    print(f"  mode     {args.mode}")
    print(f"  prompt   {len(prompt)} chars\n")
    print(f"  $ {display}\n")

    t0 = time.monotonic()
    events = []
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1,
                         encoding="utf-8", errors="replace")
    p.stdin.write(prompt)
    p.stdin.close()
    for line in p.stdout:
        line = line.rstrip("\n")
        events.append({"t": round(time.monotonic() - t0, 3), "s": line})
        sys.stdout.write(line[:200] + "\n")
        sys.stdout.flush()
    p.wait()
    dur = time.monotonic() - t0

    payload = None
    if last_path.exists():
        try:
            payload = json.loads(last_path.read_text("utf-8"))
        except json.JSONDecodeError:
            payload = {"raw": last_path.read_text("utf-8")[:2000]}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "cmd": display, "argv": argv, "exit": p.returncode,
        "duration": round(dur, 3), "mutant": args.mutant, "mode": args.mode,
        "model": args.model, "events": events, "result": payload,
    }, indent=2), encoding="utf-8")

    print(f"\n  exit {p.returncode}   {dur:.1f}s   {len(events)} lines")
    if isinstance(payload, dict) and "test_source" in payload:
        print(f"\n  targeted_behavior: {payload.get('targeted_behavior')}")
        print("  --- the test Codex wrote ---")
        for ln in payload["test_source"].splitlines():
            print("   ", ln)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
