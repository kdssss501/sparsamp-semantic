const pptxgen = require("pptxgenjs");
const path = require("path");

const ROOT = "C:/Users/41462/Documents/隐写";
const OUT = path.join(ROOT, "deliverables", "生成式文本隐写_科研面试汇报.pptx");
const ASSET = (...parts) => path.join(ROOT, ...parts);

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "项目答辩材料";
pptx.subject = "大语言模型生成式文本隐写的可靠编码与跨精度回放研究";
pptx.title = "大语言模型生成式文本隐写的可靠编码与跨精度回放研究";
pptx.company = "科研面试汇报";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.defineSlideMaster({
  title: "MASTER",
  background: { color: "FAFBFC" },
  objects: [
    { rect: { x: 0, y: 0, w: 13.333, h: 0.11, fill: { color: "173B64" }, line: { color: "173B64" } } },
    { line: { x: 0.55, y: 7.06, w: 12.2, h: 0, line: { color: "D7DEE7", width: 0.5 } } },
    { text: { text: "生成式文本隐写 | 科研面试汇报", options: { x: 0.58, y: 7.12, w: 4.1, h: 0.16, fontFace: "Microsoft YaHei", fontSize: 6.8, color: "667085", margin: 0 } } },
  ],
  slideNumber: { x: 12.25, y: 7.10, color: "667085", fontFace: "Arial", fontSize: 7 },
});

const C = {
  navy: "173B64", blue: "245C97", cyan: "0C8F88", teal: "008E78", orange: "D8781F",
  red: "C2483B", text: "27313D", muted: "667085", pale: "EDF3F8", line: "D7DEE7",
  greenPale: "E8F5F1", orangePale: "FFF1E5", redPale: "FDEEEE", white: "FFFFFF",
};
const S = pptx.ShapeType;

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h, fontFace: opts.fontFace || "Microsoft YaHei", fontSize: opts.fontSize || 14,
    color: opts.color || C.text, bold: opts.bold || false, margin: opts.margin ?? 0,
    breakLine: false, fit: "shrink", valign: opts.valign || "mid", align: opts.align || "left",
    paraSpaceAfterPt: opts.paraSpaceAfterPt || 0, italic: opts.italic || false,
  });
}
function title(slide, kicker, heading, sub = "") {
  addText(slide, kicker, 0.62, 0.35, 4.4, 0.23, { fontSize: 8.5, color: C.blue, bold: true });
  addText(slide, heading, 0.62, 0.66, 11.8, 0.55, { fontSize: 24, color: C.navy, bold: true });
  if (sub) addText(slide, sub, 0.64, 1.25, 11.8, 0.26, { fontSize: 9.5, color: C.muted });
}
function pill(slide, text, x, y, w, color, pale) {
  slide.addShape(S.roundRect, { x, y, w, h: 0.31, rectRadius: 0.05, fill: { color: pale }, line: { color: pale } });
  addText(slide, text, x + 0.1, y + 0.045, w - 0.2, 0.16, { fontSize: 8, color, bold: true, align: "center" });
}
function card(slide, x, y, w, h, heading, body, accent = C.blue, fill = C.white) {
  slide.addShape(S.roundRect, { x, y, w, h, rectRadius: 0.07, fill: { color: fill }, line: { color: C.line, width: 0.8 } });
  slide.addShape(S.rect, { x, y, w: 0.06, h, fill: { color: accent }, line: { color: accent } });
  addText(slide, heading, x + 0.22, y + 0.18, w - 0.4, 0.3, { fontSize: 13, color: accent, bold: true });
  addText(slide, body, x + 0.22, y + 0.58, w - 0.42, h - 0.75, { fontSize: 10.5, color: C.text, valign: "top" });
}
function source(slide, text) {
  addText(slide, text, 0.64, 6.7, 11.35, 0.16, { fontSize: 6.7, color: C.muted });
}
function note(slide, text) { slide.addNotes(text); }
function arrow(slide, x, y, w, color = C.blue) {
  slide.addShape(S.chevron, { x, y, w, h: 0.24, fill: { color }, line: { color } });
}

