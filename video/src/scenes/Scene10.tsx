import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import facts from '../../public/casts/facts.json';

const COUNTS = facts.counts;

/**
 * Scene 10 — the proof.
 *
 * This beat did not exist in the first cut. All three reviewers flagged that the strongest
 * evidence in the README never reached the film: the counts that show restraint, and the
 * moment GPT-5.6 refuted its own authors twice on equivalence. For a research-shaped
 * Education pitch, that is the proof beat — evidence the thing works and that we tried to
 * break it — and it is more credible than any traction chart because it is the model
 * arguing against us.
 *
 * The counts are read from facts.json (51 / 30 / 21), not typed, for the same reason as the
 * diff: a hand-set number in a slide looks exactly as sure as a measured one.
 */
export const Scene10: React.FC = () => {
  const s = sceneOf(10);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);
  const frame = useCurrentFrame();

  const barAt = b[1] ?? 44;
  const grow = interpolate(frame, [barAt, barAt + 26], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const {eligible, killed, survived} = COUNTS;

  return (
    <Stage tint={C.fail} intensity={0.6}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>we tried to break it, and printed what happened</Kicker>
      </OnBeat>

      {/* killed vs survived, to scale, out of the eligible total. */}
      <OnBeat at={barAt} y={8}>
        <div style={{display: 'flex', gap: px(4), height: px(20), marginBottom: px(14)}}>
          <div
            style={{
              background: C.pass,
              flex: killed,
              borderRadius: px(99),
              transform: `scaleX(${grow})`,
              transformOrigin: 'left',
            }}
          />
          <div
            style={{
              background: C.fail,
              flex: survived,
              borderRadius: px(99),
              transform: `scaleX(${grow})`,
              transformOrigin: 'left',
            }}
          />
        </div>
        <div
          style={{
            display: 'flex',
            gap: px(28),
            fontFamily: F.mono,
            fontSize: tx(11),
            color: C.faint,
            ...NO_LIGATURES,
          }}
        >
          <span>
            <b style={{color: C.pass}}>{killed}</b> caught by their own tests
          </span>
          <span>
            <b style={{color: C.fail}}>{survived}</b> they missed, out of {eligible}
          </span>
        </div>
      </OnBeat>

      {/* The refutation. The strongest line in the README, finally on screen. */}
      <OnBeat at={b[4] ?? 177} y={10}>
        <div
          style={{
            marginTop: px(34),
            borderLeft: `${px(3)}px solid ${C.pass}`,
            background: C.sunk,
            padding: `${px(20)}px ${px(24)}px`,
            borderRadius: `0 ${px(8)}px ${px(8)}px 0`,
            maxWidth: px(760),
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
            one we refused to ask
          </div>
          <div style={{fontSize: tx(17), color: C.ink, lineHeight: 1.4}}>
            The only way to break it was to break the program.{' '}
            <span style={{color: C.pass}}>
              GPT-5.6 refuted us twice on that, and we printed both.
            </span>
          </div>
        </div>
      </OnBeat>
    </Stage>
  );
};
