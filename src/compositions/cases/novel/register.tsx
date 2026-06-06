import { Composition } from "remotion";
import { useMemo } from "react";
import manifestJson from "../../../../data/cases/novel/chunks/manifest.json";
import configJson from "../../../../data/cases/novel/configs/paisheng.json";
import { DEFAULT_VIDEO_CONFIG } from "../../common/video";
import { NovelScene, novelSceneSchema } from "./NovelScene";

// =====================================================================
// 案例配置: 单本小说一份 configs/<name>.json
// 切换小说 = 改 ACTIVE_CASE 常量(或设置 NOVEL_CASE 环境变量)
// =====================================================================
const ACTIVE_CASE = "paisheng";

type Cue = { start: number; end: number; text: string };
type ManifestItem = {
  index: number;
  chapter: string;
  cues?: Cue[];
  image_url?: string;
  image_urls?: string[];        // 段内多图(优先用)
  image_change_interval_s?: number; // 切换间隔(秒), 默认 22
  real_duration_s?: number;
  frames_at_30fps?: number;
};

type Chapter = {
  id: string;
  title: string;
  title_en: string;
  sceneEmoji: string;
  bgColor1: string;
  bgColor2: string;
};

type NovelConfig = {
  name: string;
  title: string;
  subtitle: string;
  total_episodes: number;
  chapters: Chapter[];
  cover: {
    chapter_label: string;
    scene_image_url: string;
    subtitles: string[];
  };
  outro: {
    chapter_label: string;
    audio_file: string;
    audio_duration_s: number;
    sceneEmoji: string;
    bgColor1: string;
    bgColor2: string;
    subtitles: string[];
  };
  video: {
    cover_duration_s: number;
    outro_duration_s: number;
  };
};

const manifest = manifestJson as ManifestItem[];
const config = configJson as NovelConfig;

// 章节视觉表 (从 config.chapters 读,不再硬编码)
const chapterVisuals: Record<string, { bgColor1: string; bgColor2: string; sceneEmoji: string }> =
  Object.fromEntries(
    config.chapters.map((ch) => [
      ch.title,
      { bgColor1: ch.bgColor1, bgColor2: ch.bgColor2, sceneEmoji: ch.sceneEmoji },
    ]),
  );

// 章节 ID 后缀 (从 config.chapters 读,中文标题直接用,转拼音短码作 fallback)
// Remotion 只允许 Composition ID 含 a-z A-Z 0-9 CJK -, 所以要过滤掉括号/空白等
const chapterIdSuffix: Record<string, string> = Object.fromEntries(
  config.chapters.map((ch) => {
    // 取标题最后一段 (去掉"一、" "二、" 这种序号) 作为 ID
    const suffix = ch.title
      .replace(/^[一二三四五六七八九十]+、/, "")
      .replace(/[()（）\[\]【】\s·.,，。]/g, "")  // 过滤 Remotion 不允许的字符
      .trim();
    return [ch.title, suffix || ch.title];
  }),
);

const audioFileFor = (index: number) =>
  `assets/cases/novel/audio/chunks/${String(index).padStart(3, "0")}.mp3`;

// ===== 结构件:封面 =====
const COVER_CONFIG = {
  id: "Novel-Cover",
  durationInFrames: config.video.cover_duration_s * DEFAULT_VIDEO_CONFIG.fps,
  cues: config.cover.subtitles.map((text, i, arr) => {
    const dur = config.video.cover_duration_s / arr.length;
    return { start: i * dur, end: (i + 1) * dur, text };
  }),
};

// ===== 结构件:片尾 =====
const OUTRO_CONFIG = {
  id: "Novel-Outro",
  chapter_label: config.outro.chapter_label,
  durationInFrames: config.video.outro_duration_s * DEFAULT_VIDEO_CONFIG.fps,
  audioFile: `assets/cases/novel/audio/${config.outro.audio_file}`,
  audioDuration: config.outro.audio_duration_s,
  cues: config.outro.subtitles.map((text, i, arr) => {
    const dur = config.outro.audio_duration_s / arr.length;
    return { start: i * dur, end: (i + 1) * dur, text };
  }),
  bgColor1: config.outro.bgColor1,
  bgColor2: config.outro.bgColor2,
  sceneEmoji: config.outro.sceneEmoji,
};