// 1. Cover
{
  const s = pptx.addSlide("MASTER");
  s.background = { color: "F7FAFC" };
  s.addShape(S.rect, { x: 0, y: 0.11, w: 5.2, h: 6.95, fill: { color: "173B64" }, line: { color: "173B64" } });
  addText(s, "科研面试汇报", 0.65, 0.72, 2.1, 0.28, { fontSize: 10, color: "9AD7D0", bold: true });
  addText(s, "大语言模型\n生成式文本隐写的\n可靠编码与\n跨精度回放研究", 0.65, 1.22, 4.05, 2.05, { fontSize: 25, color: C.white, bold: true, valign: "top" });
  addText(s, "从可恢复性审计到数值稳定性的工程研究", 0.68, 3.55, 3.95, 0.34, { fontSize: 12, color: "D5E7F5" });
  addText(s, "姓名：____________\n学校 / 专业：____________\n汇报时长：8 分钟", 0.68, 5.5, 3.8, 0.78, { fontSize: 11, color: C.white, valign: "top" });
  // Editable probability-space illustration.
  addText(s, "概率空间中的秘密信息编码", 5.72, 0.86, 4.3, 0.28, { fontSize: 12, color: C.navy, bold: true });
  const bars = [0.9, 1.5, 0.62, 1.12, 0.42, 0.75, 0.3];
  bars.forEach((v, i) => {
    const x = 6.05 + i * 0.72;
    s.addShape(S.roundRect, { x, y: 4.8 - v, w: 0.36, h: v, rectRadius: 0.03, fill: { color: i === 1 ? C.cyan : "AFC6D9" }, line: { color: i === 1 ? C.cyan : "AFC6D9" } });
    s.addShape(S.ellipse, { x: x - 0.04, y: 5.03, w: 0.44, h: 0.12, fill: { color: C.white }, line: { color: "AFC6D9", width: 0.6 } });
  });
  s.addShape(S.line, { x: 5.85, y: 5.08, w: 5.75, h: 0, line: { color: C.navy, width: 1.1 } });
  [0, 1, 0, 1, 1, 0, 1, 0].forEach((b, i) => {
    const x = 6.05 + i * 0.62;
    s.addShape(S.roundRect, { x, y: 5.72, w: 0.38, h: 0.38, rectRadius: 0.04, fill: { color: b ? C.cyan : C.white }, line: { color: C.cyan, width: 1 } });
    addText(s, String(b), x, 5.80, 0.38, 0.15, { fontFace: "Arial", fontSize: 9, color: b ? C.white : C.cyan, bold: true, align: "center" });
  });
  arrow(s, 8.0, 5.25, 0.7, C.orange);
  pill(s, "模型分布", 6.0, 6.32, 1.35, C.blue, C.pale);
  pill(s, "密钥控制", 7.55, 6.32, 1.35, C.cyan, C.greenPale);
  pill(s, "秘密比特", 9.1, 6.32, 1.35, C.orange, C.orangePale);
  source(s, "说明：本页为原生可编辑概念示意，不代表实验数据。");
  note(s, "各位老师好，我汇报的项目是大语言模型生成式文本隐写的可靠编码与跨精度回放研究。核心不是简单地把信息藏进文本，而是同时解决能否正确恢复、长度是否泄露，以及不同数值精度下能否稳定复现三个问题。");
}

