import { z } from "zod";
import { zColor } from "@remotion/zod-types";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const trendingRepoSchema = z.object({
  rank: z.number(),
  owner: z.string(),
  repo: z.string(),
  description: z.string(),
  starsToday: z.number(),
  totalStars: z.number(),
  language: z.string(),
  languageColor: z.string(),
  // 4 块文案 —— 核心特性 / 使用场景 / 技术亮点 / 链接
  features: z.string(),
  useCase: z.string(),
  techHighlight: z.string(),
  url: z.string(),
});

export const githubTrendingSchema = z.object({
  title: z.string(),
  dateText: z.string(),
  accentColor: zColor(),
  repos: z.array(trendingRepoSchema),
});

// 各段音频时长（秒）— 用 silenceremove 测的"真实朗读时长"（已剔除末尾静音填充）
// XiaoyiNeural @ +10% rate
const SECTION_DURATIONS_S = {
  intro: 7.65,
  repos: [23.68, 25.38, 25.51, 27.96, 27.91], // 5 个项目（每段 3 块内容，去掉了项目地址介绍）
  outro: 6.26,
} as const;

export const GitHubTrending: React.FC<z.infer<typeof githubTrendingSchema>> = ({
  title,
  dateText,
  accentColor,
  repos,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 把秒数换算成帧数
  const introFrames = Math.round(SECTION_DURATIONS_S.intro * fps);
  const outroFrames = Math.round(SECTION_DURATIONS_S.outro * fps);
  const repoFrames = SECTION_DURATIONS_S.repos.map((s) => Math.round(s * fps));
  const totalFrames =
    introFrames + repoFrames.reduce((a, b) => a + b, 0) + outroFrames;

  // 当前所在段落
  const isIntro = frame < introFrames;
  const isOutro = frame >= totalFrames - outroFrames;

  // 计算当前是哪个项目 + 在该项目内的相对位置
  let currentRepoIndex = -1;
  let sectionFrame = 0;
  let sectionDuration = 0;
  if (isIntro) {
    sectionFrame = frame;
    sectionDuration = introFrames;
  } else if (isOutro) {
    currentRepoIndex = repos.length; // 占位
    sectionFrame = frame - (totalFrames - outroFrames);
    sectionDuration = outroFrames;
  } else {
    let accum = introFrames;
    for (let i = 0; i < repos.length; i++) {
      const seg = repoFrames[i];
      if (frame < accum + seg) {
        currentRepoIndex = i;
        sectionFrame = frame - accum;
        sectionDuration = seg;
        break;
      }
      accum += seg;
    }
  }

  // 整段背景色相漂移
  const hue = interpolate(frame, [0, totalFrames], [200, 280]);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at top, hsl(${hue}, 40%, 12%) 0%, #050510 70%)`,
        fontFamily:
          'system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif',
        color: "#FFFFFF",
      }}
    >
      {/* 整段旁白 */}
      <Audio src={staticFile("assets/cases/github-trending/audio/narration.mp3")} />

      {/* 顶部 Header */}
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
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: 12,
              background: accentColor,
              boxShadow: `0 0 24px ${accentColor}`,
            }}
          />
          <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: 1 }}>
            {title}
          </div>
        </div>
        <div style={{ fontSize: 24, color: "#FFFFFFAA", fontFamily: "monospace" }}>
          {dateText}
        </div>
      </div>

      {/* 主内容区 */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          paddingTop: 100,
          paddingBottom: 100,
        }}
      >
        {isIntro ? (
          <IntroSection
            frame={sectionFrame}
            fps={fps}
            accentColor={accentColor}
            repoCount={repos.length}
          />
        ) : isOutro ? (
          <OutroSection
            frame={sectionFrame}
            fps={fps}
            accentColor={accentColor}
            total={totalFrames}
            current={frame}
          />
        ) : (
          <RepoDeepCard
            repo={repos[currentRepoIndex]}
            sectionFrame={sectionFrame}
            sectionDuration={sectionDuration}
            fps={fps}
            accentColor={accentColor}
            rank={currentRepoIndex + 1}
          />
        )}
      </AbsoluteFill>

      {/* 底部进度条 + 段指示器 */}
      <ProgressBar
        frame={frame}
        total={totalFrames}
        accentColor={accentColor}
        introFrames={introFrames}
        outroStart={totalFrames - outroFrames}
        repoBoundaries={[
          introFrames,
          ...repoFrames.map((_, i) =>
            repoFrames.slice(0, i + 1).reduce((a, b) => a + b, introFrames),
          ),
          totalFrames,
        ]}
        currentIndex={currentRepoIndex}
        totalRepos={repos.length}
      />
    </AbsoluteFill>
  );
};

// ============ 子组件 ============

