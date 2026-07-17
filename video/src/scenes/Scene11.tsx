import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat} from '../Stage';
import {Wordmark} from '../components';

/**
 * Scene 11 — the ask.
 *
 * The first cut ended on "It's a reason to talk to your student", which is a fine last line
 * and a terrible ask: it requests nothing. An Education judge's last thought should be who
 * deploys this and how. The answer already existed and was never said: MIT, runs on the
 * instructor's own plan, the output never leaves their hands, and we want one real section.
 *
 * The closing line survives — it earned its place — but now it lands after the ask instead
 * of instead of it.
 */
export const Scene11: React.FC = () => {
  const s = sceneOf(11);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);
  const frame = useCurrentFrame();
  const dur = s.to - s.from;

  const out = interpolate(frame, [dur - 36, dur], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // "nothing leaves your hands" was false and the film proves it: scene 9 ships the
  // student's code to a hosted GPT-5.6 to write the test. A skeptical judge flagged it as
  // the kind of contradiction that makes them re-scrutinise everything. What is actually
  // true, and still strong for an Education pitch, is that the report never leaves — the
  // instructor's judgement and the student's answers stay local; only the code under test
  // crosses to the model, the same code the student already handed in.
  const CHIPS = ['MIT licensed', 'runs on your own plan', 'the report stays local'];

  return (
    <Stage tint={C.pass} intensity={0.5}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: out}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: px(30)}}>
          <OnBeat at={b[0] ?? 0}>
            <Wordmark size={tx(32)} />
          </OnBeat>

          <div style={{display: 'flex', gap: px(10)}}>
            {CHIPS.map((c, i) => (
              <OnBeat key={c} at={(b[1] ?? 44) + i * 6} y={8} inline>
                <span
                  style={{
                    fontFamily: F.mono,
                    fontSize: tx(10.5),
                    color: C.dim,
                    border: `1px solid ${C.line}`,
                    borderRadius: px(99),
                    padding: `${px(7)}px ${px(14)}px`,
                    ...NO_LIGATURES,
                  }}
                >
                  {c}
                </span>
              </OnBeat>
            ))}
          </div>

          <OnBeat at={b[3] ?? 132}>
            <p
              style={{
                fontSize: tx(30),
                textAlign: 'center',
                maxWidth: '24ch',
                lineHeight: 1.25,
                letterSpacing: '-.025em',
                margin: 0,
                fontWeight: 650,
              }}
            >
              One CS2 section this fall.
            </p>
          </OnBeat>

          <OnBeat at={b[5] ?? 220}>
            <p
              style={{
                fontSize: tx(18),
                textAlign: 'center',
                maxWidth: '30ch',
                color: C.faint,
                margin: 0,
                lineHeight: 1.4,
              }}
            >
              That's not a grade.{' '}
              <span style={{color: C.dim}}>It's a reason to talk to your student.</span>
            </p>
          </OnBeat>
        </div>
      </AbsoluteFill>
    </Stage>
  );
};