// 2. Background
{
  const s = pptx.addSlide("MASTER");
  title(s, "01 研究背景", "为什么研究大语言模型文本隐写？", "目标是在正常生成的文本中传递秘密信息，同时尽量保持生成分布与文本质量。");
  card(s, 0.68, 1.85, 2.6, 3.9, "普通生成", "语言模型给每个候选 token 分配概率，并据此采样下一个词。", C.blue, "F8FBFE");
  const tokens = [["天气", .88], ["今天", .65], ["适合", .42], ["学习", .28]];
  tokens.forEach((t, i) => {
    const y = 2.8 + i * .58;
    addText(s, t[0], 1.0, y, .5, .2, { fontSize: 10, color: C.text });
    s.addShape(S.roundRect, { x: 1.63, y: y + .02, w: 1.15 * t[1], h: .15, rectRadius: .02, fill: { color: i === 0 ? C.blue : "AFC6D9" }, line: { color: i === 0 ? C.blue : "AFC6D9" } });
  });
  arrow(s, 3.48, 3.52, .78, C.orange);
  card(s, 4.47, 1.85, 3.55, 3.9, "隐写编码", "共享密钥把秘密比特映射到概率空间，使选出的 token 同时承担“自然语言”和“信息载体”两种角色。", C.cyan, "F8FCFB");
  [1,0,1,1,0,0].forEach((b, i) => { s.addShape(S.roundRect, { x: 5.05 + i*.36, y: 3.15, w:.22, h:.22, rectRadius:.02, fill:{color:b?C.cyan:C.white}, line:{color:C.cyan} }); });
  arrow(s, 6.06, 3.56, .88, C.orange);
  card(s, 8.22, 1.85, 4.32, 3.9, "接收端恢复", "接收端以相同模型、上下文、\n密钥和离散决策规则回放，\n恢复嵌入的消息。", C.navy, "F8FBFE");
  addText(s, "研究重点", .72, 6.0, 1.15, .2, {fontSize:10,color:C.muted,bold:true});
  [["自然性",C.blue],["可恢复性",C.cyan],["长度侧信道",C.orange],["数值稳定性",C.red]].forEach((v,i)=>pill(s,v[0],2.0+i*1.52,5.93,1.28,v[1],v[1]===C.cyan?C.greenPale:v[1]===C.orange?C.orangePale:v[1]===C.red?C.redPale:C.pale));
  source(s, "概念依据：项目 README、docs/algorithm.md；示意图均为 PPT 原生图形。");
  note(s, "大模型每一步都不是只会输出一个词，而是给候选 token 一张概率表。生成式隐写利用这张概率表选择 token。对外看是一段普通文本，对持有同一密钥的人看，它对应一串可以恢复的秘密比特。难点在于，模型生成是逐步、随机且数值敏感的。");
}

// 3. Objectives
{
  const s = pptx.addSlide("MASTER");
  title(s, "02 问题定义", "四个目标不能只看其中一个", "本项目优先审计“可靠恢复”和“数值可复现”，并明确其他目标的证据边界。");
  const items = [
    [1.05,1.85,"自然性","文本应像正常生成",C.blue,C.pale],
    [7.05,1.85,"容量","每个 token 能承载多少信息",C.orange,C.orangePale],
    [1.05,4.25,"可恢复性","接收端能否无误解码",C.cyan,C.greenPale],
    [7.05,4.25,"可检测性","观察者能否区分 stego 与 cover",C.red,C.redPale],
  ];
  items.forEach(v=>card(s,v[0],v[1],5.15,1.55,v[2],v[3],v[4],v[5]));
  s.addShape(S.ellipse,{x:5.45,y:2.96,w:2.42,h:1.34,fill:{color:"E9F0F7"},line:{color:C.navy,width:1.2}});
  addText(s,"项目聚焦\n可靠恢复 + 回放一致性",5.61,3.21,2.1,.5,{fontSize:12,color:C.navy,bold:true,align:"center"});
  addText(s,"重要边界：当前结果不等于通用安全证明、完全不可检测或跨硬件保证。",1.06,6.2,11.15,.3,{fontSize:11,color:C.red,bold:true,align:"center"});
  source(s, "证据边界：docs/verified_rrc_theory.md、RESEARCH_BRIEF.md。");
  note(s, "评价一个隐写系统不能只问能不能嵌入。容量高可能影响自然性；能逐步匹配 token 分布，也不自动等于变长全文分布匹配。本项目没有把所有目标都宣称解决，而是把贡献聚焦到可靠恢复、长度侧信道缓解和跨精度回放。 ");
}