const IntroSection: React.FC<{
  frame: number;
  fps: number;
  accentColor: string;
  repoCount: number;
}> = ({ frame, fps, accentColor, repoCount }) => {
  const titleScale = spring({
    frame,
    fps,
    from: 0.3,
    to: 1,
    config: { damping: 10, stiffness: 80 },
  });
  const titleOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });
  const subOpacity = interpolate(frame, [50, 90], [0, 1], {
    extrapolateRight: "clamp",
  });
  const subY = interpolate(frame, [50, 90], [40, 0], {
    extrapolateRight: "clamp",
  });
  const dot = interpolate(frame, [120, 200], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ textAlign: "center", width: "100%" }}>
      <div
        style={{
          fontSize: 180,
          fontWeight: 900,
          letterSpacing: -4,
          opacity: titleOpacity,
          transform: `scale(${titleScale})`,
          background: `linear-gradient(135deg, ${accentColor} 0%, #FFFFFF 100%)`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          textShadow: `0 0 80px ${accentColor}80`,
        }}
      >
        GitHub Trending
      </div>
      <div
        style={{
          fontSize: 56,
          fontWeight: 300,
          color: "#FFFFFFCC",
          letterSpacing: 6,
          opacity: subOpacity,
          transform: `translateY(${subY}px)`,
          marginTop: 30,
        }}
      >
        昨日最热的 {repoCount} 个项目
      </div>
      <div
        style={{
          marginTop: 60,
          fontSize: 32,
          color: accentColor,
          fontFamily: "monospace",
          opacity: dot,
          letterSpacing: 8,
        }}
      >
        ↓ 深度拆解
      </div>
    </div>
  );
};

