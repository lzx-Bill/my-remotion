import React from "react";
import { z } from "zod";
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { pythagoreanSchema } from "./schema";

// ============ Spring / Bounce easing helpers ============
/** 弹性入场: overshoot 效果,元素入场时有一点弹跳感 */
function springIn(
  frame: number,
  delayS: number,
  durationS: number,
  fps: number,
  overshoot = 1.2,
): number {
  const t = Math.max(0, Math.min(1, (frame - delayS * fps) / (durationS * fps)));
  // cubic-bezier — overshoot 效果通过 y2>1 实现
  const eased = Easing.bezier(0.34, overshoot > 1 ? 1.56 : 0.9, 0.64, 1)(t);
  return eased;
}

/** 线性缓动 */
function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

/** Bounce ease out — 落地弹跳感 */
function bounceOut(t: number): number {
  const n1 = 7.5625, d1 = 2.75;
  if (t < 1 / d1) return n1 * t * t;
  if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + 0.75;
  if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + 0.9375;
  return n1 * (t -= 2.625 / d1) * t + 0.984375;
}

// ============ 字幕 helper ============
type Cue = { start: number; end: number; text: string };

function buildCues(script: string, durationS: number): Cue[] {
  const parts = script.split(/(?<=[。！？]|[.!?])\s*/);
  const sentences = parts.map((s) => s.trim()).filter((s) => s.length > 0);
  if (sentences.length === 0) return [];
  const totalChars = sentences.reduce((sum, s) => sum + s.length, 0);
  const cues: Cue[] = [];
  let acc = 0;
  sentences.forEach((s, i) => {
    const start = acc;
    const len = (s.length / totalChars) * durationS;
    acc = i === sentences.length - 1 ? durationS : start + len;
    cues.push({ start, end: acc, text: s });
  });
  return cues;
}

// ============ 字幕:白字大字体 + 黑色描边,底部居中 ============
const Subtitles: React.FC<{ cues: Cue[]; t: number }> = ({ cues, t }) => {
  if (cues.length === 0) return null;
  let curIdx = 0;
  for (let i = 0; i < cues.length; i++) {
    if (t >= cues[i].start && t < cues[i].end) { curIdx = i; break; }
    if (i === cues.length - 1 && t >= cues[i].end) curIdx = i;
  }
  const current = cues[curIdx];
  const curInCue = t - current.start;
  const appear = interpolate(curInCue, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
  const exit = interpolate(t, [current.end - 0.1, current.end], [1, 0], { extrapolateRight: "clamp" });
  const curOpacity = Math.min(appear, exit);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 160, padding: "0 120px", display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      <div style={{
        fontSize: 54, lineHeight: 1.3, color: "#FFFFFF", fontWeight: 700, textAlign: "center",
        opacity: curOpacity, maxWidth: 1700, padding: "12px 32px",
        textShadow: ["0 0 2px #000", "0 0 4px #000", "2px 2px 0 #000", "-2px 2px 0 #000", "2px -2px 0 #000", "-2px -2px 0 #000", "0 4px 12px rgba(0,0,0,0.8)"].join(", "),
        background: "rgba(0,0,0,0.4)", borderRadius: 12,
      }}>
        {current.text}
      </div>
    </div>
  );
};

// ============ 段指示器 ============
const SectionIndicator: React.FC<{ total: number; current: number; accentColor: string }> = ({ total, current, accentColor }) => (
  <div style={{ position: "absolute", bottom: 36, left: 0, right: 0, display: "flex", justifyContent: "center", alignItems: "center", gap: 14 }}>
    {Array.from({ length: total }).map((_, i) => {
      const isActive = i === current;
      const isPast = i < current;
      return (
        <div key={i} style={{
          width: isActive ? 56 : 14, height: 10, borderRadius: 5,
          background: isActive ? accentColor : isPast ? `${accentColor}80` : "#00000015",
          boxShadow: isActive ? `0 0 16px ${accentColor}` : "none",
          transition: "width 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
        }} />
      );
    })}
  </div>
);

// ============ 共享:几何漂浮动画值 ============
/** 浮动 Y 值,基于帧 */
function floatY(frame: number, amplitude = 12, speed = 0.8): number {
  return amplitude * Math.sin((frame / 30) * speed * Math.PI * 2);
}
/** 旋转角度,基于帧 */
function rotateDeg(frame: number, speed = 0.3): number {
  return 3 * Math.sin((frame / 30) * speed * Math.PI * 2);
}
/** 脉冲透明度 */
function pulse(frame: number, min = 0.7, max = 1, speed = 0.5): number {
  return min + (max - min) * (0.5 + 0.5 * Math.sin((frame / 30) * speed * Math.PI * 2));
}

