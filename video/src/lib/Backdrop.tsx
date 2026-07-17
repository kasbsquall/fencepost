import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C} from '../design';

/**
 * Layered backdrop. Ported from the hackathon-video template and retinted, because the
 * template's base is indigo (#0D0B24) and this product is a neutral near-black.
 *
 * The first cut of this film used `background: #0B0C0E` — one flat fill, nine scenes. The
 * client called it dark and weird and both readings were fair: a histogram of that cut is
 * a spike at black with a thin spur at #EDEFF2. Nothing cast a shadow, so there was no
 * light, so there was no depth, and the eye reports "empty" as "dark".
 *
 * The palette is not the problem and does not change. What changes is that the black now
 * has structure: a lifted pool behind the content, a masked dot grid for scale, two aurora
 * blobs that drift off `useCurrentFrame()` so every frame moves even when nothing is
 * animating, grain to break the banding at CRF 16, and a vignette to seat it.
 *
 * `tint` carries the colour story: red on the problem beats, green where the tool stays
 * silent, neutral under the product's own UI so the recording is never colour-cast.
 */
export const Backdrop: React.FC<{tint?: string; grid?: boolean; intensity?: number}> = ({
  tint = C.fail,
  grid = true,
  intensity = 1,
}) => {
  const frame = useCurrentFrame();
  // Slow and coprime-ish so the two blobs never visibly re-sync over 2.5 minutes.
  const drift = Math.sin(frame * 0.0071) * 46;
  const drift2 = Math.cos(frame * 0.0053) * 58;

  return (
    <AbsoluteFill style={{overflow: 'hidden', background: C.bg}}>
      {/* A pool of light behind the content, so the frame has a source. */}
      <AbsoluteFill
        style={{
          background:
            `radial-gradient(1400px 950px at 50% 34%, ${tint}1A, transparent 58%),` +
            `linear-gradient(180deg, #131519 0%, ${C.bg} 58%, #060708 100%)`,
        }}
      />

      {grid && (
        <AbsoluteFill
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(237,239,242,0.055) 1.2px, transparent 1.2px)',
            backgroundSize: '46px 46px',
            WebkitMaskImage: 'radial-gradient(circle at 50% 42%, black 0%, transparent 76%)',
            maskImage: 'radial-gradient(circle at 50% 42%, black 0%, transparent 76%)',
            opacity: 0.55,
          }}
        />
      )}

      <div
        style={{
          position: 'absolute',
          left: `calc(12% + ${drift}px)`,
          top: `${-8 + drift2 * 0.08}%`,
          width: 700,
          height: 700,
          borderRadius: 999,
          background: `radial-gradient(circle, ${tint}, transparent 66%)`,
          filter: 'blur(110px)',
          opacity: 0.16 * intensity,
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: `calc(8% + ${drift2}px)`,
          top: '44%',
          width: 560,
          height: 560,
          borderRadius: 999,
          background: `radial-gradient(circle, ${C.pass}, transparent 68%)`,
          filter: 'blur(120px)',
          opacity: 0.07 * intensity,
        }}
      />

      {/* Grain earns its place twice: it breaks the gradient banding that CRF 16 was
          already chosen to fight, and it keeps the flat areas from reading as dead. */}
      <AbsoluteFill style={{opacity: 0.045, mixBlendMode: 'overlay'}}>
        <svg width="100%" height="100%">
          <filter id="fp-grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
          </filter>
          <rect width="100%" height="100%" filter="url(#fp-grain)" />
        </svg>
      </AbsoluteFill>

      <AbsoluteFill style={{boxShadow: 'inset 0 0 420px 130px rgba(0,0,0,0.6)'}} />
    </AbsoluteFill>
  );
};
