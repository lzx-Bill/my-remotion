import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const logoSchema = z.object({
  logoColor1: zColor(),
  logoColor2: zColor(),
});

export const Logo: React.FC<z.infer<typeof logoSchema>> = ({
  logoColor1,
  logoColor2,
}) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();

  // 缩放：spring 弹跳进入
  const scale = interpolate(frame, [0, 30], [0.3, 1], {
    extrapolateRight: "clamp",
  });

  // 持续旋转
  const rotation = interpolate(frame, [0, 150], [0, 360]);

  // 颜色循环
  const hue = (frame * 4) % 360;

  const cx = width / 2;
  const cy = height / 2;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a1a" }}>
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${width} ${height}`}
        style={{ display: "block" }}
      >
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={logoColor1} />
            <stop offset="100%" stopColor={logoColor2} />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="20" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g
          transform={`translate(${cx} ${cy}) rotate(${rotation}) scale(${scale})`}
          style={{ filter: "url(#glow)" }}
        >
          {/* 外圈六边形 */}
          <polygon
            points="-160,-90 -80,-220 80,-220 160,-90 160,90 80,220 -80,220 -160,90"
            fill="url(#grad)"
            stroke={`hsl(${hue}, 80%, 70%)`}
            strokeWidth="6"
          />
          {/* 内圈三角形 */}
          <polygon
            points="0,-110 95,55 -95,55"
            fill={`hsl(${hue}, 90%, 60%)`}
            opacity="0.9"
          />
          {/* 中心圆点 */}
          <circle
            r="30"
            fill="#FFFFFF"
            opacity={interpolate(frame % 60, [0, 30, 60], [1, 0.3, 1], {
              extrapolateRight: "clamp",
            })}
          />
        </g>

        {/* 文本 */}
        <text
          x={cx}
          y={cy + 360}
          textAnchor="middle"
          fontSize="80"
          fontWeight="800"
          fill="#FFFFFF"
          fontFamily="system-ui, sans-serif"
          letterSpacing="8"
        >
          REMOTION
        </text>
        <text
          x={cx}
          y={cy + 440}
          textAnchor="middle"
          fontSize="36"
          fontWeight="300"
          fill="#FFFFFFAA"
          fontFamily="system-ui, sans-serif"
          letterSpacing="12"
        >
          {fps} FPS · {width}×{height}
        </text>
      </svg>

      {/* 帧号 */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          right: 60,
          fontSize: 32,
          color: "#FFFFFF80",
          fontFamily: "monospace",
        }}
      >
        frame {frame}
      </div>
    </AbsoluteFill>
  );
};
