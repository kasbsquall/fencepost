import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import facts from '../../public/casts/facts.json';

const K = facts.commit;

/**
 * Scene 7 — the receipt.
 *
 * A reviewer called this the strongest ten seconds in the film, stronger than the flip:
 * "scene 5 proves your tool works; this proves the problem is real, using the student's own
 * words as evidence." The commit subject is read from their git history by film_facts.py,
 * not quoted from memory, because the whole beat rests on it being theirs.
 *
 * "Here's the part that gets me" is the one line where a human seems to be speaking, so the
 * scene stays plain: the commit, then the sentence that turns it, and nothing competing.
 */
export const Scene7: React.FC = () => {
  const s = sceneOf(7);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);
  const frame = useCurrentFrame();

  const turnAt = b[5] ?? 221;
  const strike = interpolate(frame, [turnAt, turnAt + 26], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <Stage tint={C.fail} intensity={0.7}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>their own commit</Kicker>
      </OnBeat>

      <OnBeat at={b[1] ?? 44} y={10}>
        <div
          style={{
            fontFamily: F.mono,
            fontSize: tx(20),
            color: C.ink,
            background: C.panel,
            border: `1px solid ${C.line}`,
            borderRadius: px(10),
            padding: `${px(22)}px ${px(26)}px`,
            boxShadow: `0 ${px(24)}px ${px(56)}px rgba(0,0,0,0.5)`,
            ...NO_LIGATURES,
          }}
        >
          <span style={{color: C.faint}}>{K.sha}</span>
          {'  '}
          <span>"{K.subject}"</span>
        </div>
      </OnBeat>

      <OnBeat at={b[3] ?? 133}>
        <div
          style={{
            marginTop: px(30),
            fontSize: tx(30),
            fontWeight: 650,
            letterSpacing: '-.03em',
            lineHeight: 1.2,
          }}
        >
          They fixed it.{' '}
          <span
            style={{
              color: C.fail,
              // The turn lands on its own downbeat, underlined by a wipe on the beat.
              backgroundImage: `linear-gradient(${C.fail}, ${C.fail})`,
              backgroundSize: `${strike * 100}% ${px(2)}px`,
              backgroundPosition: '0 100%',
              backgroundRepeat: 'no-repeat',
              paddingBottom: px(4),
            }}
          >
            And their tests never checked it.
          </span>
        </div>
      </OnBeat>
    </Stage>
  );
};