// ============ 段 1 故事化:晨光下的几何发现 ============
// 关键修复:三个正方形的像素大小严格对应 a²=9, b²=16, c²=25 的面积比例
// 用 viewBox 0 0 420 320, 三角形 3-4-5 缩放到 legs 45/60px
// a² square: 45×45px | b² square: 60×60px | c² square: 75×75px (三者比例 9:16:25)
const StoryIntro: React.FC<{
  section: z.infer<typeof pythagoreanSchema>["sections"][number];
  sectionFrame: number; sectionDuration: number; fps: number;
  data: z.infer<typeof pythagoreanSchema>; cues: Cue[]; t: number;
}> = ({ section, sectionFrame: f, sectionDuration, fps, data, cues, t }) => {
  const { beach, accentColor, geoColors } = data;
  const colorA = geoColors.a, colorB = geoColors.b, colorC = geoColors.c, colorT = geoColors.triangle;

  // 动画
  const float1 = floatY(f, 10, 0.6);
  const float2 = floatY(f, 8, 0.7);
  const float3 = floatY(f, 14, 0.5);
  const glowPulse = pulse(f, 0.6, 1, 0.4);
  const enter = springIn(f, 0, 1.5, fps);
  const sqAEnter = springIn(f, 4.5, 1.2, fps);
  const sqBEnter = springIn(f, 7, 1.2, fps);
  const sqCEnter = springIn(f, 9.5, 1.2, fps);
  const formulaEnter = springIn(f, 14, 1, fps);
  const globalFade = interpolate(f, [0, fps * 0.4, sectionDuration - fps * 0.4, sectionDuration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // 三角形参数 — viewBox 600×500
  // 边长严格按 3:4:5 比例: a=75px, b=100px, c=125px (×25)
  // 面积比例 5625:10000:15625 = 9:16:25 ✓
  // 直角顶点 (250, 280); 顶点 (250, 205); 右点 (350, 280)
  const rx = 250, ry = 280, tx = 250, ty = 205, bx = 350, by = 280;
  // a² square: side=75px, 垂直边外侧(左)
  const sqAX = rx - 75 - 6, sqAY = ty, sqASide = 75;
  // b² square: side=100px, 水平边外侧(下)
  const sqBX = rx, sqBY = ry, sqBSide = 100;
  // c² square: side=125px, 斜边外侧(右上),不旋转!
  // 斜边从 (250,205) 到 (350,280), 向量 (100, 75)
  // 法向(三角形内部到外部) = (hypDy, -hypDx)/hypLen = (75, -100)/125 = (0.6, -0.8)
  const hypMidX = (tx + bx) / 2, hypMidY = (ty + by) / 2; // (300, 242.5)
  const hypDx = bx - tx, hypDy = by - ty; // (100, 75)
  const hypLen = Math.sqrt(hypDx * hypDx + hypDy * hypDy); // 125
  const normX = hypDy / hypLen, normY = -hypDx / hypLen; // (0.6, -0.8)
  // 中心在斜边中点 + 法向*100px
  const sqCCenterX = hypMidX + normX * 100, sqCCenterY = hypMidY + normY * 100; // (360, 162.5)
  const sqCSide = 125;

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, ${beach.skyTop} 0%, ${beach.skyBottom} 50%, ${beach.sandColor} 85%)`, opacity: globalFade, overflow: "hidden" }}>
      {/* 太阳光晕 */}
      <div style={{ position: "absolute", left: beach.sun.x - 100, top: beach.sun.y - 100 + floatY(f, 6, 0.4), width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, #FFE0A0 0%, #FFD080 40%, transparent 70%)", opacity: glowPulse }} />

      {/* 标题 */}
      <div style={{ position: "absolute", top: 30, left: 0, right: 0, textAlign: "center", opacity: enter }}>
        <div style={{ fontSize: 26, color: colorA, letterSpacing: 8, fontWeight: 500 }}>公元前 500 年</div>
        <div style={{ fontSize: 56, color: "#1E1E1E", fontWeight: 700, marginTop: 8, letterSpacing: 4 }}>{section.title}</div>
      </div>

      {/* 三角形 + 三色正方形 — 严格按 a:b:c=3:4:5 边长 / a²:b²:c²=9:16:25 面积比例 */}
      <div style={{ position: "absolute", left: "50%", top: "50%", transform: `translate(-50%, -50%) translateY(${float1}px)`, width: 600, height: 500 }}>
        <svg viewBox="0 0 600 500" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
          {/* 三角形 3-4-5: 边长 90/120/150px */}
          <polygon points={`${rx},${ry} ${tx},${ty} ${bx},${by}`} fill="none" stroke={colorT} strokeWidth="5" strokeLinejoin="round" />
          {/* 直角标记 */}
          <polyline points={`${rx + 16},${ry} ${rx + 16},${ry - 16} ${rx},${ry - 16}`} fill="none" stroke={colorT} strokeWidth="2" />
          {/* 边长标注 */}
          <text x={rx - 10} y={ty + 60} fill={colorA} fontSize="22" textAnchor="end" fontWeight="900">a = 3</text>
          <text x={(rx + bx) / 2} y={ry + 26} fill={colorB} fontSize="22" textAnchor="middle" fontWeight="900">b = 4</text>
          <text x={hypMidX + 20} y={hypMidY - 12} fill={colorC} fontSize="22" textAnchor="start" fontWeight="900">c = 5</text>
        </svg>

        {/* 正方形 a²=9 — 90×90px, 深橙色, 严格正方形 (3×3 = 9 单元) */}
        <div style={{
          position: "absolute", left: sqAX, top: sqAY,
          width: sqASide, height: sqASide,  // 严格的 90×90 正方形
          background: `${colorA}25`, border: `4px solid ${colorA}`,
          opacity: sqAEnter, transform: `scale(${0.2 + sqAEnter * 0.8})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: colorA, fontSize: 24, fontWeight: 900, fontFamily: "monospace",
          boxShadow: `0 6px 20px ${colorA}50`, transformOrigin: "center",
        }}>
          a²=9
        </div>

        {/* 正方形 b²=16 — 120×120px, 深青色, 严格正方形 (4×4 = 16 单元) */}
        <div style={{
          position: "absolute", left: sqBX, top: sqBY,
          width: sqBSide, height: sqBSide,  // 严格的 120×120 正方形
          background: `${colorB}25`, border: `4px solid ${colorB}`,
          opacity: sqBEnter, transform: `scale(${0.2 + sqBEnter * 0.8})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: colorB, fontSize: 26, fontWeight: 900, fontFamily: "monospace",
          boxShadow: `0 6px 20px ${colorB}50`, transformOrigin: "center",
        }}>
          b²=16
        </div>

        {/* 正方形 c²=25 — 150×150px, 深紫色, 严格正方形 (5×5 = 25 单元) — 不旋转,放在斜边外侧 */}
        <div style={{
          position: "absolute",
          left: sqCCenterX - sqCSide / 2, top: sqCCenterY - sqCSide / 2,
          width: sqCSide, height: sqCSide,  // 严格的 150×150 正方形
          background: `${colorC}25`, border: `4px solid ${colorC}`,
          opacity: sqCEnter, transform: `scale(${0.2 + sqCEnter * 0.8})`,
          transformOrigin: "center",
          boxShadow: `0 6px 20px ${colorC}50`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: colorC, fontSize: 28, fontWeight: 900, fontFamily: "monospace",
        }}>
          c²=25
        </div>
      </div>

      {/* 等式 */}
      <div style={{ position: "absolute", bottom: 200, left: 0, right: 0, textAlign: "center", opacity: formulaEnter, transform: `scale(${0.7 + formulaEnter * 0.3})` }}>
        <div style={{ fontSize: 90, fontWeight: 900, color: colorA, fontFamily: "monospace", textShadow: `0 4px 20px ${colorA}60` }}>9 + 16 = 25</div>
      </div>

      <Subtitles cues={cues} t={t} />
    </AbsoluteFill>
  );
};

// ============ 段 2 板书:几何直观(为什么是面积) ============
const GeometricIntuition: React.FC<{
  section: z.infer<typeof pythagoreanSchema>["sections"][number];
  sectionFrame: number; sectionDuration: number; fps: number;
  data: z.infer<typeof pythagoreanSchema>; cues: Cue[]; t: number;
}> = ({ section, sectionFrame: f, sectionDuration, fps, data, cues, t }) => {
  const { chalkboardBg, accentColor } = data;
  const { a, b, c } = data.geometricIntuition;
  const colorA = data.geoColors.a, colorB = data.geoColors.b, colorC = data.geoColors.c;

  const float1 = floatY(f, 8, 0.5);
  const float2 = floatY(f, 6, 0.7);

  const squaresEnter = springIn(f, 0, 1.5, fps, 1.3);
  const comparisonEnter = springIn(f, 12, 1.2, fps, 1.2);
  const insightEnter = springIn(f, 25, 1, fps, 1.3);
  const globalFade = interpolate(f, [0, fps * 0.4, sectionDuration - fps * 0.4, sectionDuration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, #FDF6F0 0%, #FEF0E6 50%, #FDF6F0 100%)`, opacity: globalFade, fontFamily: '"Kalam", "Caveat", cursive, sans-serif', padding: 80 }}>
      {/* 标题 */}
      <div style={{ fontSize: 76, fontWeight: 700, color: "#1E1E1E", marginBottom: 8, letterSpacing: 4 }}>{section.title}</div>
      <div style={{ fontSize: 24, color: "#666", fontWeight: 300, marginBottom: 30, letterSpacing: 6 }}>边长 vs 面积</div>

      <div style={{ display: "flex", alignItems: "center", gap: 60 }}>
        {/* 三个正方形 — 浮动入场 */}
        <div style={{ position: "relative", width: 460, height: 460, transform: `translateY(${float1}px)` }}>
          <svg viewBox="0 0 460 460" style={{ width: "100%", height: "100%", opacity: squaresEnter }}>
            <rect x="30" y="30" width="120" height="120" fill={`${colorA}15`} stroke={colorA} strokeWidth="3" />
            <text x="90" y="100" fill={colorA} fontSize="52" textAnchor="middle" fontFamily="monospace" fontWeight="bold">9</text>
            <text x="90" y="170" fill={colorA} fontSize="18" textAnchor="middle">a = 3</text>

            <rect x="200" y="30" width="160" height="160" fill={`${colorB}15`} stroke={colorB} strokeWidth="3" />
            <text x="280" y="120" fill={colorB} fontSize="62" textAnchor="middle" fontFamily="monospace" fontWeight="bold">16</text>
            <text x="280" y="210" fill={colorB} fontSize="18" textAnchor="middle">b = 4</text>

            <rect x="30" y="240" width="200" height="200" fill={`${colorC}15`} stroke={colorC} strokeWidth="3" />
            <text x="130" y="350" fill={colorC} fontSize="76" textAnchor="middle" fontFamily="monospace" fontWeight="bold">25</text>
            <text x="130" y="220" fill={colorC} fontSize="18" textAnchor="middle">c = 5</text>
          </svg>
        </div>

        {/* 对比推导 */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 30 }}>
          <div style={{ fontSize: 40, fontWeight: 600, color: "#333", opacity: comparisonEnter, transform: `translateX(${(1 - comparisonEnter) * -40}px)` }}>
            <div style={{ color: "#999" }}>边长相加:</div>
            <div style={{ fontSize: 64, color: "#DC2626", fontFamily: "monospace", marginTop: 8 }}>3 + 4 = 7<span style={{ fontSize: 28, color: "#DC262680", marginLeft: 16 }}>→ 7² = 49 ✗</span></div>
          </div>
          <div style={{ fontSize: 40, fontWeight: 600, color: "#333", opacity: comparisonEnter, transform: `translateX(${(1 - comparisonEnter) * -40}px)` }}>
            <div style={{ color: "#999" }}>面积相加:</div>
            <div style={{ fontSize: 64, color: colorA, fontFamily: "monospace", marginTop: 8 }}>9 + 16 = 25<span style={{ fontSize: 28, color: `${colorA}99`, marginLeft: 16 }}>→ 5² = 25 ✓</span></div>
          </div>
          <div style={{ fontSize: 36, fontWeight: 700, color: "#1E1E1E", opacity: insightEnter, transform: `scale(${0.85 + insightEnter * 0.15})`, padding: 16, borderLeft: `4px solid ${colorC}`, background: `${colorC}10`, borderRadius: "0 12px 12px 0" }}>
            <span style={{ color: colorC, fontWeight: 900 }}>关键:</span> 斜边是独立的长度,不是两直角边之和
          </div>
        </div>
      </div>

      <Subtitles cues={cues} t={t} />
    </AbsoluteFill>
  );
};

