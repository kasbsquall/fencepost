import {Audio, Sequence, staticFile} from 'remotion';
import React from 'react';

// A one-shot micro-interaction sound placed at a local frame offset within a scene.
export const Sfx: React.FC<{src: string; at: number; vol?: number}> = ({src, at, vol = 0.4}) => (
  <Sequence from={at} durationInFrames={60} layout="none">
    <Audio src={staticFile(`sfx/${src}`)} volume={vol} />
  </Sequence>
);
