import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from './design';
import {Backdrop} from './lib/Backdrop';

/**
 * Every scene's frame.
 *
 * This was one line — `background: C.bg` — with `justifyContent: 'center'` and no
 * `alignItems`, which parked a left-ragged column in the upper-left of a flat near-black
 * 1920x1080 and left 87% of the opening frame as dead pixels. The client called the film
 * dark and weird. The palette was never the problem: nothing cast a shadow, so there was no
 * light, so there was no depth, and an empty frame reads as a dark one.
 *
 * `tint` carries the colour story: red where the problem lives, green where the tool stays
 * silent, and dropped to a low intensity under the product's own recorded UI so a real
 * screen capture is never colour-cast by the film's own lighting.
 */
export const Stage: React.FC<{
  children: React.ReactNode;
  pad?: number;
  tint?: string;
  intensity?: number;
}> = ({children, pad = 100, tint = C.fail, intensity = 1}) => (
  <AbsoluteFill style={{fontFamily: F.sans, color: C.ink}}>
    <Backdrop tint={tint} intensity={intensity} />
    <AbsoluteFill style={{padding: px(pad), justifyContent: 'center', alignItems: 'center'}}>
      <div style={{width: '100%', maxWidth: px(1000), display: 'flex', flexDirection: 'column'}}>
        {children}
      </div>
    </AbsoluteFill>
  </AbsoluteFill>
);

/**
 * Reveal on a beat, with weight.
 *
 * `damping: 200` is critically damped: no overshoot, no snap, no character. The first cut
 * used it for every chip, row, headline and flag across 2:24 — one animation, sixty uses,
 * which is "muy básico" stated precisely. These are the template's values: things now
 * arrive rather than appear.
 */
export const OnBeat: React.FC<{
  at: number;
  children: React.ReactNode;
  y?: number;
  inline?: boolean;
}> = ({at, children, y = 16, inline = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - at, fps, config: {damping: 14, stiffness: 130, mass: 0.7}});
  return (
    <div
      style={{
        opacity: Math.min(1, s * 1.4),
        transform: `translateY(${px((1 - s) * y)}px) scale(${0.985 + s * 0.015})`,
        // A child's alignSelf never reaches the flex parent through this wrapper, so a chip
        // stretched to the full column width. `inline` lets the wrapper shrink.
        alignSelf: inline ? 'flex-start' : undefined,
      }}
    >
      {children}
    </div>
  );
};

export const Kicker: React.FC<{children: string; color?: string}> = ({children, color = C.faint}) => (
  <div
    style={{
      fontFamily: F.mono,
      fontSize: tx(11.5),
      letterSpacing: '.11em',
      textTransform: 'uppercase',
      color,
      marginBottom: px(16),
      ...NO_LIGATURES,
    }}
  >
    {children}
  </div>
);

export const Head: React.FC<{children: React.ReactNode; size?: number}> = ({children, size = 44}) => (
  <h1
    style={{
      fontSize: tx(size),
      lineHeight: 1.08,
      letterSpacing: '-.035em',
      fontWeight: 650,
      maxWidth: '20ch',
      margin: 0,
    }}
  >
    {children}
  </h1>
);
