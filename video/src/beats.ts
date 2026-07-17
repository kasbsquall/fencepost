/**
 * The beat grid and the scene layout, both measured, neither chosen.
 *
 * Suno delivered 161.5 BPM against a requested 162, which is close enough that computing
 * beats as `frame % 11.15` would look right for eight bars and drift visibly by the end.
 * librosa found the real beats; these are those, in frames. An element that appears on
 * frame 47 lands on the beat because 47 is where the beat actually is.
 *
 * The windows used to be typed here, copied off the script's timestamps. Five of eleven
 * scenes did not fit the takes that actually got synthesised. They now come from
 * tools/layout_film.py, which reads the real voiceover durations and the real downbeats
 * and refuses to emit a layout where a scene overruns its window.
 */

import grid from '../public/casts/beatgrid_punk.json';
import layout from './layout.json';

export const TEMPO = grid.tempo as number;
export const FPS = grid.fps as number;
export const BEATS = grid.beatFrames as number[];
export const DOWNBEATS = grid.downbeatFrames as number[];
export const LIFT = grid.liftFrame as number;

/** Frames per bar. 161.5 BPM -> 1.486s -> ~44.6 frames. */
export const BAR = (60 / TEMPO) * 4 * FPS;

/** The next downbeat strictly after `frame`. */
export const nextDownbeat = (frame: number): number =>
  DOWNBEATS.find((d) => d > frame) ?? DOWNBEATS[DOWNBEATS.length - 1];

/** Downbeats inside [from, to), absolute frames. Reveals hang off these. */
export const beatsIn = (from: number, to: number): number[] =>
  DOWNBEATS.filter((d) => d >= from && d < to);

export type Scene = {n: number; from: number; to: number; voAt: number; hold: number};

/** Generated. Every boundary is a real downbeat and every take fits its window. */
export const SCENES = layout.scenes as Scene[];
export const DURATION = layout.durationInFrames as number;

export const sceneOf = (n: number): Scene => {
  const s = SCENES.find((x) => x.n === n);
  if (!s) throw new Error(`no scene ${n} in layout.json`);
  return s;
};
