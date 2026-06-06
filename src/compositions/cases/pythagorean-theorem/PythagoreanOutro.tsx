import React from "react";
import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// 片尾 schema
export const pythagoreanOutroSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  accentColor: zColor(),
  background: zColor(),
  bgmFile: z.string().optional(),
  bgmVolume: z.number().optional(),
  nextEpisodeHint: z.string().optional(),
});

export const PythagoreanOutro: React.FC<z.infer<typeof pythagoreanOutroSchema>> = ({
  title,
  subtitle,
  accentColor,
  background,
  bgmFile,
  bgmVolume = 0.5,
  nextEpisodeHint,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = interpolate(frame, [0, fps * 0.6], [0, 1], { extrapolateRight: "clamp" });
  const titleEnter = interpolate(frame, [fps * 0.5, fps * 2.5], [0, 1], { extrapolateRight: "clamp" });
  const titleScale = interpolate(frame, [fps * 0.5, fps * 2.5], [0.6, 1], { extrapolateRight: "clamp" });
  const subtitleEnter = interpolate(frame, [fps * 2, fps * 4], [0, 1], { extrapolateRight: "clamp" });
  const hintEnter = interpolate(frame, [fps * 3.5, fps * 5], [0, 1], { extrapolateRight: "clamp" });
  const exitFade = interpolate(frame, [fps * 5, fps * 6], [1, 0], { extrapolateRight: "clamp" });
  const opacity = Math.min(enter, exitFade);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #F5F0FF 0%, #FFF8E6 50%, #FDF6F0 100%)`,
        fontFamily: 'system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif',
        opacity, color: "#1E1E1E",
      }}
    >
      {bgmFile && <Audio src={staticFile(bgmFile)} volume={bgmVolume} />}

      <AbsoluteFill
        style={{
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
        }}
      >
        {/* 主标题"完" */}
        <div
          style={{
            fontSize: 280, fontWeight: 900, color: "#1E1E1E",
            opacity: titleEnter, transform: `scale(${titleScale})`,
            background: `linear-gradient(135deg, ${accentColor} 0%, #7C3AED 100%)`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            marginBottom: 30,
          }}
        >
          完
        </div>

        {/* 副标题:专题名 */}
        <div
          style={{
            fontSize: 48, color: "#555555CC", fontWeight: 300, letterSpacing: 8,
            opacity: subtitleEnter, marginBottom: 40,
          }}
        >
          {title} · {subtitle}
        </div>

        {/* 下一期提示 */}
        {nextEpisodeHint && (
          <div
            style={{
              fontSize: 28, color: accentColor, fontFamily: "monospace",
              letterSpacing: 6, opacity: hintEnter,
              padding: "10px 24px", border: `1px solid ${accentColor}60`,
              borderRadius: 999, background: `${accentColor}15`,
            }}
          >
            {nextEpisodeHint}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