// 4. Routes
{
  const s = pptx.addSlide("MASTER");
  title(s, "03 技术路线", "复现、比较并扩展两条生成式文本隐写路线", "SparSamp 与 RRC 是并列路线；Verified-RRC、Fixed-Length RRC 是对 RRC 的可靠性扩展。");
  card(s, .72,1.8,5.5,3.85,"路线 A：SparSamp 稀疏采样","• 根据 token 概率和消息/密钥进行受控采样\n• 通过稀疏记录或稀疏决策降低回放负担\n• 项目中作为复现与比较对象",C.blue,"F8FBFE");
  card(s,7.1,1.8,5.5,3.85,"路线 B：Range Coding / RRC","• 将秘密消息对应到一个概率区间\n• 每步旋转并按 token 概率切分区间\n• 项目重点：终止正确性、固定长度、跨精度回放",C.cyan,"F8FCFB");
  arrow(s,6.36,3.45,.5,C.orange);
  pill(s,"复现",2.05,5.97,1.08,C.blue,C.pale); pill(s,"比较",4.02,5.97,1.08,C.orange,C.orangePale); pill(s,"可靠性扩展",8.55,5.97,1.6,C.cyan,C.greenPale);
  addText(s,"不宣称：将 SparSamp 与 RRC 融合为一个新算法。",2.5,6.38,8.3,.24,{fontSize:10.5,color:C.red,bold:true,align:"center"});
  source(s, "参考：SparSamp（USENIX Security 2025）；Yan & Murawaki, Range Coding（ACL 2026）；项目实现与审计文档。");
  note(s, "我先把两条路线区分清楚。SparSamp 和 RRC 都利用 token 概率完成隐写，但编码机制不同。我的工作不是把二者拼接成一个算法，而是在复现和比较的基础上，重点对 RRC 的终止可靠性和跨精度回放做了工程扩展。 ");
}

// 5. SparSamp
{
  const s = pptx.addSlide("MASTER");
  title(s, "04 SparSamp", "用概率分布做“带密钥的选择”", "下图为简化示意：真实实现还需要共享配置、离散化规则与严格回放条件。");
  addText(s,"候选 token 概率",.8,1.85,2.1,.25,{fontSize:12,color:C.navy,bold:true});
  const p = [["安全",.82,C.blue],["可靠",.61,C.cyan],["高效",.4,"91B9D2"],["自然",.25,"C6D5E2"]];
  p.forEach((v,i)=>{const y=2.35+i*.62; addText(s,v[0],.95,y,.58,.2,{fontSize:11}); s.addShape(S.roundRect,{x:1.72,y:y+.01,w:2.1*v[1],h:.18,rectRadius:.03,fill:{color:v[2]},line:{color:v[2]}}); addText(s,`${Math.round(v[1]*100)}%`,4.0,y,.42,.18,{fontSize:9,color:C.muted,align:"right"});});
  arrow(s,4.58,3.35,.85,C.orange);
  card(s,5.65,2.0,2.2,2.65,"密钥 + 消息块","共享密钥生成受控偏移；消息块决定在候选空间的落点。",C.orange,C.orangePale);
  arrow(s,8.12,3.35,.85,C.orange);
  card(s,9.15,2.0,3.2,2.65,"选择 token","在保持概率结构的前提下选出“可靠”，并使接收端能重放同一决策。",C.cyan,C.greenPale);
  pill(s,"概率分布",1.15,5.48,1.35,C.blue,C.pale); pill(s,"受控偏移",5.97,5.48,1.35,C.orange,C.orangePale); pill(s,"稀疏决策",9.78,5.48,1.35,C.cyan,C.greenPale);
  addText(s,"面试表达：SparSamp 的关键不是“强行指定词”，而是在模型原有概率分布上进行可回放的受控采样。",.94,6.17,11.4,.3,{fontSize:10.5,color:C.text,align:"center"});
  source(s,"概念依据：docs/fh_sparsamp.md、RESEARCH_BRIEF.md；本页为简化原生示意。 ");
  note(s,"可以把 SparSamp 理解成在一张概率表上用密钥找到一个可重复的位置。它不是简单地把某个词替换进去，而是尽量沿着模型本来就允许的候选空间采样。面试中需要强调，它是本项目的比较路线，不能说成与 RRC 融合后的新方法。 ");
}