// ============ 段 3 现代动效:公式 + 经典勾股数 ============
const ModernCore: React.FC<{
  section: z.infer<typeof pythagoreanSchema>["sections"][number];
  sectionFrame: number; sectionDuration: number; fps: number;
  data: z.infer<typeof pythagoreanSchema>; cues: Cue[]; t: number;
}> = ({ section, sectionFrame: f, sectionDuration, fps, data, cues, t }) => {
  const { accentColor, modernBg, triples } = data;
  const colorA = data.geoColors.a, colorB = data.geoColors.b, colorC = data.geoColors.c;

  const float1 = floatY(f, 10, 0.4);
  const formulaEnter = springIn(f, 0, 1.5, fps, 1.4);
  const t1Enter = springIn(f, 4, 1.2, fps, 1.3);
  const t2Enter = springIn(f, 9, 1.2, fps, 1.3);
  const t3Enter = springIn(f, 14, 1.2, fps, 1.3);
  const taglineEnter = springIn(f, 22, 1, fps, 1.2);
  const globalFade = interpolate(f, [0, fps * 0.4, sectionDuration - fps * 0.4, sectionDuration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const renderTriple = (trip: (typeof triples)[number], enter: number, idx: number) => {
    const floatOffset = floatY(f + idx * 20, 6, 0.5 + idx * 0.1);
    return (
      <div key={idx} style={{
        display: "flex", alignItems: "center", gap: 28, opacity: enter,
        transform: `translateX(${(1 - enter) * -60}px) translateY(${floatOffset}px)`,
        padding: "20px 32px", background: `${trip.color}12`,
        border: `2px solid ${trip.color}50`, borderRadius: 20,
        boxShadow: `0 4px 24px ${trip.color}30`,
      }}>
        <div style={{ fontSize: 80, fontWeight: 900, fontFamily: "monospace", color: trip.color, letterSpacing: 2 }}>{trip.a}, {trip.b}, {trip.c}</div>
        <div style={{ fontSize: 50, color: "#AAAAAA", fontFamily: "monospace" }}>→</div>
        <div style={{ fontSize: 56, fontWeight: 700, color: "#1E1E1E", fontFamily: "monospace" }}>{trip.a * trip.a} + {trip.b * trip.b} = {trip.c * trip.c}</div>
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, #FDF6F0 0%, #FEF0E6 50%, #FDF6F0 100%)`, opacity: globalFade, fontFamily: 'system-ui, sans-serif', color: "#1E1E1E", padding: 80 }}>
      <div style={{ fontSize: 28, color: colorC, letterSpacing: 6, fontWeight: 600, marginBottom: 12 }}>核心规律</div>
      <div style={{ fontSize: 52, fontWeight: 800, color: "#1E1E1E", letterSpacing: -1, marginBottom: 20 }}>{section.title}</div>

      <div style={{ textAlign: "center", marginBottom: 36, opacity: formulaEnter, transform: `scale(${0.6 + formulaEnter * 0.4})` }}>
        <div style={{
          fontSize: 150, fontWeight: 900, fontFamily: "monospace",
          background: `linear-gradient(135deg, ${colorA} 0%, ${colorC} 100%)`,
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          letterSpacing: -4, lineHeight: 1,
          textShadow: "none",
        }}>a² + b² = c²</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 18, alignItems: "center" }}>
        {renderTriple(triples[0], t1Enter, 0)}
        {renderTriple(triples[1], t2Enter, 1)}
        {renderTriple(triples[2], t3Enter, 2)}
      </div>

      <div style={{ position: "absolute", bottom: 240, left: 0, right: 0, textAlign: "center", opacity: taglineEnter }}>
        <div style={{ fontSize: 26, color: colorA, fontFamily: "monospace", letterSpacing: 8 }}>→ 没有反例,一次都没有</div>
      </div>

      <Subtitles cues={cues} t={t} />
    </AbsoluteFill>
  );
};

// ============ 段 4 现代动效:原始勾股数 ============
const PrimitiveTriples: React.FC<{
  section: z.infer<typeof pythagoreanSchema>["sections"][number];
  sectionFrame: number; sectionDuration: number; fps: number;
  data: z.infer<typeof pythagoreanSchema>; cues: Cue[]; t: number;
}> = ({ section, sectionFrame: f, sectionDuration, fps, data, cues, t }) => {
  const { accentColor, modernBg, primitiveTriples } = data;
  const colors = [accentColor, data.geoColors.b, data.geoColors.c, "#E07B00"];

  const enters = [0, 4, 9, 15].map((start) => springIn(f, start, 1.2, fps, 1.3));
  const formulaEnter = springIn(f, 20, 1.2, fps, 1.2);
  const globalFade = interpolate(f, [0, fps * 0.4, sectionDuration - fps * 0.4, sectionDuration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, #FDF6F0 0%, #FEF0E6 50%, #FDF6F0 100%)`, opacity: globalFade, fontFamily: 'system-ui, sans-serif', color: "#1E1E1E", padding: 80 }}>
      <div style={{ fontSize: 28, color: data.geoColors.b, letterSpacing: 6, fontWeight: 600, marginBottom: 12 }}>欧几里得的发现</div>
      <div style={{ fontSize: 52, fontWeight: 800, color: "#1E1E1E", letterSpacing: -1, marginBottom: 36 }}>{section.title}</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 40 }}>
        {primitiveTriples.map((trip, i) => (
          <div key={i} style={{
            padding: "24px 32px", background: `${colors[i]}10`,
            border: `2px solid ${colors[i]}50`, borderRadius: 20,
            opacity: enters[i], transform: `translateY(${(1 - enters[i]) * 40}px) scale(${0.9 + enters[i] * 0.1})`,
            boxShadow: `0 4px 20px ${colors[i]}25`,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ fontSize: 18, color: colors[i], fontFamily: "monospace", letterSpacing: 4 }}>#{i + 1}</div>
              <div style={{ fontSize: 18, color: `${colors[i]}CC`, fontFamily: "monospace" }}>{trip.formula}</div>
            </div>
            <div style={{ fontSize: 52, fontWeight: 900, fontFamily: "monospace", color: colors[i], letterSpacing: 2 }}>{trip.a}, {trip.b}, {trip.c}</div>
            <div style={{ fontSize: 20, color: "#555", fontFamily: "monospace", marginTop: 8 }}>{trip.a * trip.a} + {trip.b * trip.b} = {trip.c * trip.c}</div>
          </div>
        ))}
      </div>

      <div style={{ textAlign: "center", padding: "24px 32px", background: `${accentColor}10`, border: `2px solid ${accentColor}50`, borderRadius: 20, opacity: formulaEnter, transform: `scale(${0.95 + formulaEnter * 0.05})` }}>
        <div style={{ fontSize: 20, color: accentColor, fontFamily: "monospace", letterSpacing: 4, marginBottom: 12 }}>EUCLID'S FORMULA</div>
        <div style={{ fontSize: 40, fontWeight: 700, color: "#1E1E1E", fontFamily: "monospace" }}>a = m² - n², &nbsp; b = 2mn, &nbsp; c = m² + n²</div>
        <div style={{ fontSize: 20, color: "#777", fontFamily: "monospace", marginTop: 8 }}>(m &gt; n, 互质, 一奇一偶)</div>
      </div>

      <Subtitles cues={cues} t={t} />
    </AbsoluteFill>
  );
};

