import {useCurrentFrame, useVideoConfig, spring, interpolate, OffthreadVideo, staticFile} from 'remotion';
import {CameraMotionBlur} from '@remotion/motion-blur';
import React from 'react';
import {C, F} from '../design';

// A real screen-recording (Playwright capture) shown inside a tilted 3D browser
// window — motion, not a static screenshot. The clip loops/trims to the scene.
export const VideoShot3D: React.FC<{
  src: string;
  width?: number;
  url?: string;
  delay?: number;
  tiltX?: number;
  tiltY?: number;
  startFrom?: number;
  zoom?: number; // Ken Burns target scale over the scene (e.g. 1.08)
  blur?: boolean; // cinematic motion blur on the move
}> = ({src, width = 1180, url = 'localhost:8765/report', delay = 0, tiltX = 5, tiltY = -12, startFrom = 0, zoom = 1.09, blur = true}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const p = spring({frame: frame - delay, fps, config: {damping: 18, stiffness: 90, mass: 0.9}});
  const y = interpolate(p, [0, 1], [90, 0]);
  const rx = interpolate(p, [0, 1], [tiltX + 8, tiltX]);
  const ry = interpolate(p, [0, 1], [tiltY - 10, tiltY]);
  const ken = interpolate(frame, [0, durationInFrames], [1, zoom], {extrapolateRight: 'clamp'});
  const scale = interpolate(p, [0, 1], [0.92, 1]) * ken;
  const inner = (
    <div style={{perspective: 2200, perspectiveOrigin: '50% 40%'}}>
      <div
        style={{
          width,
          transform: `translateY(${y}px) rotateX(${rx}deg) rotateY(${ry}deg) scale(${scale})`,
          opacity: p,
          borderRadius: 18,
          overflow: 'hidden',
          background: C.bg,
          boxShadow: `0 ${70}px ${130}px rgba(0,0,0,0.62), 0 ${12}px ${30}px rgba(0,0,0,0.5)`,
          border: `1px solid ${C.line}`,
        }}
      >
        <div style={{height: 46, background: C.panel, borderBottom: `1px solid ${C.line}`, display: 'flex', alignItems: 'center', gap: 9, padding: '0 18px'}}>
          {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
            <div key={c} style={{width: 12, height: 12, borderRadius: 99, background: c}} />
          ))}
          <div style={{marginLeft: 14, flex: 1, maxWidth: 440, height: 28, borderRadius: 8, background: C.sunk, display: 'flex', alignItems: 'center', padding: '0 14px', color: C.dim, fontFamily: F.sans, fontSize: 14, fontWeight: 500}}>
            <span style={{color: C.pass, fontSize: 12, marginRight: 8}}>●</span>
            {url}
          </div>
        </div>
        <OffthreadVideo src={staticFile(src)} startFrom={startFrom} muted style={{width: '100%', display: 'block'}} />
      </div>
    </div>
  );
  return blur ? (
    <CameraMotionBlur shutterAngle={120} samples={6}>
      {inner}
    </CameraMotionBlur>
  ) : (
    inner
  );
};
