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
  audioFile: z.string().optional(),  // cover/outro 等结构件可无音轨
  audioDuration: z.number(),
  bgColor1: zColor(),
  bgColor2: zColor(),
  sceneEmoji: z.string(),
  sceneImage: z.string().optional(), // 兼容旧版: 单张图(cover/outro 用)
  imageUrls: z.array(z.string()).optional(), // 新版: 多图切换(段内 N 张)
  imageChangeIntervalS: z.number().optional(), // 多图切换间隔(秒), 默认 22
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
  imageUrls,
  imageChangeIntervalS,
}) => {
  // 决定显示哪些图: 多图优先, 退到单图, 再退到无图
  const effectiveImageUrls: string[] =
    imageUrls && imageUrls.length > 0
      ? imageUrls
      : sceneImage
      ? [sceneImage]
      : [];
  const changeInterval = imageChangeIntervalS ?? 22;
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 当前时间(秒)
  const t = frame / fps;

  // 找当前 cue: t 落在 [start, end] 区间
  // 注意: cue 之间可能有 0.1-0.5s 间隙 (B 方案 VAD 切出来的 cue 不连续), 用最近匹配
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
  const current = cues[currentCueIndex];

  // 入场/离场
  const totalFrames = audioDuration * fps;
  const fadeIn = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [totalFrames - 30, totalFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const globalOpacity = Math.min(fadeIn, fadeOut);

  // 单条字幕: cue 切换时快速 fade (0.15s 进 / 0.1s 出)
  const cueFadeIn = current
    ? interpolate(frame, [Math.max(0, current.start * fps - 1), current.start * fps + 4], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at top, ${bgColor1} 0%, ${bgColor2} 70%, #050510 100%)`,
        fontFamily: 'system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif',
        color: "#FFFFFF",
        opacity: globalOpacity,
      }}
    >
      {/* 配音 (cover/outro 等结构件无音频) */}
      {audioFile && <Audio src={staticFile(audioFile)} />}

      {/* 场景图 (全屏背景) — 多图按 imageChangeIntervalS 切换, 0.3s cross-fade */}
      {effectiveImageUrls.length > 0 && (
        <>
          {effectiveImageUrls.map((url, i) => {
            const slotStart = i * changeInterval;
            const slotEnd = (i + 1) * changeInterval;
            const isLast = i === effectiveImageUrls.length - 1;
            // 显示窗口: [slotStart - fadeIn, slotEnd + fadeOut] 但首图无 fadeIn, 末图无 fadeOut
            const visible =
              t >= slotStart && (!isLast ? t <= slotEnd + 0.3 : t >= slotStart);
            if (!visible) return null;
            // fade in
            const fadeIn =
              i === 0
                ? 1
                : interpolate(t, [slotStart, slotStart + 0.3], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  });
            // fade out
            const fadeOut = isLast
              ? 1
              : interpolate(t, [slotEnd, slotEnd + 0.3], [1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                });
            const opacity = Math.min(fadeIn, fadeOut) * globalOpacity;
            if (opacity <= 0) return null;
            return (
              <Img
                key={i}
                src={url.startsWith("http") ? url : staticFile(url)}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  opacity,
                }}
              />
            );
          })}
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
      {effectiveImageUrls.length === 0 && (
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

      {/* 字幕区: 单行 + 半透明黑条底 (B 方案 2026-06-04, 2026-06-04 宽度调整) */}
      {current && (
        <div
          style={{
            position: "absolute",
            left: 100,
            right: 100,
            bottom: 60,
            padding: "18px 60px",
            background: "rgba(0, 0, 0, 0.7)",
            borderRadius: 12,
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
            opacity: cueFadeIn,
          }}
        >
          <div
            style={{
              fontSize: 52,
              lineHeight: 1.5,
              color: "#FFFFFF",
              fontWeight: 700,
              textAlign: "center",
              textShadow: "0 0 20px rgba(0, 0, 0, 0.8), 0 2px 4px rgba(0, 0, 0, 0.9)",
              letterSpacing: 1.5,
            }}
          >
            {current.text}
          </div>
        </div>
      )}

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
    </AbsoluteFill>
  );
};
