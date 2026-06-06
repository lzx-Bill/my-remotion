import { Composition } from "remotion";
import { DEFAULT_VIDEO_CONFIG } from "../../common/video";
import { PythagoreanTheorem } from "./PythagoreanTheorem";
import { PythagoreanCover, pythagoreanCoverSchema } from "./PythagoreanCover";
import { PythagoreanOutro, pythagoreanOutroSchema } from "./PythagoreanOutro";
import { pythagoreanData } from "./data";

const TOTAL_CONTENT_S = pythagoreanData.sections.reduce((a, s) => a + s.durationS, 0);

const COVER_DURATION_S = 5;
const OUTRO_DURATION_S = 6;

export const PythagoreanTheoremCompositions: React.FC = () => {
  return (
    <>
      {/* 0. 封面 (5s) */}
      <Composition
        id="Pythagorean-Cover"
        component={PythagoreanCover}
        durationInFrames={Math.round(COVER_DURATION_S * DEFAULT_VIDEO_CONFIG.fps)}
        fps={DEFAULT_VIDEO_CONFIG.fps}
        width={DEFAULT_VIDEO_CONFIG.width}
        height={DEFAULT_VIDEO_CONFIG.height}
        schema={pythagoreanCoverSchema}
        defaultProps={{
          title: pythagoreanData.title,
          subtitle: pythagoreanData.subtitle,
          accentColor: pythagoreanData.accentColor,
          background: pythagoreanData.storyBg,
          logoEmoji: "📐",
        }}
      />

      {/* 1. 主体内容 (6 段, ~187s) */}
      <Composition
        id="PythagoreanTheorem"
        component={PythagoreanTheorem}
        durationInFrames={Math.round(TOTAL_CONTENT_S * DEFAULT_VIDEO_CONFIG.fps)}
        fps={DEFAULT_VIDEO_CONFIG.fps}
        width={DEFAULT_VIDEO_CONFIG.width}
        height={DEFAULT_VIDEO_CONFIG.height}
        defaultProps={pythagoreanData}
      />

      {/* 2. 片尾 (6s) */}
      <Composition
        id="Pythagorean-Outro"
        component={PythagoreanOutro}
        durationInFrames={Math.round(OUTRO_DURATION_S * DEFAULT_VIDEO_CONFIG.fps)}
        fps={DEFAULT_VIDEO_CONFIG.fps}
        width={DEFAULT_VIDEO_CONFIG.width}
        height={DEFAULT_VIDEO_CONFIG.height}
        schema={pythagoreanOutroSchema}
        defaultProps={{
          title: pythagoreanData.title,
          subtitle: pythagoreanData.subtitle,
          accentColor: pythagoreanData.accentColor,
          background: pythagoreanData.modernBg,
          bgmFile: "assets/cases/pythagorean-theorem/audio/outro-bgm.mp3",
          bgmVolume: 0.5,
          nextEpisodeHint: "下一期:相似三角形",
        }}
      />
    </>
  );
};
