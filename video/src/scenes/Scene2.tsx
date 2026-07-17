import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker, Head} from '../Stage';

/**
 * Scene 2 — the person.
 *
 * The first cut spent 14 seconds here on 24 tiles that did not render. Measured: C.panel
 * (#131519) on C.bg (#0B0C0E) is a 1.05:1 contrast ratio, and the "marked" tiles at
 * rgba(255,107,107,0.10) composited to about #231615, also 1.05:1. Twenty-four identical
 * black squares. The idea of the scene — some of these used an agent and you cannot tell
 * which — was invisible, and it was invisible for a seventh of the film.
 *
 * The tiles now carry a real border and fill, and the marked ones bloom to a red that is
 * legible rather than theoretical. The scene is also 5 seconds shorter, which paid for the
 * beat in scene 3 that explains what the product does.
 *
 * The grid deliberately never resolves. Eight are marked and the film never says which
 * eight are right, because the instructor cannot know either. That indeterminacy is the
 * whole problem, so the picture refuses to answer it.
 */
export const Scene2: React.FC = () => {
  const s = sceneOf(2);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const MARKED = [2, 5, 6, 9, 13, 14, 18, 21];
  const bloomAt = b[3] ?? 132;

  return (
    <Stage tint={C.fail} intensity={0.75}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>CS2 · assignment 3 · 24 submissions</Kicker>
      </OnBeat>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, 1fr)',
          gap: px(12),
          marginBottom: px(38),
        }}
      >
        {Array.from({length: 24}).map((_, i) => {
          const at = (b[1] ?? 44) + i * 2;
          const p = spring({frame: frame - at, fps, config: {damping: 14, stiffness: 140, mass: 0.5}});
          const marked = MARKED.includes(i);
          const bloom = interpolate(frame, [bloomAt, bloomAt + 22], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          return (
            <div
              key={i}
              style={{
                height: px(64),
                borderRadius: px(7),
                // 1px of C.line on C.panel was a 1.05:1 wall. These read.
                border: `1px solid ${marked ? `rgba(255,107,107,${0.25 + 0.5 * bloom})` : '#2E343E'}`,
                background: marked
                  ? `rgba(255,107,107,${0.06 + 0.22 * bloom})`
                  : '#191D23',
                boxShadow: marked
                  ? `0 0 ${px(22 * bloom)}px rgba(255,107,107,${0.3 * bloom})`
                  : `0 ${px(6)}px ${px(14)}px rgba(0,0,0,0.4)`,
                opacity: Math.min(1, p * 1.4),
                transform: `translateY(${px((1 - p) * 10)}px) scale(${0.93 + p * 0.07})`,
              }}
            />
          );
        })}
      </div>

      <OnBeat at={b[4] ?? 177}>
        <Head size={38}>
          Every instructor knows some of the class used an agent.{' '}
          <em style={{fontStyle: 'normal', color: C.fail}}>None can prove which.</em>
        </Head>
      </OnBeat>
      <OnBeat at={b[6] ?? 265}>
        <p
          style={{
            marginTop: px(18),
            fontFamily: F.mono,
            fontSize: tx(12),
            color: C.faint,
            margin: 0,
            ...NO_LIGATURES,
          }}
        >
          so they grade like nobody did
        </p>
      </OnBeat>
    </Stage>
  );
};
