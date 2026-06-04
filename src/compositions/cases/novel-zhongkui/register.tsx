import { Composition } from "remotion";
import manifestJson from "../../../../data/cases/novel-zhongkui/chunks/manifest.json";
import { DEFAULT_VIDEO_CONFIG } from "../../common/video";
import { NovelScene, novelSceneSchema } from "./NovelScene";

type Cue = {
  start: number;
  end: number;
  text: string;
};

type ManifestItem = {
  index: number;
  chapter: string;
  cues?: Cue[];
  image_url?: string;
  real_duration_s?: number;
  frames_at_30fps?: number;
};

const manifest = manifestJson as ManifestItem[];

const chapterVisuals: Record<string, { bgColor1: string; bgColor2: string; sceneEmoji: string }> = {
  "一、天师下岗": { bgColor1: "#1a0f0a", bgColor2: "#0a0508", sceneEmoji: "🏮" },
  "二、面试": { bgColor1: "#0a1a12", bgColor2: "#080f0a", sceneEmoji: "📄" },
  "三、首播": { bgColor1: "#1a0a14", bgColor2: "#0e050d", sceneEmoji: "📱" },
  "四、爆火": { bgColor1: "#241106", bgColor2: "#0f0604", sceneEmoji: "🔥" },
  "五、真假": { bgColor1: "#081822", bgColor2: "#050b10", sceneEmoji: "🪞" },
  "六、停播": { bgColor1: "#131313", bgColor2: "#050505", sceneEmoji: "⏸" },
  "七、重新出发": { bgColor1: "#102018", bgColor2: "#08100d", sceneEmoji: "🌱" },
  "八、最后一战": { bgColor1: "#220d0d", bgColor2: "#0d0404", sceneEmoji: "⚔" },
  "九、尾声": { bgColor1: "#101622", bgColor2: "#05080d", sceneEmoji: "🌘" },
};

const chapterIdSuffix: Record<string, string> = {
  "一、天师下岗": "天师下岗",
  "二、面试": "面试",
  "三、首播": "首播",
  "四、爆火": "爆火",
  "五、真假": "真假",
  "六、停播": "停播",
  "七、重新出发": "重新出发",
  "八、最后一战": "最后一战",
  "九、尾声": "尾声",
};

const audioFileFor = (index: number) => `assets/cases/novel-zhongkui/audio/chunks/${String(index).padStart(3, "0")}.mp3`;

export const NovelZhongKuiCompositions: React.FC = () => {
  return (
    <>
      {manifest.map((item) => {
        const visuals = chapterVisuals[item.chapter] ?? chapterVisuals["一、天师下岗"];
        const audioDuration = item.real_duration_s ?? (item.frames_at_30fps ?? DEFAULT_VIDEO_CONFIG.fps) / DEFAULT_VIDEO_CONFIG.fps;
        const durationInFrames = item.frames_at_30fps ?? Math.max(1, Math.round(audioDuration * DEFAULT_VIDEO_CONFIG.fps));
        const compositionId = `Novel-${String(item.index).padStart(2, "0")}-${chapterIdSuffix[item.chapter] ?? item.index}`;

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
              bgColor1: visuals.bgColor1,
              bgColor2: visuals.bgColor2,
              sceneEmoji: visuals.sceneEmoji,
              sceneImage: item.image_url,
            }}
            {...DEFAULT_VIDEO_CONFIG}
          />
        );
      })}
    </>
  );
};
