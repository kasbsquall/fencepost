import React from 'react';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import {DiffRow} from '../components';
import facts from '../../public/casts/facts.json';

const H = facts.hero;
const K = facts.commit;

/**
 * Scene 4 — the mutation.
 *
 * Not one value here is typed. The first cut hand-wrote this diff and shipped one that does
 * not exist: the label said 38, the code belonged to line 39, and the two halves came from
 * different real mutants. The voiceover said "line thirty-nine" while the screen said 38 and
 * nobody noticed for a day, because a constant in a .tsx file looks exactly as confident
 * whether it was measured or guessed. Everything now comes from tools/film_facts.py, which
 * reads .fp_demo and refuses to emit anything if the mutant is not in the run.
 *
 * The `git blame` command is on screen because the voiceover no longer says it: "Git"
 * synthesised as "get" across two takes and two Whisper models, and they are a minimal pair
 * the language model wins every time. The jargon lives where it is read, not where it is
 * heard, and the claim survives intact.
 */
export const Scene4: React.FC = () => {
  const s = sceneOf(4);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);

  return (
    <Stage tint={C.fail} intensity={0.7}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>{`git blame -M -C -C -w  ·  ${H.path}`}</Kicker>
      </OnBeat>

      <OnBeat at={b[1] ?? 44} y={10}>
        <div
          style={{
            border: `1px solid ${C.line}`,
            borderRadius: px(12),
            background: C.panel,
            overflow: 'hidden',
            boxShadow: `0 ${px(30)}px ${px(70)}px rgba(0,0,0,0.55)`,
          }}
        >
          {Object.entries(H.context_before).map(([n, text]) => (
            <DiffRow key={n} n={n} scale={1.7}>
              {text}
            </DiffRow>
          ))}
          <OnBeat at={(b[3] ?? 133) - (b[1] ?? 44)} y={0}>
            <DiffRow n={String(H.line)} kind="del" scale={1.7}>
              {H.del}
            </DiffRow>
          </OnBeat>
          <OnBeat at={(b[4] ?? 177) - (b[1] ?? 44)} y={0}>
            <DiffRow n={String(H.line)} kind="add" scale={1.7}>
              {H.add}
            </DiffRow>
          </OnBeat>
          {Object.entries(H.context_after).map(([n, text]) => (
            <DiffRow key={n} n={n} scale={1.7}>
              {text}
            </DiffRow>
          ))}
        </div>
      </OnBeat>

      {/* The provenance, quiet, under the diff. The receipt gets its own scene later; here
          it only has to establish that the line is theirs. */}
      <OnBeat at={b[5] ?? 221}>
        <div
          style={{
            marginTop: px(18),
            fontFamily: F.mono,
            fontSize: tx(10.5),
            color: C.faint,
            ...NO_LIGATURES,
          }}
        >
          line {H.line} · commit <span style={{color: C.dim}}>{K.sha}</span> · {K.date} ·{' '}
          <span style={{color: C.dim}}>"{K.subject}"</span>
        </div>
      </OnBeat>
    </Stage>
  );
};
