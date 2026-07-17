"""Tag which stream each captured line came from, without re-running the capture.

capture_codex_shot.py merged stderr into stdout so nothing could be lost. That means the
take contains transport errors from a broken MCP server in the host's global codex config —
environment noise that the product never sees, because adversarial.py captures the two
streams separately and reads only stdout.

Re-running would separate them cleanly, but codex is not deterministic: the take would be a
different test. The take we have is real and the film shows what it wrote. So this labels
the lines instead of regenerating them.

The rule is narrow and printed, not a filter that quietly drops whatever looks untidy:
a line is stderr only if it matches codex's Rust tracing prefix. Every line it moves is
listed. Anything it cannot classify stays on stdout.
"""

import argparse
import json
import re
from pathlib import Path

# codex's Rust tracing writes ISO-8601 + LEVEL + target::path to stderr. Nothing the
# product reads on stdout looks like this — stdout is one JSON object per line.
STDERR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s+(ERROR|WARN|INFO|DEBUG|TRACE)\s+\S+:")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cast")
    args = ap.parse_args()

    p = Path(args.cast)
    d = json.loads(p.read_text("utf-8"))

    out, err, unknown = [], [], []
    for e in d["events"]:
        s = e["s"]
        if STDERR_RE.match(s):
            err.append(e)
        elif s.startswith("{") and s.rstrip().endswith("}"):
            out.append(e)
        else:
            unknown.append(e)
            out.append(e)

    d["events"] = out
    d["stderr_events"] = err
    d["stream_note"] = (
        "stdout is what adversarial.py reads and what the film renders. stderr_events are "
        "transport errors from an unrelated MCP server in the host's global codex config; "
        "the product captures the streams separately and never reads them."
    )
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")

    print(f"  stdout {len(out)}   stderr {len(err)}   unclassified {len(unknown)}")
    print("\n  movido a stderr:")
    for e in err:
        print(f"    {e['t']:6.2f}s  {e['s'][:96]}")
    if unknown:
        print("\n  no clasificado, se queda en stdout:")
        for e in unknown:
            print(f"    {e['t']:6.2f}s  {e['s'][:96]}")
    print(f"\n  -> {p}")


if __name__ == "__main__":
    main()
