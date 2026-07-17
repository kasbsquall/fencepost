import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {C, F, NO_LIGATURES, px, tx} from '../design';
import {beatsIn, sceneOf} from '../beats';
import {Stage, OnBeat, Kicker} from '../Stage';
import {VideoShot3D} from '../lib/VideoShot3D';

/**
 * Scene 3 — the beat that did not exist.
 *
 * Three reviewers read the first cut independently and landed on the same failure, and the
 * client had already said it in one sentence: he did not understand the film. Across 2:24
 * nobody ever said what Fencepost does. The film showed a diff and assumed the viewer would
 * infer mutation-based probing from looking at a red row and a green row. A judge who has
 * never heard of mutation testing cannot tell whether that diff is a bug, a fix, or an
 * attack.
 *
 * So this scene says the mechanism as one causal sentence, in four steps that land on four
 * downbeats, and then it does the thing the first cut never did in 144 seconds: it puts the
 * instructor's real report on screen. At 22s, not 78s.
 *
 * The chain is the argument, so it gets the frame, and the report is the payoff, so it gets
 * the size. `report.mp4` is a real Playwright recording of the real product — the shot list
 * always said so; the first cut rebuilt it in React and left the recording on disk.
 */
export const Scene3: React.FC = () => {
  const s = sceneOf(3);
  const b = beatsIn(s.from, s.to).map((x) => x - s.from);
  const frame = useCurrentFrame();

  const STEPS = [
    {k: 'their line', v: 'a line from their own commit'},
    {k: 'change one', v: 'one character, nothing else'},
    {k: 'run their tests', v: 'the suite they submitted'},
    {k: 'still green', v: 'a gap they never checked'},
  ];

  // The chain is the argument and the report is the payoff, so they do not share the frame:
  // holding both put the report half off the bottom edge. The chain states the mechanism,
  // then recedes and hands the frame over on the downbeat the report lands on.
  const reportAt = b[6] ?? 270;
  const yield_ = interpolate(frame, [reportAt - 8, reportAt + 14], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <Stage tint={C.fail} intensity={0.55} pad={70}>
      {yield_ > 0 ? (
      <div style={{opacity: yield_, position: yield_ < 1 ? "absolute" : undefined}}>
      <OnBeat at={b[0] ?? 0}>
        <Kicker>fencepost does not detect</Kicker>
      </OnBeat>

      <div style={{display: 'flex', gap: px(10), marginBottom: px(26)}}>
        {STEPS.map((step, i) => {
          // One step per downbeat: the sentence is being spoken while the chain builds, so
          // the picture arrives on the drum instead of chasing the voice.
          const at = b[1 + i] ?? 30 + i * 45;
          const on = frame >= at;
          const last = i === STEPS.length - 1;
          return (
            <OnBeat key={step.k} at={at} y={10}>
              <div
                style={{
                  minWidth: px(196),
                  padding: `${px(14)}px ${px(16)}px`,
                  borderRadius: px(10),
                  border: `1px solid ${last && on ? C.fail : C.line}`,
                  background: last && on ? C.failBg : C.panel,
                  boxShadow: on ? `0 ${px(18)}px ${px(40)}px rgba(0,0,0,0.5)` : 'none',
                }}
              >
                <div
                  style={{
                    fontFamily: F.mono,
                    fontSize: tx(9.5),
                    letterSpacing: '.11em',
                    textTransform: 'uppercase',
                    color: last ? C.fail : C.faint,
                    marginBottom: px(7),
                    ...NO_LIGATURES,
                  }}
                >
                  {step.k}
                </div>
                <div style={{fontSize: tx(11), color: C.dim, lineHeight: 1.35}}>{step.v}</div>
              </div>
            </OnBeat>
          );
        })}
      </div>
      </div>
      ) : null}

      {/* The payoff, and the first sighting of the product in the film. Full frame: the
          reviewers were blunt that a small mockup in a sea of empty space reads unfinished,
          and this is the shot the whole scene exists to deliver. */}
      <OnBeat at={reportAt} y={0}>
        {/* 1500 wide put the window 73px past the bottom edge: a 16:9 recording at that
            width is 844 tall, plus 46 of chrome, against ~817 of usable height. Measured,
            not nudged. */}
        <VideoShot3D
          src="raw/report_hd.mp4"
          width={1340}
          url="localhost:8765/report"
          delay={reportAt}
          tiltX={3}
          tiltY={-7}
          zoom={1.05}
          blur={false}
        />
      </OnBeat>
    </Stage>
  );
};
