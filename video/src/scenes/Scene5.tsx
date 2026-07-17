import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import {RunRow} from '../components';

/**
 * Scene 5 — the flip.
 *
 * The hold at the end used to be 2.6 seconds of total silence: no voice, no band. The client
 * watched it and asked why the film went quiet, and that question is the whole verdict — a
 * silence only reads as authored when the viewer never has to ask. On a laptop at 1.5x it is
 * indistinguishable from an encode dropout, and it was landing on a red error, which is the
 * exact grammar of "something broke". The worst possible frame to go dark over.
 *
 * So the voice stops and the band keeps playing, ducked. Voice-absent over a sustained bed
 * reads as emphasis. Total silence reads as failure. The hold is 48 frames from layout.json,
 * and tools/mix_audio.py owns the level, because the mix belongs next to the measurement.
 *
 * The rows land inside 4 seconds on purpose. A reviewer on the first pass: "if the animation
 * eats 4 seconds and the hold eats 2, the scene is all waiting. Land the rows fast so the
 * silence is on comprehension, not on animation."
 */
export const Scene5: React.FC = () => {
  const s = sceneOf(5);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);
  const frame = useCurrentFrame();

  // The assertion arrives, then the frame leans in slightly and stays there through the
  // hold. Nothing else moves: the picture is doing the talking.
  const at = b[5] ?? 221;
  const lean = interpolate(frame, [at, at + 40], [1, 1.028], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <Stage tint={C.fail} intensity={0.9}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>the assertion is the answer key</Kicker>
      </OnBeat>

      <div style={{display: 'flex', flexDirection: 'column', gap: px(18), marginBottom: px(26)}}>
        <OnBeat at={b[1] ?? 44}>
          <RunRow who="Their submitted suite" verb="passed" ok t="10 tests · 0.95s" scale={1.8} />
        </OnBeat>
        <OnBeat at={b[3] ?? 132}>
          <RunRow
            who="Test written by gpt-5.6-terra"
            verb="failed"
            ok={false}
            t="sandboxed · no network"
            scale={1.8}
          />
        </OnBeat>
      </div>

      <OnBeat at={at} y={8}>
        <div
          style={{
            transform: `scale(${lean})`,
            transformOrigin: 'left center',
            borderLeft: `${px(3)}px solid ${C.fail}`,
            background: C.sunk,
            padding: `${px(22)}px ${px(24)}px`,
            borderRadius: `0 ${px(8)}px ${px(8)}px 0`,
            boxShadow: `0 ${px(24)}px ${px(60)}px rgba(0,0,0,0.5)`,
          }}
        >
          <div
            style={{
              fontFamily: F.mono,
              fontSize: tx(9.5),
              letterSpacing: '.1em',
              textTransform: 'uppercase',
              color: C.faint,
              marginBottom: px(12),
              ...NO_LIGATURES,
            }}
          >
            What it printed
          </div>
          <pre
            style={{
              fontFamily: F.mono,
              fontSize: tx(15),
              color: C.fail,
              margin: 0,
              ...NO_LIGATURES,
            }}
          >
            IndexError: list index out of range
          </pre>
        </div>
      </OnBeat>
    </Stage>
  );
};
