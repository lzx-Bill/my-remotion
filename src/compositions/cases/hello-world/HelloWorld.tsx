import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";
import { Logo } from "./Logo";

export const helloWorldSchema = z.object({
  titleText: z.string(),
  titleColor: zColor(),
  subtitleText: z.string(),
  accentColor: zColor(),
});

export const HelloWorld: React.FC<z.infer<typeof helloWorldSchema>> = ({
  titleText,
  titleColor,
  subtitleText,
  accentColor,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 0–60 帧：标题从下方滑入 + 渐显
  const titleY = spring({
    frame,
    fps,
    from: 200,
    to: 0,
    config: { damping: 12, stiffness: 80, mass: 1 },
  });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  // 30–60 帧：副标题渐入
  const subOpacity = interpolate(frame, [30, 60], [0, 1], {
    extrapolateRight: "clamp",
  });
  const subY = interpolate(frame, [30, 60], [40, 0], {
    extrapolateRight: "clamp",
  });

  // 60–120 帧：logo 出现（Sequence 包裹）
  // 90–150 帧：底部"Hello from Remotion"淡出淡出
  const footerOpacity = interpolate(frame, [90, 120, 140, 150], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });

  // 整段背景做一个缓慢的颜色漂移
  const hue = interpolate(frame, [0, 150], [220, 280]);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, hsl(${hue}, 60%, 12%) 0%, hsl(${hue + 30}, 70%, 8%) 100%)`,
        fontFamily: "system-ui, -apple-system, sans-serif",
        color: titleColor,
      }}
    >
      {/* 标题块 */}
      <div
        style={{
          position: "absolute",
          top: height * 0.3,
          left: 0,
          right: 0,
          textAlign: "center",
          transform: `translateY(${titleY}px)`,
          opacity: titleOpacity,
        }}
      >
        <div
          style={{
            fontSize: 140,
            fontWeight: 800,
            letterSpacing: -2,
            textShadow: `0 0 40px ${accentColor}80`,
          }}
        >
          {titleText}
        </div>
      </div>

      {/* 副标题块 */}
      <div
        style={{
          position: "absolute",
          top: height * 0.45,
          left: 0,
          right: 0,
          textAlign: "center",
          transform: `translateY(${subY}px)`,
          opacity: subOpacity,
        }}
      >
        <div
          style={{
            fontSize: 48,
            fontWeight: 300,
            color: "#FFFFFFCC",
            letterSpacing: 1,
          }}
        >
          {subtitleText}
        </div>
      </div>

      {/* Logo：60 帧开始播放，独立 Sequence */}
      <Sequence from={60} durationInFrames={90}>
        <div
          style={{
            position: "absolute",
            top: height * 0.6,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <Logo logoColor1={accentColor} logoColor2={accentColor} />
        </div>
      </Sequence>

      {/* 帧号显示（用于演示帧驱动） */}
      <div
        style={{
          position: "absolute",
          top: 40,
          right: 60,
          fontSize: 32,
          color: "#FFFFFF80",
          fontFamily: "monospace",
        }}
      >
        frame {frame} / fps {fps}
      </div>

      {/* 底部 footer */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 36,
          color: accentColor,
          opacity: footerOpacity,
          letterSpacing: 4,
        }}
      >
        视频 = 时间轴上的 React 应用
      </div>

      {/* 装饰：左侧进度条 */}
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: 0,
          width: 8,
          background: `linear-gradient(180deg, ${accentColor} 0%, transparent 100%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 8,
          height: `${(frame / 150) * 100}%`,
          background: accentColor,
          boxShadow: `0 0 20px ${accentColor}`,
        }}
      />
    </AbsoluteFill>
  );
};
