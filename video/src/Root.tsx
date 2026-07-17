import React from 'react';
import {Composition} from 'remotion';
import {Film} from './Film';
import {DURATION, sceneOf} from './beats';
import {Scene1} from './scenes/Scene1';
import {Scene2} from './scenes/Scene2';
import {Scene3} from './scenes/Scene3';
import {Scene4} from './scenes/Scene4';
import {Scene5} from './scenes/Scene5';
import {Scene6} from './scenes/Scene6';
import {Scene7} from './scenes/Scene7';
import {Scene8} from './scenes/Scene8';
import {Scene9} from './scenes/Scene9';
import {Scene10} from './scenes/Scene10';
import {Scene11} from './scenes/Scene11';

const S = [Scene1, Scene2, Scene3, Scene4, Scene5, Scene6, Scene7, Scene8, Scene9, Scene10, Scene11];

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Film" component={Film} durationInFrames={DURATION} fps={30} width={1920} height={1080} />
    {S.map((Comp, i) => {
      const n = i + 1;
      const s = sceneOf(n);
      return <Composition key={n} id={`S${n}`} component={Comp} durationInFrames={s.to - s.from} fps={30} width={1920} height={1080} />;
    })}
  </>
);