export const NovelCompositions: React.FC = () => {
  // 动态 Composition 数量 = 1 封面 + manifest.length 内容 + 1 片尾
  const defaultChapterVisuals = chapterVisuals[config.chapters[0]?.title];

  return (
    <>
      {/* 封面:结构件,放在最前,固定 5s */}
      <Composition
        id={COVER_CONFIG.id}
        component={NovelScene}
        durationInFrames={COVER_CONFIG.durationInFrames}
        schema={novelSceneSchema}
        defaultProps={{
          chapter: config.cover.chapter_label,
          sceneIndex: 0,
          sceneTotal: 1,
          cues: COVER_CONFIG.cues,
          audioFile: undefined,
          audioDuration: COVER_CONFIG.durationInFrames / DEFAULT_VIDEO_CONFIG.fps,
          bgColor1: defaultChapterVisuals?.bgColor1 ?? "#1a0f0a",
          bgColor2: defaultChapterVisuals?.bgColor2 ?? "#0a0508",
          sceneEmoji: defaultChapterVisuals?.sceneEmoji ?? "🏮",
          sceneImage: config.cover.scene_image_url,
        }}
        {...DEFAULT_VIDEO_CONFIG}
      />

      {/* 内容段:动态来自 manifest */}
      {manifest.map((item) => {
        const visuals = chapterVisuals[item.chapter] ?? defaultChapterVisuals;
        const audioDuration =
          item.real_duration_s ??
          (item.frames_at_30fps ?? DEFAULT_VIDEO_CONFIG.fps) / DEFAULT_VIDEO_CONFIG.fps;
        const durationInFrames =
          item.frames_at_30fps ?? Math.max(1, Math.round(audioDuration * DEFAULT_VIDEO_CONFIG.fps));
        const compositionId = `Novel-${String(item.index).padStart(2, "0")}-${
          chapterIdSuffix[item.chapter] ?? String(item.index)
        }`;

        return (
          <Composition
            key={compositionId}
            id={compositionId}
            component={NovelScene}
            durationInFrames={durationInFrames}
            schema={novelSceneSchema}
            defaultProps={{
              chapter: item.chapter,
              sceneIndex: item.index,
              sceneTotal: manifest.length,
              cues: item.cues ?? [],
              audioFile: audioFileFor(item.index),
              audioDuration,
              bgColor1: visuals?.bgColor1 ?? "#1a0f0a",
              bgColor2: visuals?.bgColor2 ?? "#0a0508",
          sceneEmoji: visuals?.sceneEmoji ?? "🏮",
          sceneImage: item.image_url,
          imageUrls: item.image_urls,
          imageChangeIntervalS: item.image_change_interval_s,
        }}
            {...DEFAULT_VIDEO_CONFIG}
          />
        );
      })}

      {/* 片尾:结构件,放在最后,固定 Ns */}
      <Composition
        id={OUTRO_CONFIG.id}
        component={NovelScene}
        durationInFrames={OUTRO_CONFIG.durationInFrames}
        schema={novelSceneSchema}
        defaultProps={{
          chapter: OUTRO_CONFIG.chapter_label ?? "片尾",
          sceneIndex: 0,
          sceneTotal: 1,
          cues: OUTRO_CONFIG.cues,
          audioFile: OUTRO_CONFIG.audioFile,
          audioDuration: OUTRO_CONFIG.audioDuration,
          bgColor1: OUTRO_CONFIG.bgColor1,
          bgColor2: OUTRO_CONFIG.bgColor2,
          sceneEmoji: OUTRO_CONFIG.sceneEmoji,
          sceneImage: undefined,
        }}
        {...DEFAULT_VIDEO_CONFIG}
      />
    </>
  );
};

// 旧名保留,避免 Root.tsx 改名时漏改
export const NovelZhongKuiCompositions = NovelCompositions;
// 新名,推荐用
export { ACTIVE_CASE };
