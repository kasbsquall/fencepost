import React from 'react';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker, Head} from '../Stage';

/**
 * Scene 6 — synthetic, relocated.
 *
 * This used to open the film's third scene, at 0:26, and it deflated everything after it.
 * At 0:26 the viewer cannot name the product yet, so the first assertive thing they hear
 * about Fencepost is an apology for it, and they spent the flip discounting what they were
 * about to see. Same words, wrong place.
 *
 * Here, just after the flip, the judge has watched the mutant get caught and is asking
 * whether it was rigged. The disclosure answers before they finish the thought. Early it is
 * a disclaimer; late it is a dare — and it hands them the way to check for themselves.
 */
export const Scene6: React.FC = () => {
  const s = sceneOf(6);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);

  return (
    <Stage tint={C.pass} intensity={0.55}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker color={C.pass}>check our work</Kicker>
      </OnBeat>
      <OnBeat at={b[1] ?? 45}>
        <Head size={40}>
          This student is <em style={{fontStyle: 'normal', color: C.pass}}>synthetic.</em> We
          built them so you can check every number.
        </Head>
      </OnBeat>

      <OnBeat at={b[4] ?? 176} y={10}>
        <div
          style={{
            marginTop: px(30),
            border: `1px solid ${C.line}`,
            borderRadius: px(10),
            background: C.sunk,
            padding: `${px(18)}px ${px(20)}px`,
            fontFamily: F.mono,
            fontSize: tx(11.5),
            color: C.dim,
            boxShadow: `0 ${px(20)}px ${px(46)}px rgba(0,0,0,0.5)`,
            ...NO_LIGATURES,
          }}
        >
          <span style={{color: C.faint}}>$ </span>
          pytest tests/integration
          <span style={{color: C.pass}}>{'   → 2 passed, no API key'}</span>
        </div>
      </OnBeat>
    </Stage>
  );
};
