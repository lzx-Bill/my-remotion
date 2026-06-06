// 勾股定理教育专题试点 — 4 段 → 6 段内容（+封面/片尾）
// 段风格:story (1) + chalkboard (2,5) + modern (3,4,6) — 三种风格都试
// 总时长 ≈ 198s (3分18秒)

export const SECTION_STYLES = ["story", "chalkboard", "modern", "modern", "chalkboard", "modern"] as const;
export type SectionStyle = (typeof SECTION_STYLES)[number];

// 视觉资产
export const pythagoreanData = {
  // 视频元信息
  title: "勾股定理",
  subtitle: "一个等式背后的 2500 年智慧",
  tagline: "短边的平方和,永远等于长边的平方",
  // 主调色:金色(教育/数学调性,在深色背景上对比强)
  accentColor: "#E07B00",
  // v7 浅色主题 — 全片背景改为暖白/淡色系,动画丰富 + 丝滑过渡
  // 四套浅色背景
  modernBg: "#FDF6F0",        // 暖杏白(全片统一)
  chalkboardBg: "#FEF0E6",    // 暖橙白(段2/5)
  storyBg: "#FDF6F0",         // 淡杏白(段1)
  modernBg2: "#FEF8F0",       // 备用暖白

  // 故事化场景(段 1):"晨光下的几何发现"——暖白渐变,几何元素用金/青/紫三色
  beach: {
    sun: { x: 1620, y: 220, r: 90 },
    sandColor: "#FDF6F0",     // 地面(暖白)
    skyTop: "#FFF8F0",         // 顶部(淡杏)
    skyBottom: "#FFF0E6",      // 中部(暖粉)
  },

  // 几何元素三色 — 浅色背景下用更饱和的深色调,对比清晰
  geoColors: {
    a: "#C2410C",  // 深橙 — 边长 a
    b: "#0D9488",  // 深青 — 边长 b
    c: "#7C3AED",  // 深紫 — 边长 c (斜边)
    triangle: "#1E1E1E",  // 深灰三角,在浅色背景上清晰
  },

  // 经典勾股数(段 3) — 配色与故事化一致
  triples: [
    { a: 3, b: 4, c: 5,  color: "#F59E0B" },
    { a: 5, b: 12, c: 13, color: "#5EEAD4" },
    { a: 8, b: 15, c: 17, color: "#A78BFA" },
  ],

  // 原始勾股数(段 4) — a 是奇数,三数两两互质
  primitiveTriples: [
    { a: 3,  b: 4,  c: 5,  formula: "m=2, n=1", m: 2, n: 1 },
    { a: 5,  b: 12, c: 13, formula: "m=3, n=2", m: 3, n: 2 },
    { a: 15, b: 8,  c: 17, formula: "m=4, n=1", m: 4, n: 1 },
    { a: 7,  b: 24, c: 25, formula: "m=4, n=3", m: 4, n: 3 },
  ],

  // 几何直观(段 2)— 用 3-4-5 三角形直观证明
  geometricIntuition: {
    a: 3, b: 4, c: 5,
  },

  // 6 段内容 — durationS = 干净 audio 实际长度(头尾静音已裁,完美音画对齐)
  // 真实 TTS 时长见 public/assets/cases/pythagorean-theorem/audio/timings.json
  sections: [
    {
      id: "intro-story",
      style: "story" as SectionStyle,
      title: "2500 年前的沙滩",
      durationS: 19.5,  // clean audio 19.35s
      script:
        "公元前 500 年的希腊,毕达哥拉斯在沙滩上走路时随手画了一个直角三角形,又在三条边上各自画了一个正方形。他盯着这个图看了一会儿,突然愣住了——两个小正方形的面积加起来,恰好等于大正方形的面积。他发现了一个自然界的隐秘规律,而这个规律,跟是什么材质、大小是多少完全无关。",
    },
    {
      id: "why-areas",
      style: "chalkboard" as SectionStyle,
      title: "为什么偏偏是面积?",
      durationS: 24.7,  // clean audio 24.55s
      script:
        "好,这里有个很反直觉的点——我们说的不是边长相加,而是面积相加。为什么?因为斜边 c 是一个独立的长度,它不等于 a 加 b。3 加 4 等于 7,但斜边是 5,不是 7。面积呢?边长 3 的正方形面积是 9,边长 4 的是 16,9 加 16 刚好等于边长 5 的正方形面积,25。这里 c 不是 a 和 b 的和,却和它们的平方有着精确的等式关系。这就是勾股定理厉害的地方。",
    },
    {
      id: "core-formula",
      style: "modern" as SectionStyle,
      title: "一个等式,管用 2500 年",
      durationS: 28.3,  // clean audio 28.12s
      script:
        "这个规律用一句话写完:a 的平方加 b 的平方等于 c 的平方。2500 年来,数学家验证了无数组数字。最经典的 3、4、5,9 加 16 等于 25。5、12、13,25 加 144 等于 169。8、15、17,64 加 225 等于 289。每一组都精确吻合。世界上没有一组直角三角形能逃过这个等式。",
    },
    {
      id: "primitive-triples",
      style: "modern" as SectionStyle,
      title: "所有勾股数,都能用公式生成",
      durationS: 21.9,  // clean audio 21.71s
      script:
        "但勾股数不是随机出现的。2300 年前,欧几里得发现了一个生成公式——随便选两个数 m 和 n,m 大于 n,一奇一偶,就能生成 a 等于 m 方减 n 方,b 等于 2mn,c 等于 m 方加 n 方。3、4、5 对应 m 等于 2、n 等于 1。5、12、13 对应 m 等于 3、n 等于 2。这个公式能造出所有勾股数,一个不漏。",
    },
    {
      id: "proof-zhao-shuang",
      style: "chalkboard" as SectionStyle,
      title: "一张图,讲清了为什么",
      durationS: 32.4,  // clean audio 32.23s
      script:
        "但勾股定理为什么一定成立?中国古代数学家赵爽在公元 3 世纪画了一张图,一眼就能看明白。四个完全相同的直角三角形,拼成了一个大的正方形。外面正方形的边长是 a 加 b,所以它的面积等于 a 加 b 的平方。同时,它也可以看作中间那个小正方形的面积 c 平方,加上四个三角形的面积,也就是 4 乘 ab 除以 2。把这两个式子画等号,化简一下——a 平方加 b 平方等于 c 平方。赵爽用图形本身,证明了等式永远成立。这就是著名的赵爽弦图。",
    },
    {
      id: "outro-modern",
      style: "modern" as SectionStyle,
      title: "勾股定理的真正启示",
      durationS: 20.4,  // clean audio 20.21s
      script:
        "勾股定理不只是一个数学游戏,它告诉我们三件事。第一,世界的规律往往极其简洁——一个等式就能描述无数种形状。第二,几何和代数是一体的两面——赵爽用图证明了数的关系。第三,2500 年前的智慧今天仍在用——GPS 定位、屏幕分辨率、建筑结构,处处都有它。短边的平方和,永远等于长边的平方。记住了吗?",
    },
  ],
};
