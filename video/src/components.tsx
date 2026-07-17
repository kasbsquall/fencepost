import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, F, NO_LIGATURES, px} from './design';

/**
 * The Offset Post. Two rails, three posts, and one post pushed out of line in red — the
 * whole product in a glyph: the fence stands, one member is off, and that is the thing
 * worth looking at. Traced from the mockup's SVG rather than redrawn.
 */
export const Mark: React.FC<{size?: number}> = ({size = px(19)}) => (
  <svg viewBox="0 0 24 24" fill="none" style={{width: size, height: size}}>
    <path d="M2 8h20M2 16h20" stroke={C.ink} strokeWidth={1.5} />
    <path d="M6 3v18M12 3v18M18 3v18" stroke={C.ink} strokeWidth={1.5} />
    <path d="M12 9v18" stroke={C.fail} strokeWidth={2.6} />
  </svg>
);

export const Wordmark: React.FC<{size?: number}> = ({size = px(14)}) => (
  <span
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: px(9),
      fontFamily: F.mono,
      fontSize: size,
      fontWeight: 600,
      letterSpacing: '-.02em',
      color: C.ink,
      ...NO_LIGATURES,
    }}
  >
    <Mark size={size * 1.35} />
    <span>
      fence<span style={{color: C.fail}}>post</span>
    </span>
  </span>
);

/** A diff row in the product's exact grammar: line number, sign gutter, code. */
export const DiffRow: React.FC<{
  n?: string;
  kind?: 'del' | 'add' | 'ctx';
  children: string;
  scale?: number;
}> = ({n = '', kind = 'ctx', children, scale = 1}) => {
  const bg = kind === 'del' ? C.failBg : kind === 'add' ? C.passBg : 'transparent';
  const sign = kind === 'del' ? '−' : kind === 'add' ? '+' : '';
  const signColor = kind === 'del' ? C.fail : kind === 'add' ? C.pass : C.faint;
  const ink = kind === 'del' ? C.delInk : kind === 'add' ? C.addInk : C.ink;
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `${px(46 * scale)}px ${px(20 * scale)}px 1fr`,
        alignItems: 'baseline',
        background: bg,
        fontFamily: F.mono,
        fontSize: px(13 * scale),
        ...NO_LIGATURES,
      }}
    >
      <span
        style={{
          color: kind === 'add' ? 'transparent' : C.faint,
          textAlign: 'right',
          padding: `${px(4 * scale)}px ${px(10 * scale)}px ${px(4 * scale)}px 0`,
        }}
      >
        {n}
      </span>
      <span style={{textAlign: 'center', color: signColor}}>{sign}</span>
      <span style={{padding: `${px(4 * scale)}px ${px(12 * scale)}px`, whiteSpace: 'pre', color: ink}}>
        {children}
      </span>
    </div>
  );
};

/**
 * A run row: who ran, what happened, how long. Equal rank — no CI glyphs on a person.
 *
 * `who` is a fixed width, not a minimum. The scene's whole argument is that the same code
 * produced two different verdicts, and the eye only reads that if `passed` and `failed`
 * share a column. With `minWidth`, "Test written by gpt-5.6-terra" ran long and pushed its
 * verb out of line with the one above it, which is the comparison the shot exists to make.
 */
export const RunRow: React.FC<{who: string; verb: string; ok: boolean; t: string; scale?: number}> = ({
  who,
  verb,
  ok,
  t,
  scale = 1,
}) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'baseline',
      gap: px(10 * scale),
      fontFamily: F.mono,
      fontSize: px(13 * scale),
      ...NO_LIGATURES,
    }}
  >
    <span
      style={{
        color: C.dim,
        width: px(250 * scale),
        flexShrink: 0,
        whiteSpace: 'nowrap',
      }}
    >
      {who}
    </span>
    <span style={{fontWeight: 600, color: ok ? C.pass : C.fail}}>{verb}</span>
    <span style={{marginLeft: 'auto', color: C.faint, fontSize: px(11 * scale)}}>{t}</span>
  </div>
);

/**
 * Replays a captured terminal run. Lines appear at the wall-clock offset they actually
 * appeared at, which is why the 12-second gap in the Codex shot is really there: that is
 * the model thinking, and the voiceover talks across it.
 */
export const Terminal: React.FC<{
  cmd: string;
  events: {t: number; s: string}[];
  startFrame: number;
  fps: number;
  scale?: number;
  maxChars?: number;
}> = ({cmd, events, startFrame, fps, scale = 1, maxChars = 200}) => {
  const frame = useCurrentFrame();
  const elapsed = (frame - startFrame) / fps;

  // The command types itself over half a second, then the run starts. Anything faster
  // reads as a cut; anything slower wastes a scene.
  const typed = Math.floor(interpolate(elapsed, [0, 0.5], [0, cmd.length], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  }));

  const shown = events.filter((e) => e.t <= elapsed - 0.5);

  return (
    <div
      style={{
        fontFamily: F.mono,
        fontSize: px(13 * scale),
        lineHeight: 1.65,
        color: C.ink,
        background: C.sunk,
        border: `1px solid ${C.line}`,
        borderRadius: px(10),
        padding: `${px(16)}px ${px(18)}px`,
        whiteSpace: 'pre-wrap',
        ...NO_LIGATURES,
      }}
    >
      <div style={{color: C.dim}}>
        <span style={{color: C.faint}}>$ </span>
        {cmd.slice(0, typed)}
        {typed < cmd.length && elapsed >= 0 ? <span style={{color: C.fail}}>▌</span> : null}
      </div>
      {shown.map((e, i) => (
        <div key={i} style={{color: C.dim}}>
          {e.s.slice(0, maxChars)}
        </div>
      ))}
    </div>
  );
};