const RepoDeepCard: React.FC<{
  repo: z.infer<typeof trendingRepoSchema>;
  sectionFrame: number;
  sectionDuration: number;
  fps: number;
  accentColor: string;
  rank: number;
}> = ({ repo, sectionFrame, sectionDuration, fps, accentColor, rank }) => {
  // 入场
  const enterScale = spring({
    frame: sectionFrame,
    fps,
    from: 0.9,
    to: 1,
    config: { damping: 12, stiffness: 100 },
  });
  const enterOpacity = interpolate(sectionFrame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  // 离场
  const exitStart = sectionDuration - 30;
  const exitOpacity = interpolate(sectionFrame, [exitStart, sectionDuration], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitX = interpolate(sectionFrame, [exitStart, sectionDuration], [0, -60], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const opacity = Math.min(enterOpacity, exitOpacity);

  // 计算当前在哪个信息块（0-2）—— 3 块内容
  const progress = sectionFrame / sectionDuration;
  let blockIndex = 0;
  if (progress < 0.35) blockIndex = 0; // 核心特性
  else if (progress < 0.70) blockIndex = 1; // 使用场景
  else blockIndex = 2; // 技术亮点

  const blocks = [
    { icon: "★", title: "核心特性", content: repo.features, color: accentColor },
    { icon: "▶", title: "使用场景", content: repo.useCase, color: "#5EEAD4" },
    { icon: "⚙", title: "技术亮点", content: repo.techHighlight, color: "#FBBF24" },
  ];
  const current = blocks[blockIndex];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 70,
        padding: "0 80px",
        width: "100%",
        opacity,
        transform: `translateX(${exitX}px) scale(${enterScale})`,
      }}
    >
      {/* 左侧：项目身份卡 */}
      <div style={{ minWidth: 580, display: "flex", flexDirection: "column" }}>
        <div
          style={{
            fontSize: 240,
            fontWeight: 900,
            lineHeight: 0.9,
            color: `${accentColor}30`,
            fontFamily: "monospace",
            textShadow: `0 0 80px ${accentColor}40`,
          }}
        >
          #{rank}
        </div>
        <div style={{ marginTop: -20 }}>
          <div
            style={{
              fontSize: 72,
              fontWeight: 800,
              letterSpacing: -1,
              lineHeight: 1.05,
            }}
          >
            <span style={{ color: "#FFFFFFAA", fontWeight: 500 }}>{repo.owner}/</span>
            <br />
            <span style={{ color: "#FFFFFF" }}>{repo.repo}</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 24, flexWrap: "wrap" }}>
          <Badge color={accentColor} bg={`${accentColor}25`} border={`${accentColor}60`}>
            🔥 +{repo.starsToday.toLocaleString()} today
          </Badge>
          <Badge color="#FFFFFFCC" bg="#FFFFFF10" border="transparent">
            ⭐ {repo.totalStars.toLocaleString()} total
          </Badge>
          <Badge color="#FFFFFFCC" bg="#FFFFFF10" border="transparent">
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: 5,
                background: repo.languageColor,
                marginRight: 8,
              }}
            />
            {repo.language}
          </Badge>
        </div>

        {/* 完整项目地址 — 整段常驻显示（不是块） */}
        <div
          style={{
            marginTop: 36,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 18px",
            background: `${accentColor}15`,
            border: `1px solid ${accentColor}40`,
            borderRadius: 10,
            fontSize: 24,
            fontFamily: "monospace",
            color: "#FFFFFFE5",
            maxWidth: 560,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          <span style={{ color: accentColor, fontSize: 26 }}>→</span>
          <span style={{ color: accentColor }}>github.com/</span>
          <span>{repo.url.replace("github.com/", "")}</span>
        </div>
      </div>

      {/* 右侧：信息块（按时间切换） */}
      <div style={{ flex: 1, minHeight: 400 }}>
        <InfoBlock
          block={current}
          sectionFrame={sectionFrame}
          sectionDuration={sectionDuration}
          blockIndex={blockIndex}
          fps={fps}
        />

        {/* 块指示器 */}
        <div
          style={{
            marginTop: 60,
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          {blocks.map((b, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 14px",
                borderRadius: 999,
                background: i === blockIndex ? `${b.color}20` : "transparent",
                border: `1px solid ${i === blockIndex ? b.color : "#FFFFFF20"}`,
                fontSize: 22,
                color: i === blockIndex ? b.color : "#FFFFFF50",
                fontWeight: i === blockIndex ? 700 : 400,
                transition: "all 0.1s",
              }}
            >
              <span>{b.icon}</span>
              <span>{b.title}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const InfoBlock: React.FC<{
  block: { icon: string; title: string; content: string; color: string };
  sectionFrame: number;
  sectionDuration: number;
  blockIndex: number;
  fps: number;
}> = ({ block, sectionFrame, sectionDuration, blockIndex, fps }) => {
  // 块切换时的进入动画
  const blockProgress = blockIndex;
  const blockStart = [0, 0.28, 0.55, 0.82][blockIndex] * sectionDuration;
  const localFrame = sectionFrame - blockStart;

  const enterX = spring({
    frame: localFrame,
    fps,
    from: 60,
    to: 0,
    config: { damping: 14, stiffness: 90 },
  });
  const enterOpacity = interpolate(localFrame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      key={blockIndex}
      style={{
        opacity: enterOpacity,
        transform: `translateX(${enterX}px)`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          marginBottom: 28,
        }}
      >
        <div
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: block.color,
            textShadow: `0 0 30px ${block.color}80`,
          }}
        >
          {block.icon}
        </div>
        <div
          style={{
            fontSize: 56,
            fontWeight: 700,
            color: block.color,
            letterSpacing: 2,
          }}
        >
          {block.title}
        </div>
      </div>
      <div
        style={{
          fontSize: 36,
          lineHeight: 1.55,
          color: "#FFFFFFE5",
          fontWeight: 300,
          maxWidth: 1100,
        }}
      >
        {block.content}
      </div>
    </div>
  );
};

const OutroSection: React.FC<{
  frame: number;
  fps: number;
  accentColor: string;
  total: number;
  current: number;
}> = ({ frame, fps, accentColor }) => {
  const scale = spring({
    frame,
    fps,
    from: 0.9,
    to: 1,
    config: { damping: 12 },
  });
  const opacity = interpolate(frame, [0, 30, 150, 192], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        textAlign: "center",
        opacity,
        transform: `scale(${scale})`,
        width: "100%",
      }}
    >
      <div
        style={{
          fontSize: 130,
          fontWeight: 800,
          letterSpacing: -2,
          marginBottom: 30,
          background: `linear-gradient(135deg, #FFFFFF 0%, ${accentColor} 100%)`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        去看完整榜单
      </div>
      <div
        style={{
          fontSize: 64,
          color: "#FFFFFFDD",
          fontFamily: "monospace",
          letterSpacing: 4,
        }}
      >
        github.com/trending
      </div>
    </div>
  );
};

const ProgressBar: React.FC<{
  frame: number;
  total: number;
  accentColor: string;
  introFrames: number;
  outroStart: number;
  repoBoundaries: number[];
  currentIndex: number;
  totalRepos: number;
}> = ({ frame, total, accentColor, introFrames, outroStart, repoBoundaries, currentIndex, totalRepos }) => {
  const progress = (frame / total) * 100;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        padding: "40px 80px",
      }}
    >
      {/* 项目段落指示器 */}
      <div
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 16,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {Array.from({ length: totalRepos }).map((_, i) => {
          const isPast = i < currentIndex;
          const isActive = i === currentIndex;
          return (
            <div
              key={i}
              style={{
                width: isActive ? 50 : 14,
                height: 12,
                borderRadius: 6,
                background: isActive
                  ? accentColor
                  : isPast
                  ? `${accentColor}80`
                  : "#FFFFFF20",
                boxShadow: isActive ? `0 0 16px ${accentColor}` : "none",
                transition: "width 0.1s",
              }}
            />
          );
        })}
      </div>

      {/* 进度条 */}
      <div
        style={{
          height: 4,
          background: "#FFFFFF15",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progress}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${accentColor} 0%, #FFFFFF 100%)`,
            boxShadow: `0 0 16px ${accentColor}`,
          }}
        />
      </div>
    </div>
  );
};

const Badge: React.FC<{
  color: string;
  bg: string;
  border: string;
  children: React.ReactNode;
}> = ({ color, bg, border, children }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      padding: "10px 18px",
      borderRadius: 999,
      background: bg,
      border: `1px solid ${border}`,
      fontSize: 24,
      fontWeight: 600,
      color,
    }}
  >
    {children}
  </div>
);
