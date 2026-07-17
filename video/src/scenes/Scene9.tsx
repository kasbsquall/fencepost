import React from 'react';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, nextDownbeat, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import {Terminal} from '../components';
import cast from '../../public/casts/codex_exec.json';

/**
 * Scene 9 — Codex inside.
 *
 * This carries the submission's headline requirement: the audio must cover how Codex and
 * GPT-5.6 were used. The terminal is the real stage-5 call on a real survivor — the argv
 * the product runs, captured with fencepost's own request builder, not a re-typed
 * lookalike. The `-m gpt-5.6-terra` flag is on screen because the rule wants it seen.
 *
 * The generated test appears when the run actually emits it (item.completed at ~15s), not
 * on a chosen beat: the answer must not arrive before the question. That timing is derived
 * from the capture and snapped forward to the next downbeat so it still lands on the drum.
 */
export const Scene9: React.FC = () => {
  const s = sceneOf(9);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);

  const test =
    (cast as any).result?.test_source ??
    'import gradebook.analytics as analytics\n\n\ndef test_clamp_percent_preserves_float_at_inclusive_upper_boundary():\n    result = analytics.clamp_percent(100.0)\n    assert str(result) == "100.0"';

  const termStart = b[0] ?? 0;
  const emitted = cast.events.find((e) => e.s.includes('item.completed'));
  const emittedFrame = termStart + Math.round(((emitted?.t ?? 15) + 0.5) * 30);
  const testAt = nextDownbeat(emittedFrame + s.from) - s.from;

  const flags = ['--network none', 'read-only rootfs', 'no /out mount', 'caps dropped'];
  const flagsAt = b[8] ?? 354;

  return (
    <Stage tint={C.pass} intensity={0.5} pad={80}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker color={C.pass}>codex runs inside the product · on the instructor's own plan · no api key</Kicker>
      </OnBeat>

      <OnBeat at={b[0] ?? 0} y={8}>
        <Terminal
          cmd={cast.cmd}
          events={cast.events}
          startFrame={b[0] ?? 0}
          fps={30}
          scale={1.15}
          maxChars={104}
        />
      </OnBeat>

      <OnBeat at={testAt} y={10}>
        <div
          style={{
            marginTop: px(18),
            border: `1px solid ${C.pass}`,
            background: C.passBg,
            borderRadius: px(10),
            padding: `${px(16)}px ${px(18)}px`,
            boxShadow: `0 ${px(20)}px ${px(46)}px rgba(0,0,0,0.5)`,
          }}
        >
          <pre
            style={{
              fontFamily: F.mono,
              fontSize: tx(11),
              color: C.addInk,
              margin: 0,
              whiteSpace: 'pre-wrap',
              ...NO_LIGATURES,
            }}
          >
            {test.trim()}
          </pre>
        </div>
      </OnBeat>

      <div style={{display: 'flex', gap: px(10), flexWrap: 'wrap', marginTop: px(16)}}>
        {flags.map((f, i) => (
          <OnBeat key={f} at={flagsAt + i * 5} y={6} inline>
            <span
              style={{
                fontFamily: F.mono,
                fontSize: tx(10),
                color: C.dim,
                border: `1px solid ${C.line}`,
                borderRadius: px(99),
                padding: `${px(6)}px ${px(13)}px`,
                ...NO_LIGATURES,
              }}
            >
              {f}
            </span>
          </OnBeat>
        ))}
      </div>
    </Stage>
  );
};