// 6. RRC
{
  const s = pptx.addSlide("MASTER");
  title(s, "05 RRC", "把秘密消息映射为区间，再逐 token 收缩", "Range Coding 在项目中也称 RRC，因为每一步会用共享偏移对当前区间做旋转。");
  const xs=[1.0,4.78,8.55];
  const heads=["初始秘密点","旋转并按概率切分","选中子区间"];
  const bodies=["消息 m 对应初始区间\n[0, 2^l) 内的一点。","共享偏移旋转秘密点；\n模型概率决定分割比例。","生成 token 后保留包含\n秘密点的子区间，继续下一步。"];
  xs.forEach((x,i)=>{card(s,x,1.85,3.1,3.2,heads[i],bodies[i],i===1?C.orange:i===2?C.cyan:C.blue,i===1?C.orangePale:i===2?C.greenPale:"F8FBFE"); if(i<2)arrow(s,x+3.24,3.22,.35,C.orange);});
  // editable interval illustrations
  [[1.37,.45,C.blue],[5.12,.33,C.orange],[8.9,.2,C.cyan]].forEach((v,i)=>{s.addShape(S.rect,{x:v[0],y:4.43,w:2.22,h:.16,fill:{color:"DCE7EF"},line:{color:"DCE7EF"}});s.addShape(S.rect,{x:v[0]+.3,y:4.43,w:2.22*v[1],h:.16,fill:{color:v[2]},line:{color:v[2]}});});
  addText(s,"I⁻¹ = [0, 2ˡ)",1.44,5.03,1.7,.2,{fontFace:"Arial",fontSize:10,color:C.navy,bold:true,align:"center"});
  addText(s,"dᵗ = rotate(dᵗ⁻¹)",5.0,5.03,2.1,.2,{fontFace:"Arial",fontSize:10,color:C.navy,bold:true,align:"center"});
  addText(s,"Iᵗ ⊂ Iᵗ⁻¹",9.03,5.03,1.55,.2,{fontFace:"Arial",fontSize:10,color:C.navy,bold:true,align:"center"});
  addText(s,"接收端按相同 token 前缀、偏移和分割规则反向重放，尝试恢复 m。",1.2,6.05,10.95,.28,{fontSize:11,color:C.text,align:"center"});
  source(s,"依据：docs/rrc.md、docs/verified_rrc_theory.md；示意不按具体模型概率绘制。 ");
  note(s,"RRC 可以看成把秘密消息放在一条数轴上。每生成一个 token，语言模型的概率把当前区间切成多个小格；我们选择包含秘密点的那一格。旋转的作用是让秘密点在当前区间内均匀移动。接收端拥有同样的密钥和模型配置时，就能按相反方向回放。 ");
}

