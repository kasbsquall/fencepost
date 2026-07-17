import React from 'react';
import {C, px} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import {VideoShot3D} from '../lib/VideoShot3D';

/**
 * Scene 8 — the student.
 *
 * The one real recording of the student view. The first cut showed it for twelve seconds
 * with a visible `I donâ€™t know` mojibake baked into the take — a bug the app had already
 * fixed, still on screen because the recording predated the fix. probe_hd.mp4 is a fresh
 * capture, dark mode, at delivery resolution, of the real flow: the student answers before
 * any evidence is shown, and either choice commits their answer first.
 *
 * Full frame, per the reviewers: a small mockup in a sea of empty space reads unfinished,
 * and this is the beat that proves the student half of the product exists.
 */
export const Scene8: React.FC = () => {
  const s = sceneOf(8);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);

  return (
    <Stage tint={C.fail} intensity={0.4} pad={64}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>they answer before they see anything</Kicker>
      </OnBeat>
      <OnBeat at={b[1] ?? 44} y={0}>
        <VideoShot3D
          src="raw/probe_hd.mp4"
          width={1360}
          url="localhost:8766 · student probe"
          delay={b[1] ?? 44}
          tiltX={3}
          tiltY={-6}
          zoom={1.04}
          blur={false}
        />
      </OnBeat>
    </Stage>
  );
};