// ============ 段 5 板书:赵爽弦图 ============
const ChalkboardProof: React.FC<{
  section: z.infer<typeof pythagoreanSchema>["sections"][number];
  sectionFrame: number; sectionDuration: number; fps: number;
  data: z.infer<typeof pythagoreanSchema>; cues: Cue[]; t: number;
}> = ({ section, sectionFrame: f, sectionDuration, fps, data, cues, t }) => {
  const { chalkboardBg, accentColor } = data;
  const colorA = data.geoColors.a, colorB = data.geoColors.b, colorC = data.geoColors.c;

  const float1 = floatY(f, 8, 0.5);
  const trianglesEnter = springIn(f, 2, 1.5, fps, 1.3);
  const formulaStep1 = springIn(f, 10, 1, fps, 1.2);
  const formulaStep2 = springIn(f, 18, 1, fps, 1.2);
  const formulaStep3 = springIn(f, 28, 1.2, fps, 1.4);
  const globalFade = interpolate(f, [0, fps * 0.4, sectionDuration - fps * 0.4, sectionDuration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const a = 60, b = 90, big = a + b, small = b - a;
  const bigSide = 320;
  const scale = bigSide / big;

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, #FDF6F0 0%, #FEF0E6 50%, #FDF6F0 100%)`, opacity: globalFade, fontFamily: '"Kalam", "Caveat", cursive, sans-serif', color: "#1E1E1E", padding: 80 }}>
      <div style={{ fontSize: 76, fontWeight: 700, color: "#1E1E1E", marginBottom: 8, letterSpacing: 4 }}>{section.title}</div>
      <div style={{ fontSize: 24, color: "#777", fontWeight: 300, marginBottom: 30, letterSpacing: 6 }}>赵爽弦图</div>

      <div style={{ display: "flex", alignItems: "center", gap: 60 }}>
        {/* 弦图 — 浮动 + 旋转 */}
        <div style={{ position: "relative", width: 380, height: 380, transform: `translateY(${float1}px) rotate(${rotateDeg(f, 0.2)}deg)` }}>
          <svg viewBox={`0 0 ${bigSide + 40} ${bigSide + 40}`} style={{ width: "100%", height: "100%", opacity: trianglesEnter }}>
            <rect x="20" y="20" width={bigSide} height={bigSide} fill="none" stroke={colorA} strokeWidth="3" strokeDasharray={bigSide * 4} strokeDashoffset={bigSide * 4 * (1 - trianglesEnter)} />

            <polygon points={`20,${20 + b * scale} ${20 + a * scale},${20 + b * scale} 20,${20 + (b - a) * scale}`} fill={`${colorA}20`} stroke={colorA} strokeWidth="2" />
            <polygon points={`${20 + big * scale},20 ${20 + big * scale},${20 + b * scale} ${20 + (big - a) * scale},${20 + b * scale}`} fill={`${colorA}20`} stroke={colorA} strokeWidth="2" />
            <polygon points={`20,${20 + (big - a) * scale} 20,${20 + big * scale} ${20 + b * scale},${20 + big * scale}`} fill={`${colorA}20`} stroke={colorA} strokeWidth="2" />
            <polygon points={`${20 + big * scale},${20 + (big - a) * scale} ${20 + (big - a) * scale},${20 + big * scale} ${20 + big * scale},${20 + big * scale}`} fill={`${colorA}20`} stroke={colorA} strokeWidth="2" />

            <rect x={20 + (b - a) * scale} y={20 + (b - a) * scale} width={small * scale} height={small * scale} fill={`${colorC}20`} stroke={colorC} strokeWidth="2" strokeDasharray={small * scale * 4} strokeDashoffset={small * scale * 4 * (1 - trianglesEnter)} />

            <text x={20 + big * scale / 2} y="14" fill={colorA} fontSize="16" textAnchor="middle" fontFamily="monospace">a + b</text>
            <text x={20 + (b - a) * scale + small * scale / 2} y={20 + (b - a) * scale + small * scale / 2 + 5} fill={colorC} fontSize="14" textAnchor="middle" fontFamily="monospace">c²</text>
          </svg>
        </div>

        {/* 公式推导 */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 22 }}>
          <div style={{ fontSize: 48, fontWeight: 700, opacity: formulaStep1, transform: `translateX(${(1 - formulaStep1) * -40}px)`, color: "#333" }}>
            <span style={{ color: "#888" }}>大正方形面积 =</span><br />
            <span style={{ color: colorA, fontSize: 60, fontWeight: 900 }}>(a + b)²</span>
          </div>
          <div style={{ fontSize: 40, fontWeight: 600, opacity: formulaStep2, transform: `translateX(${(1 - formulaStep2) * -40}px)`, color: "#333" }}>
            <span style={{ color: "#888" }}>也等于</span><br />
            <span style={{ color: colorB }}>4 × ½ab</span>
            <span style={{ color: "#888" }}> + </span>
            <span style={{ color: colorC }}>c²</span>
          </div>
          <div style={{ fontSize: 68, fontWeight: 900, opacity: formulaStep3, transform: `scale(${0.8 + formulaStep3 * 0.2})`, color: "#1E1E1E", textShadow: `0 4px 20px ${colorC}50` }}>
            <span style={{ color: colorA }}>a² + b²</span>
            <span style={{ color: "#888" }}> = </span>
            <span style={{ color: colorC }}>c²</span>
          </div>
        </div>
      </div>

      <Subtitles cues={cues} t={t} />
    </AbsoluteFill>
  );
};

