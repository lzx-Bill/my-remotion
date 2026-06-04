import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// 字幕 cue schema
const cueSchema = z.object({
  start: z.number(),  // 秒
  end: z.number(),
  text: z.string(),
});

export const novelSceneSchema = z.object({
  chapter: z.string(),
  sceneIndex: z.number(),
  sceneTotal: z.number(),
  cues: z.array(cueSchema),     // ASR 时间戳 + 原文文字
  audioFile: z.string(),
  audioDuration: z.number(),
  bgColor1: zColor(),
  bgColor2: zColor(),
  sceneEmoji: z.string(),
  sceneImage: z.string().optional(), // 支持 public/ 相对路径或远程图片 URL
});

export const NovelScene: React.FC<z.infer<typeof novelSceneSchema>> = ({
  chapter,
  sceneIndex,
  sceneTotal,
  cues,
  audioFile,
  audioDuration,
  bgColor1,
  bgColor2,
  sceneEmoji,
  sceneImage,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 当前时间(秒)
  const t = frame / fps;

  // 找当前 cue: t 落在 [start, end] 区间
  let currentCueIndex = 0;
  for (let i = 0; i < cues.length; i++) {
    if (t >= cues[i].start && t < cues[i].end) {
      currentCueIndex = i;
      break;
    }
    // 超过最后一个 cue 还在 t 之后,固定到最后一个
    if (i === cues.length - 1 && t >= cues[i].end) {
      currentCueIndex = i;
    }
  }

  // 入场/离场
  const totalFrames = audioDuration * fps;
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [totalFrames - 30, totalFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const globalOpacity = Math.min(fadeIn, fadeOut);

  // 显示上下文:当前 + 上一条 + 下一条
  const current = cues[currentCueIndex];
  const prev = currentCueIndex > 0 ? cues[currentCueIndex - 1] : null;
  const next = currentCueIndex < cues.length - 1 ? cues[currentCueIndex + 1] : null;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at top, ${bgColor1} 0%, ${bgColor2} 70%, #050510 100%)`,
        fontFamily: 'system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif',
        color: "#FFFFFF",
        opacity: globalOpacity,
      }}
    >
      {/* 配音 */}
      <Audio src={staticFile(audioFile)} />

      {/* 场景图 (全屏背景) */}
      {sceneImage && (
        <>
          <Img
            src={sceneImage}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
          {/* 半透明黑色渐变 — 让字幕更清晰 */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background:
                "linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 30%, rgba(0,0,0,0.1) 60%, rgba(0,0,0,0.6) 100%)",
              pointerEvents: "none",
            }}
          />
        </>
      )}

      {/* 装饰 emoji (仅在没有图时显示) */}
      {!sceneImage && (
        <div
          style={{
            position: "absolute",
            top: 80,
            right: 100,
            fontSize: 220,
            opacity: 0.2,
            filter: "drop-shadow(0 0 40px #FFFFFF60)",
          }}
        >
          {sceneEmoji}
        </div>
      )}

      {/* 章节 + 进度 */}
      <div
        style={{
          position: "absolute",
          top: 50,
          left: 80,
          right: 80,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            fontSize: 24,
            color: "#FFFFFFBB",
            fontWeight: 600,
            letterSpacing: 2,
          }}
        >
          <span style={{ fontSize: 16, color: "#FFFFFF80" }}>●</span>
          <span>{chapter}</span>
        </div>
        <div
          style={{
            fontSize: 20,
            color: "#FFFFFF60",
            fontFamily: "monospace",
            letterSpacing: 1,
          }}
        >
          {String(sceneIndex + 1).padStart(2, "0")} / {String(sceneTotal).padStart(2, "0")}
        </div>
      </div>

      {/* 字幕区: 三行 (上一行 / 当前行 / 下一行) */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 160,
          padding: "0 100px",
          display: "flex",
          flexDirection: "column",
          gap: 18,
          alignItems: "center",
        }}
      >
        {/* 上一条 (已过去,半透明) */}
        {prev && (
          <div
            style={{
              fontSize: 36,
              lineHeight: 1.4,
              color: "#FFFFFF50",
              fontWeight: 400,
              maxWidth: 1600,
              textAlign: "center",
              textShadow: "0 2px 4px #00000060",
            }}
          >
            {prev.text}
          </div>
        )}

        {/* 当前条 (高亮) */}
        {current && (
          <div
            style={{
              fontSize: 60,
              lineHeight: 1.4,
              color: "#FFFFFF",
              fontWeight: 700,
              maxWidth: 1700,
              textAlign: "center",
              textShadow: "0 0 30px #FFFFFF40, 0 4px 12px #000000A0",
              padding: "0 20px",
            }}
          >
            {current.text}
          </div>
        )}

        {/* 下一条 (预览,半透明) */}
        {next && (
          <div
            style={{
              fontSize: 36,
              lineHeight: 1.4,
              color: "#FFFFFF60",
              fontWeight: 400,
              maxWidth: 1600,
              textAlign: "center",
              textShadow: "0 2px 4px #00000060",
            }}
          >
            {next.text}
          </div>
        )}
      </div>

      {/* 底部进度条 - 段级 */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 100,
          right: 100,
          height: 4,
          background: "#FFFFFF15",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${(t / audioDuration) * 100}%`,
            height: "100%",
            background: `linear-gradient(90deg, #FFFFFF80 0%, #FFFFFF 100%)`,
            boxShadow: "0 0 12px #FFFFFF80",
          }}
        />
      </div>

      {/* 帧号 */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          left: 100,
          fontSize: 16,
          color: "#FFFFFF30",
          fontFamily: "monospace",
        }}
      >
        t = {t.toFixed(1)}s · frame {frame}
      </div>
    </AbsoluteFill>
  );
};
