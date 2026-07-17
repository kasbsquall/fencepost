import React from 'react';
import {Sfx} from './lib/Sfx';
import {sceneOf, beatsIn, DOWNBEATS} from './beats';

/**
 * The SFX cue sheet, as one auditable table at absolute frames.
 *
 * Six SFX sat in public/sfx/ unused for the entire first cut; the script annotated a cue
 * per scene and none were wired. These are placed against the real downbeat grid, not the
 * reviewer's original table — that was built against the old 9-scene layout and every frame
 * in it is now wrong.
 *
 * No whoosh at frame 1 of every scene, deliberately, against the skill's default. This film
 * has a measured 161.5 BPM track, so the drums already mark every cut; a whoosh on top is a
 * second downbeat fighting the first. Worse, whoosh is the only SFX with real 2-6 kHz energy
 * — the exact consonant band the audio mix was rebuilt to protect after the film once
 * transcribed as "codecs". So whoosh appears twice only, both on a clean downbeat with the
 * voice clear. Everywhere else the band is the transition.
 *
 * Volumes are low: the bed plays at ~0.22 in the gaps, and these sit above it without
 * covering the voice. The tonal cues (pop/alert/chime) are all fundamentals under 1.3 kHz,
 * which is why they may sit under a line; whoosh may not.
 */

const db = (scene: number, i: number): number => {
  const s = sceneOf(scene);
  const beats = beatsIn(s.from, s.to);
  return beats[Math.min(i, beats.length - 1)] ?? s.from;
};

type Cue = {at: number; src: string; vol: number};

const CUES: Cue[] = [
  // 1 · the green lie — pop as the dots land, alert on the question
  {at: db(1, 0), src: 'pop.mp3', vol: 0.22},
  {at: db(1, 1), src: 'alert.mp3', vol: 0.24},
  // 2 · the person — whoosh on the cut (downbeat, voice clear), stamp as the marked bloom
  {at: sceneOf(2).from, src: 'whoosh.mp3', vol: 0.12},
  {at: db(2, 1), src: 'pop.mp3', vol: 0.18},
  {at: db(2, 3), src: 'stamp.mp3', vol: 0.22},
  {at: db(2, 4), src: 'alert.mp3', vol: 0.26},
  // 3 · what it is — pop per chain step, then the report lands
  {at: db(3, 1), src: 'pop.mp3', vol: 0.18},
  {at: db(3, 2), src: 'pop.mp3', vol: 0.18},
  {at: db(3, 3), src: 'pop.mp3', vol: 0.18},
  {at: db(3, 4), src: 'pop.mp3', vol: 0.20},
  {at: db(3, 6), src: 'chime.mp3', vol: 0.20},
  // 4 · the mutation — the diff panel, then stamp on the deleted row
  {at: db(4, 1), src: 'pop.mp3', vol: 0.20},
  {at: db(4, 3), src: 'stamp.mp3', vol: 0.26},
  {at: db(4, 4), src: 'pop.mp3', vol: 0.20},
  // 5 · the flip — chime on the false green, stamp on the fail, error alone on the red
  {at: db(5, 1), src: 'chime.mp3', vol: 0.28},
  {at: db(5, 3), src: 'stamp.mp3', vol: 0.26},
  {at: db(5, 5), src: 'error.mp3', vol: 0.34},
  // 6 · synthetic — pop on the disclosure, chime on the passing gate
  {at: db(6, 1), src: 'pop.mp3', vol: 0.18},
  {at: db(6, 4), src: 'chime.mp3', vol: 0.24},
  // 7 · the receipt — alert on the commit line
  {at: db(7, 1), src: 'alert.mp3', vol: 0.28},
  {at: db(7, 3), src: 'stamp.mp3', vol: 0.22},
  // 8 · the student — the one true second whoosh (downbeat, voice clear), pop on the panel
  {at: sceneOf(8).from, src: 'whoosh.mp3', vol: 0.13},
  {at: db(8, 1), src: 'pop.mp3', vol: 0.18},
  // 9 · Codex — pop on the terminal, chime when the generated test appears, pop per flag
  {at: db(9, 0), src: 'pop.mp3', vol: 0.16},
  {at: db(9, 6), src: 'chime.mp3', vol: 0.30},
  {at: db(9, 8), src: 'pop.mp3', vol: 0.16},
  {at: db(9, 8) + 5, src: 'pop.mp3', vol: 0.16},
  // 10 · the proof — pop as the bar grows, alert on the refutation
  {at: db(10, 1), src: 'pop.mp3', vol: 0.20},
  {at: db(10, 4), src: 'alert.mp3', vol: 0.26},
  // 11 · the close — wordmark, chips, then chime on the last downbeat
  {at: db(11, 0), src: 'pop.mp3', vol: 0.18},
  {at: db(11, 1), src: 'pop.mp3', vol: 0.14},
  {at: DOWNBEATS[DOWNBEATS.length - 1] - 20, src: 'chime.mp3', vol: 0.34},
];

export const Cues: React.FC = () => (
  <>
    {CUES.map((c, i) => (
      <Sfx key={i} src={c.src} at={c.at} vol={c.vol} />
    ))}
  </>
);
