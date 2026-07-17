import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// The film is dark, flat, and full of type. Default CRF banded the gradients behind
// the panels and softened 13px mono. 16 holds both.
Config.setCrf(16);