// 7. Counterexample
{
  const s = pptx.addSlide("MASTER");
  title(s, "06 关键发现", "局部“接近中点”并不总能保证正确恢复", "在本项目采用的 Algorithm 3/4 形式化下，跨越旋转切点时，局部停止条件不是精确恢复的充分条件。 ");
  const steps=[
    ["t=0", "I⁻¹=[0,8)，m=3", "选中 I⁰=[3,5)", C.blue],
    ["t=1", "偏移 o₁=1/2", "选中 I¹=[3,9/2)", C.orange],
    ["反向", "mid(I¹)-d¹=-1/4", "round(19/4)=5 ≠ 3", C.red],
  ];
  steps.forEach((v,i)=>{const x=.82+i*4.18;card(s,x,1.84,3.55,2.0,v[0],`${v[1]}\n${v[2]}`,v[3],v[3]===C.red?C.redPale:v[3]===C.orange?C.orangePale:"F8FBFE");if(i<2)arrow(s,x+3.65,2.66,.38,C.orange);});
  addText(s,"区间演化（简化）",.9,4.32,2.1,.22,{fontSize:11,color:C.navy,bold:true});
  s.addShape(S.line,{x:1.35,y:5.16,w:9.8,h:0,line:{color:C.navy,width:1.2}});
  [0,3,4.5,5,8].forEach((n,i)=>{const x=1.35+[0,3.67,5.72,6.34,9.8][i];s.addShape(S.line,{x,y:5.05,w:0,h:.22,line:{color:C.navy,width:.7}});addText(s,String(n),x-.1,5.33,.2,.16,{fontFace:"Arial",fontSize:8,color:C.muted,align:"center"});});
  s.addShape(S.line,{x:5.02,y:4.9,w:2.45,h:0,line:{color:C.blue,width:7,beginArrowType:"none",endArrowType:"none"}});
  s.addShape(S.line,{x:5.02,y:5.43,w:1.65,h:0,line:{color:C.orange,width:7,beginArrowType:"none",endArrowType:"none"}});
  addText(s,"I⁰",5.78,4.6,.5,.18,{fontFace:"Arial",fontSize:9,color:C.blue,bold:true,align:"center"}); addText(s,"I¹",5.65,5.68,.5,.18,{fontFace:"Arial",fontSize:9,color:C.orange,bold:true,align:"center"});
  s.addShape(S.roundRect,{x:2.1,y:6.05,w:9.12,h:.38,rectRadius:.04,fill:{color:C.redPale},line:{color:"F3C4BE"}});
  addText(s,"结论：不能只检查局部距离；必须真正执行接收端的逆过程验证。",2.25,6.16,8.82,.15,{fontSize:10,color:C.red,bold:true,align:"center"});
  source(s,"精确有理数反例：docs/verified_rrc_theory.md，第 4 节；可用 scripts/verify_rrc_theory.py 重现。 ");
  note(s,"这是项目最关键的理论审计发现。原始局部规则只看最终中点是否离当前秘密点足够近，但反向旋转有一个切点。跨过切点后，数轴上的普通距离不再保持，因此局部看似满足条件，最后却可能被舍入到另一个消息。这里我不说原论文所有实现都错误，而是限定在项目采用的 Algorithm 3/4 形式化下，这个条件不充分。 ");
}

// 8. Verified RRC
{
  const s = pptx.addSlide("MASTER");
  title(s, "07 方法改进", "Verified-RRC：把“可能停”改成“确认能恢复才停”", "Fixed-Length RRC 再以 HMAC 认证帧和固定公开长度缓解停止长度泄露。 ");
  const flow=[["候选停止","局部条件满足",C.orange,C.orangePale],["逆重放验证","完整模拟接收端",C.cyan,C.greenPale],["HMAC 认证","验证消息前缀",C.blue,C.pale],["固定长度填充","采样至公开 N",C.navy,"E9F0F7"]];
  flow.forEach((v,i)=>{const x=.68+i*3.08;card(s,x,1.85,2.55,1.5,v[0],v[1],v[2],v[3]);if(i<3)arrow(s,x+2.67,2.48,.28,C.orange);});
  card(s,.83,4.12,3.2,1.65,"原局部停止规则", "Mock 审计精确恢复率\n87%–96%", C.red,C.redPale);
  card(s,4.95,4.12,3.2,1.65,"Verified-RRC", "500/500 精确恢复\n平均额外 0.04–0.15 token", C.cyan,C.greenPale);
  card(s,9.07,4.12,3.2,1.65,"代价边界", "单样本最多额外 2 token\n不等于对任意模型必然终止", C.orange,C.orangePale);
  addText(s,"认证帧：F = m || HMAC(K_auth, domain || l || context || m)[:a]",1.2,6.16,10.95,.28,{fontFace:"Arial",fontSize:11,color:C.navy,bold:true,align:"center"});
  source(s,"真实结果：refine-logs/R012_VERIFIED_RRC_RESULTS.md；固定长度设计：docs/fixed_length_rrc.md。MockProvider，非 Qwen 通用结论。 ");
  note(s,"Verified-RRC 的思想很直接：一旦局部条件看起来可以停止，不立刻输出，而是完整执行一次接收端的逆重放。只有真正恢复到原消息，才停止。为了不把完成时刻直接暴露在文本长度上，固定长度版本把消息和 HMAC 标签一起嵌入，完成后按同一量化目标分布继续采样到公开长度 N。R012 的 500 个 Mock 样本都准确恢复，但这不是任意模型都必然有限终止的证明。 ");
}

