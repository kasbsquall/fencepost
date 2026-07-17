import React from 'react';
import {C, px} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Head} from '../Stage';
import {Terminal} from '../components';
import cast from '../../public/casts/pytest_student.json';

/**
 * Scene 1 — the green lie.
 *
 * The first cut landed the terminal on frame 4 and the headline on frame 138, then held
 * 7.4 seconds of nothing in the window where a judge decides whether to keep watching. The
 * script had already called it: "a green terminal is the most common opening image in a
 * hackathon reel; if my thumb is hovering, it hovers there. Get the words on screen fast."
 * The note was written and the opposite shipped. The headline is now on the second downbeat.
 *
 * The terminal replays a real capture — real bytes, real timings, from `pytest -q` in the
 * fixture. `10 passed` is not a graphic.
 */
export const Scene1: React.FC = () => {
  const s = sceneOf(1);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);

  return (
    <Stage tint={C.pass} intensity={0.5}>
      <div style={{display: 'flex', flexDirection: 'column', gap: px(38), maxWidth: px(820)}}>
        <OnBeat at={b[0] ?? 0}>
          <Terminal cmd={cast.cmd} events={cast.events} startFrame={b[0] ?? 0} fps={30} scale={1.6} />
        </OnBeat>
        <OnBeat at={b[1] ?? 44}>
          <Head size={44}>
            Ten tests pass.{' '}
            <em style={{fontStyle: 'normal', color: C.faint}}>So did they understand it?</em>
          </Head>
        </OnBeat>
      </div>
    </Stage>
  );
};
