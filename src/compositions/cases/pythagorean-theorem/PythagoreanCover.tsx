import React from "react";
import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

function springIn(frame: number, delayS: number, durationS: number, fps: number) {
  const t = Math.max(0, Math.min(1, (frame - delayS * fps) / (durationS * fps)));
  return Easing.bezier(0.34, 1.56, 0.64, 1)(t);
}

function floatY(frame: number, amp = 10, speed = 0.5) {
  return amp * Math.sin((frame / 30) * speed * Math.PI * 2);
}

// 封面 schema
export const pythagoreanCoverSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  accentColor: zColor(),
  background: zColor(),
  logoEmoji: z.string(),
});

export const PythagoreanCover: React.FC<z.infer<typeof pythagoreanCoverSchema>> = ({
  title,
  subtitle,
  accentColor,
  background,
  logoEmoji,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 入场动画
  const enter = springIn(frame, 0, 0.8, fps);
  const logoScale = springIn(frame, 0, 1.5, fps);
  const titleEnter = springIn(frame, 0.8, 1.5, fps);
  const titleX = interpolate(frame, [fps * 0.8, fps * 2.5], [80, 0], { extrapolateRight: "clamp" });
  const subtitleEnter = springIn(frame, 2, 1.5, fps);
  const formulaEnter = springIn(frame, 3, 1.2, fps);
  const formulaScale = springIn(frame, 3, 1.2, fps);
  const float = floatY(frame, 8, 0.4);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, #FFF8F0 0%, #FFF0E6 50%, #FDF6F0 100%)`,
        fontFamily: 'system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif',
        opacity: enter,
        color: "#1E1E1E",
      }}
    >
      {/* 装饰几何图形背景 */}
      <svg
        viewBox="0 0 1920 1080"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.15 }}
      >
        <polygon points="200,540 200,200 600,540" fill="none" stroke={accentColor} strokeWidth="3" />
        <rect x="100" y="100" width="100" height="100" fill="none" stroke={accentColor} strokeWidth="2" />
        <rect x="600" y="540" width="200" height="200" fill="none" stroke={accentColor} strokeWidth="2" />
        <rect x="350" y="100" width="200" height="200" fill="none" stroke="#5EEAD4" strokeWidth="2" transform="rotate(45 450 200)" />
      </svg>

      {/* 中心内容 */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Logo / Emoji */}
        <div
          style={{
            fontSize: 180, transform: `scale(${logoScale})`, marginBottom: 30,
            filter: `drop-shadow(0 4px 20px ${accentColor}60)`,
          }}
        >
          {logoEmoji}
        </div>

        {/* 主标题 */}
        <div
          style={{
            fontSize: 140, fontWeight: 900, color: "#1E1E1E", letterSpacing: 8,
            opacity: titleEnter, transform: `translateX(${titleX}px) translateY(${float}px)`,
            marginBottom: 16,
          }}
        >
          {title}
        </div>

        {/* 副标题 */}
        <div
          style={{
            fontSize: 44, color: "#666666CC", fontWeight: 300, letterSpacing: 8,
            opacity: subtitleEnter, marginBottom: 60,
          }}
        >
          {subtitle}
        </div>

        {/* 公式 */}
        <div
          style={{
            fontSize: 100, fontWeight: 900, fontFamily: "monospace",
            background: `linear-gradient(135deg, ${accentColor} 0%, #7C3AED 100%)`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            opacity: formulaEnter, transform: `scale(${formulaScale})`,
            letterSpacing: 8,
          }}
        >
          a² + b² = c²
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