// ============ 段 6 现代 Outro ============
const ModernOutro: React.FC<{
  section: z.infer<typeof pythagoreanSchema>["sections"][number];
  sectionFrame: number; sectionDuration: number; fps: number;
  data: z.infer<typeof pythagoreanSchema>; cues: Cue[]; t: number;
}> = ({ section, sectionFrame: f, sectionDuration, fps, data, cues, t }) => {
  const { accentColor, modernBg, tagline } = data;
  const colorA = data.geoColors.a, colorB = data.geoColors.b, colorC = data.geoColors.c;

  const insight1 = springIn(f, 1, 1, fps, 1.3);
  const insight2 = springIn(f, 5, 1, fps, 1.3);
  const insight3 = springIn(f, 9, 1, fps, 1.3);
  const finalTagline = springIn(f, 16, 1.5, fps, 1.4);
  const globalFade = interpolate(f, [0, fps * 0.4, sectionDuration - fps * 0.4, sectionDuration], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const InsightRow: React.FC<{ idx: number; text: string; color: string; enter: number; floatOff: number }> = ({ idx, text, color, enter, floatOff }) => (
    <div style={{
      display: "flex", alignItems: "center", gap: 24, padding: "16px 32px",
      background: `${color}12`, border: `2px solid ${color}40`, borderRadius: 16,
      opacity: enter, transform: `translateX(${(1 - enter) * -50}px) translateY(${floatOff}px)`,
      width: 1100, boxShadow: `0 4px 20px ${color}20`,
    }}>
      <div style={{ fontSize: 48, fontWeight: 900, color, fontFamily: "monospace", minWidth: 60 }}>{idx.toString().padStart(2, "0")}</div>
      <div style={{ fontSize: 28, color: "#333", fontWeight: 500 }}>{text}</div>
    </div>
  );

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, #FDF6F0 0%, #FEF0E6 50%, #FDF6F0 100%)`, opacity: globalFade, fontFamily: 'system-ui, sans-serif', color: "#1E1E1E", padding: 100 }}>
      <div style={{ fontSize: 28, color: colorC, letterSpacing: 6, fontWeight: 600, marginBottom: 8, textAlign: "center" }}>3 条启发</div>
      <div style={{ fontSize: 52, fontWeight: 800, color: "#1E1E1E", letterSpacing: -1, marginBottom: 40, textAlign: "center" }}>{section.title}</div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center", marginBottom: 40 }}>
        <InsightRow idx={1} text="简单的等式,能描述世界真理" color={colorA} enter={insight1} floatOff={floatY(f, 5, 0.4)} />
        <InsightRow idx={2} text="几何与代数从不孤立 — 赵爽用图证明了公式" color={colorB} enter={insight2} floatOff={floatY(f + 15, 5, 0.5)} />
        <InsightRow idx={3} text="2500 年前的智慧,今天仍管用 — GPS、屏幕分辨率" color={colorC} enter={insight3} floatOff={floatY(f + 30, 5, 0.6)} />
      </div>

      <div style={{ position: "absolute", bottom: 280, left: 0, right: 0, textAlign: "center", opacity: finalTagline }}>
        <div style={{
          fontSize: 90, fontWeight: 900, color: "#1E1E1E",
          background: `linear-gradient(135deg, ${colorA} 0%, ${colorC} 100%)`,
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          letterSpacing: 4, transform: `scale(${0.7 + finalTagline * 0.3})`,
        }}>a² + b² = c²</div>
        <div style={{ fontSize: 30, color: "#555", marginTop: 12, fontWeight: 300, letterSpacing: 4 }}>{tagline}</div>
      </div>

      <Subtitles cues={cues} t={t} />
    </AbsoluteFill>
  );
};

