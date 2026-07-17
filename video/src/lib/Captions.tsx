import {useCurrentFrame, useVideoConfig} from 'remotion';
import React from 'react';
import capsRaw from '../../public/casts/captions.json';
import {C, F, px} from '../design';

type Word = {t: number; e: number; w: string};
const caps = capsRaw as Word[];

// Group words into readable lines (~46 chars, break on sentence end).
type Line = {start: number; end: number; words: Word[]};
const LINES: Line[] = (() => {
  const lines: Line[] = [];
  let cur: Word[] = [];
  for (const c of caps) {
    cur.push(c);
    const txt = cur.map((x) => x.w).join(' ');
    const endsSent = /[.?!]$/.test(c.w);
    if (txt.length >= 46 || (endsSent && cur.length >= 3)) {
      lines.push({start: cur[0].t, end: cur[cur.length - 1].e, words: cur});
      cur = [];
    }
  }
  if (cur.length) lines.push({start: cur[0].t, end: cur[cur.length - 1].e, words: cur});
  return lines;
})();

// Burned-in karaoke captions.
export const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const line = LINES.find((l) => t >= l.start - 0.12 && t <= l.end + 0.35);
  if (!line) return null;
  return (
    <div
      style={{
        position: 'absolute',
        bottom: px(46),
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          maxWidth: px(880),
          padding: `${px(13)}px ${px(28)}px`,
          borderRadius: px(12),
          background: 'rgba(11,12,14,0.82)',
          border: `1px solid ${C.line}`,
          boxShadow: '0 18px 50px rgba(0,0,0,0.35)',
          textAlign: 'center',
          fontFamily: F.sans,
          fontWeight: 700,
          fontSize: px(24),
          lineHeight: 1.28,
        }}
      >
        {line.words.map((w, i) => {
          const active = t >= w.t - 0.04;
          return (
            <span key={i} style={{color: active ? C.ink : C.faint}}>
              {w.w}{' '}
            </span>
          );
        })}
      </div>
    </div>
  );
};