// 9. BDS
{
  const s = pptx.addSlide("MASTER");
  title(s, "08 工程可靠性", "BDS：跨 FP16 / BF16 时，只记录真正不稳定的决策", "微小 logit 差异可能改变一个 token，并在自回归生成中被持续放大。 ");
  const arch = ASSET("paper","ccfa_bounded_decision","figures","figure_01_architecture.png");
  const fig4 = ASSET("figures","fig4_precision_direction.png");
  s.addImage({path:arch,x:.65,y:1.72,w:5.74,h:3.9});
  s.addImage({path:fig4,x:6.75,y:1.72,w:5.9,h:3.9});
  pill(s,"公共整数概率合同",.95,5.95,1.85,C.blue,C.pale); pill(s,"稳定：省略",4.05,5.95,1.25,C.cyan,C.greenPale); pill(s,"不稳定：记录",8.05,5.95,1.48,C.orange,C.orangePale);
  addText(s,"R059 独立 seed：40/40 精确回放，观测 0 false-safe。",1.02,6.36,11.2,.2,{fontSize:11,color:C.navy,bold:true,align:"center"});
  source(s,"左：project working paper Figure 1（概念图）；右：figures/fig4_precision_direction.png。R059 范围：Qwen2.5-1.5B、RTX 3060 Laptop、指定软件栈。 ");
  note(s,"RRC 的数学正确性还不够，因为发送端和接收端可能使用 FP16 与 BF16，两边的微小数值误差会导致 token 分叉。BDS 先用公开的整数概率合同把决策离散化，再枚举在声明不确定范围内所有可能的决策。如果某一步无论怎样都选同一个 token，就不记录；否则记录修正信息。R059 的两个独立 seed 合计 40 条都精确回放，但这个结果只覆盖指定的 Qwen 模型和同一 GPU 软件栈。 ");
}

// 10. Summary
{
  const s = pptx.addSlide("MASTER");
  title(s, "09 结果与总结", "项目成果：先保证能正确回来，再讨论能否稳定重放", "阶段性 working paper / 项目成果，不代表已发表、已投稿或通用安全结论。 ");
  const fig2=ASSET("figures","fig2_main_scale.png");
  s.addImage({path:fig2,x:.62,y:1.68,w:6.15,h:4.47});
  card(s,7.15,1.73,5.45,1.12,"结果 1：恢复可靠性","R012 Mock：Verified-RRC 为 500/500 精确恢复。",C.cyan,C.greenPale);
  card(s,7.15,3.03,5.45,1.12,"结果 2：跨精度回放","指定实验中：校正后 60/60，未校正 10/60。",C.blue,C.pale);
  card(s,7.15,4.33,5.45,1.12,"下一步","扩大模型/硬件矩阵；补充文本质量、检测与固定长度失败率评估。",C.orange,C.orangePale);
  addText(s,"边界：不宣称通用安全、完全不可检测、跨硬件保证或论文已发表。",1.12,6.3,11.1,.22,{fontSize:10.5,color:C.red,bold:true,align:"center"});
  source(s,"真实图表：figures/fig2_main_scale.png，详见 figures/source_data/figure2_trials.csv；结论范围见 RESEARCH_BRIEF.md。 ");
  note(s,"最后总结三点。第一，我复现并比较了 SparSamp 与 RRC 两条路线；第二，我通过精确反例发现 RRC 局部停止条件的跨边界风险，并实现了 Verified-RRC 与固定长度认证设计；第三，我用 BDS 处理 FP16/BF16 的离散决策分叉。现有结论都是阶段性、条件化的证据。下一步我会扩大模型和硬件范围，并补足文本质量与检测实验。谢谢各位老师。 ");
}

pptx.writeFile({ fileName: OUT });