// ============ 主组件 ============
export const PythagoreanTheorem: React.FC<z.infer<typeof pythagoreanSchema>> = ({
  title, subtitle, accentColor, modernBg, chalkboardBg, storyBg,
  beach, triples, primitiveTriples, geometricIntuition, tagline, geoColors, sections,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sectionFrames = sections.map((s) => Math.round(s.durationS * fps));
  const totalFrames = sectionFrames.reduce((a, b) => a + b, 0);

  let currentSectionIndex = 0, sectionFrame = 0, sectionDuration = 0, accum = 0;
  for (let i = 0; i < sections.length; i++) {
    const seg = sectionFrames[i];
    if (frame < accum + seg) {
      currentSectionIndex = i;
      sectionFrame = frame - accum;
      sectionDuration = seg;
      break;
    }
    accum += seg;
  }

  const currentSection = sections[currentSectionIndex];
  const t = sectionFrame / fps;
  const cues = buildCues(currentSection.script, currentSection.durationS);

  const sectionData = { title, subtitle, accentColor, modernBg, chalkboardBg, storyBg, beach, triples, primitiveTriples, geometricIntuition, tagline, geoColors, sections };

  const renderSection = () => {
    const props = { section: currentSection, sectionFrame, sectionDuration, fps, data: sectionData, cues, t };
    switch (currentSection.style) {
      case "story": return <StoryIntro {...props} />;
      case "chalkboard": return currentSectionIndex === 1 ? <GeometricIntuition {...props} /> : <ChalkboardProof {...props} />;
      case "modern":
        if (currentSectionIndex === 3) return <PrimitiveTriples {...props} />;
        if (currentSectionIndex === 5) return <ModernOutro {...props} />;
        return <ModernCore {...props} />;
      default: return null;
    }
  };

  return (
    <AbsoluteFill style={{ background: "#FDF8F2" }}>
      {sections.map((section, i) => {
        const from = sectionFrames.slice(0, i).reduce((a, b) => a + b, 0);
        const durationInFrames = sectionFrames[i];
        return (
          <Sequence key={section.id} from={from} durationInFrames={durationInFrames}>
            <Audio src={staticFile(`assets/cases/pythagorean-theorem/audio/section-${i + 1}.mp3`)} />
          </Sequence>
        );
      })}
      {renderSection()}
      <SectionIndicator total={sections.length} current={currentSectionIndex} accentColor={accentColor} />
    </AbsoluteFill>
  );
};
