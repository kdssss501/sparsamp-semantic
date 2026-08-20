# 交付说明：科研面试 PPT（v2）

项目：大语言模型生成式文本隐写的可靠编码与跨精度回放研究
用途：科研面试 / 保研面试 · 8 分钟 · 计算机学院老师

## 产物清单

- PPT：`生成式文本隐写_科研面试汇报_v2.pptx`（16:9，10 页，原生可编辑，含每页演讲备注）
- 逐页讲稿：`speech.md`
- 大纲与事实映射：`outline.md`
- 构建脚本：`build_ppt.py`（python-pptx；插图存在时自动嵌入，否则绘制原生示意图并标注“示意”）
- 生图提示词：`prompts/image_prompts.json`（6 张，供九秋工作台使用）
- 预览图：`preview/幻灯片1-10.PNG`

## 使用说明（如何生成 6 张插图，需九秋工作台可达）

本机 Clash Verge 当前为 `direct` 模式且节点不可达，九秋（dingdangapii.cn，Cloudflare 前端）
在此网络下被重置。恢复步骤：

1. 打开 Clash Verge，把模式切到「规则」，并确认「🌍AI 网站」组选择了可用节点；
2. 或确认 dingdangapii.cn 在浏览器中可直接打开；
3. 然后在本仓库执行（密钥从 Codex 全局状态读取，不写入任何文件）：

```powershell
$json = Get-Content -Raw "$env:USERPROFILE\.codex\.codex-global-state.json"
$i = $json.IndexOf('dingdangapii.cn'); $k = [regex]::Match($json.Substring($i), 'sk-[A-Za-z0-9]{20,}').Value
$env:OPENAI_API_KEY = $k; $env:OPENAI_BASE_URL = 'https://dingdangapii.cn/v1'
$py = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$gen = "$env:USERPROFILE\.codex\skills\.system\imagegen\scripts\image_gen.py"
$p = 'C:\Users\41462\Documents\隐写\deliverables\interview-ppt\prompts'
Get-Content "$p\image_prompts.json" -Raw | ConvertFrom-Json | ForEach-Object {
  & $py $gen generate --model gpt-image-2 --size 1536x1024 --quality high `
    --use-case $_.use_case --style $_.style --composition $_.composition `
    --constraints $_.constraints --prompt $_.prompt `
    --out "C:\Users\41462\Documents\隐写\deliverables\interview-ppt\assets\$($_.filename)"
}
& $py 'C:\Users\41462\Documents\隐写\deliverables\interview-ppt\build_ppt.py'
```

生成 6 张图并重新运行 `build_ppt.py` 后，第 1、5、6、7、8、9 页会自动嵌入新插图。

---

# A. PPT 逐页内容与版式说明

整体版式：白底（#FAFBFC）、深灰正文（#27313D）、深蓝强调（#173B64/#245C97）；
青绿（#0C8F88）标“改进”，橙色（#D8781F）标“风险/边界”，红色（#C2483B）标“禁止表述”。
每页顶部 0.11 英寸深蓝条 + 章节编号 + 标题 + 副标题；底部来源行。每页 ≤4 个核心点。

## 第 1 页：标题页
- 版式：左侧深蓝信息区（项目名、占位姓名/学校/专业、8 分钟）+ 右侧概念图/原生概率条示意
- 插图：建议生成 `fig_cover_stego_channel.png`（可选，缺失时用原生图形）
- 核心点：项目名；复现、比较并扩展 SparSamp 与 RRC；working paper / 项目阶段成果
- 备注：25–30 秒（见 speech.md Slide 1）

## 第 2 页：研究背景
- 版式：三张流程卡（普通生成 → 隐写编码 → 接收端回放）+ 底部四个研究重点药丸
- 插图：不需要（流程图用 PPT 原生图形）
- 核心点：利用 next-token 概率表嵌入消息；接收端需相同密钥/模型/配置；随机生成对精度敏感
  （R044：未校正 10/60 精确重放）
- 备注：约 45 秒

## 第 3 页：问题定义
- 版式：2×2 目标卡 + 中央椭圆（项目聚焦）+ 两条边界红线
- 插图：不需要
- 核心点：自然性/容量/可恢复性/可检测性互相牵制；逐步分布匹配 ≠ 变长全文匹配（TV=1/2 反例）；
  不宣称零 KL、完全不可检测、通用安全
- 备注：约 45 秒

## 第 4 页：技术路线
- 版式：左右双卡对比（SparSamp vs RRC）+ 底部动作药丸 + 红色边界行
- 插图：不需要（数据为真实复现结果）
- 核心点：SparSamp（USENIX Security 2025）官方兼容复现：105 tokens/576 bits/5.486 bit/token；
  R002 1,193/1,200 完成、846/846 无歧义精确解码、16/16 容量误差 ≤5%；RRC（ACL 2026）为审计对象；
  不宣称融合
- 备注：约 40 秒

## 第 5 页：SparSamp 原理
- 版式：左侧原生概率条示意 + 右侧“密钥+消息块 → 稀疏采样选择 token” + 底部面试表达
- 插图：建议生成 `fig_sparsamp_sampling.png`（缺失时用原生示意并标注“示意”）
- 核心点：概率分布；密钥受控偏移；消息块决定落点；block 收缩到单点后恢复；项目内为复现/对比角色
- 备注：约 50 秒

## 第 6 页：RRC 原理
- 版式：顶部三张步骤卡（初始秘密点/旋转切分/选中子区间）+ 底部区间收缩示意
- 插图：建议生成 `fig_rrc_interval.png`（缺失时用原生区间条示意）
- 核心点：m∈[0,2^l)；每步旋转+按概率切分；选择含秘密点子区间；接收端反向重放
- 备注：约 55 秒

## 第 7 页：关键发现（跨边界问题）
- 版式：三张反例步骤卡（t=0 / t=1 / 反向）+ 数轴/几何示意 + 红色结论条
- 插图：建议生成 `fig_counterexample_wrap.png`（缺失时用原生数轴示意）
- 核心点：局部条件 −1/2<mid−d≤1/2 不充分；精确反例 m=3 恢复为 5；失败区域测度 1/1024；
  表述限定“本项目采用的 Algorithm 3/4 形式化下”
- 备注：约 60 秒

## 第 8 页：方法改进
- 版式：四步流程卡（候选停止→逆重放→HMAC→固定长度）+ 三张结果卡 + 认证帧公式
- 插图：建议生成 `fig_hmac_frame.png`（可选）
- 核心点：Verified-RRC 500/500（Mock），原规则 87–96%，平均 +0.04–0.15 token；
  R020 Mock 400/400、0 错 key 接受；F=m‖HMAC(K_auth,·)[:a]；非任意模型必然终止
- 备注：约 55 秒

## 第 9 页：工程可靠性（BDS）
- 版式：左侧概念图/工作论文 Figure 1 + 右侧三张结果卡 + 底部边界行
- 插图：建议生成 `fig_bds_replay.png`（缺失时复用工作论文 figure_01_architecture.png）
- 核心点：R044 未校正 10/60、修正率 2.16%[1.80,2.53]；BDS=公开整数合同+有限枚举；
  R059 独立 seed 40/40、0 false-safe、负载≈54.6%；范围=Qwen2.5-1.5B + RTX 3060 Laptop + 指定栈
- 备注：约 55 秒

## 第 10 页：结果、局限、未来与总结
- 版式：左侧真实数据图（R044：60/60 vs 10/60）+ 右侧三张结果卡 + 局限/未来 + 红色边界行
- 插图：真实数据图 `deliverables/assets/fig2_main_scale.png`（必须保留原图）
- 核心点：结果 1/2/3（见卡）；局限：单模型单 GPU、无真人盲评、无跨硬件；
  未来：扩大矩阵、失败率区间、整数频数合同、盲评与检测；不宣称已发表
- 备注：约 70 秒

---

# B. 每张插图的独立生图提示词

共 6 张，全部要求：nature 风格、白底、低饱和、扁平/轻微 3D、无水印、无文字（文字由 PPT
原生文本完成）。完整 JSON 见 `prompts/image_prompts.json`，此处列出核心提示词（英文，适配 gpt-image-2）。

1. **fig_cover_stego_channel.png（第 1 页/背景概念）**
   A row of seven vertical probability bars representing an LLM next-token distribution; one highlighted
   bar carries a thin hidden channel of binary bits through the distribution and re-emerges as the same
   token stream; a minimal dashed secret-key link connects both ends. Flat editorial vector style, thin
   precise outlines, deep blue / teal / warm gray, pure white background, no text, no labels, no watermark.

2. **fig_sparsamp_sampling.png（第 5 页）**
   Sparse controlled sampling over a probability mass: horizontal token slots of varying widths, a message
   block and shared-key symbol select a narrow sparse interval, a marker point resolves to one slot, and a
   replay arrow echoes the same slot. Deep blue and teal accents, pure white background, no text.

3. **fig_rrc_interval.png（第 6 页）**
   One long interval shrinking into three nested sub-intervals left-to-right; each partitioned by thin
   probability ticks; one marker stays inside; a curved rotation arrow above the middle stage. Deep blue
   primary with teal and orange accents, pure white background, no text, no formulas.

4. **fig_counterexample_wrap.png（第 7 页）**
   Modular wrapping geometry: a number-line segment bent into a circular band; a point crosses the seam;
   its projection back onto the straight line lands in a different unit cell. Orange seam highlight,
   pure white background, no text, no formulas.

5. **fig_hmac_frame.png（第 8 页）**
   Authenticated fixed-length frame: a short message block + key-shaped authentication tag embedded into a
   longer token tape; a seal at the authenticated-prefix boundary; dashed guides show the private completion
   point hidden inside public length. No lock/spy imagery, pure white background, no text.

6. **fig_bds_replay.png（第 9 页）**
   Two parallel token streams; at one bounded fork the stream splits into candidate paths inside a
   translucent envelope, then rejoins after a sparse indexed correction slip; both streams end aligned.
   Deep blue and teal with vermilion accent, pure white background, no text.

---

# C. 8 分钟完整讲稿

完整讲稿见 `speech.md`（已同时写入 PPT 演讲备注）。分段时间：第 1 页 25–30s，第 2–6 页
40–55s，第 7 页 60s，第 8–9 页 55s，第 10 页 70s，合计约 8 分钟。要点：每页先讲结论再讲
证据；所有数字都带“指定环境/小样本/Mock”限定；收尾固定一句话——“现有结论均为阶段性、
条件化的证据”。

---

# D. 5 个老师可能追问的问题及稳妥回答

1. **SparSamp 和 RRC 是不是被你融合成了新算法？**
   不是。它们是两条独立路线：SparSamp 是概率分布上的受控稀疏采样，RRC 是区间旋转收缩编码。
   我的工作是在复现、比较的基础上，对 RRC 路线做可靠性扩展（Verified-RRC、固定长度认证、
   BDS 回放），不宣称融合。

2. **为什么局部停止条件会失败？**
   局部条件只看“中点是否接近当前秘密点”，但反向恢复是模区间映射，存在切点。跨过切点后，
   圆周距离保持、线性距离不保持，最终可能落到错误的舍入单元。项目给出精确两步有理数反例
   （m=3 恢复为 5），并构造了测度 1/1024 的正测度失败区域。表述边界：在本项目采用的
   Algorithm 3/4 形式化下该条件不充分。

3. **HMAC 认证标签在 Fixed-Length RRC 里起什么作用？**
   嵌入帧是 F = m ‖ HMAC(K_auth, domain‖l‖context‖m)[:a]。接收端沿每个前缀反向重放，
   只有认证通过才接受候选消息；这样不需要公开真实完成时刻，也能防止错误前缀被误判。
   默认 a=128，理想标签下扫描误接受 union bound 为 N/2^a。

4. **为什么 BDS 不能说“跨硬件绝对可复现”？**
   BDS 的结论需要一个已声明的模型、tokenizer、采样配置和目标数值环境。R059 只在
   Qwen2.5-1.5B-Instruct、RTX 3060 Laptop 和指定软件栈上做了独立 seed 确认。不同 GPU、
   驱动、算子或 tokenizer 都可能改变候选顺序与概率边界，必须做独立实验。

5. **这个项目的创新点和局限分别是什么？**
   创新是可靠性审计与工程扩展：RRC 局部停止的精确反例、逆重放验证、固定长度认证，
   以及把跨精度分叉变成稀疏可审计修正（BDS/SPRC）。局限：单模型单 GPU、无真人盲评、
   无跨硬件验证、无任意模型必然终止证明，也尚无现实不可检测性结论；当前是 working paper。

---

# E. 项目真实性检查清单（不能夸大的表述）

| 可说（含限定） | 不可说 |
|---|---|
| 复现、比较并扩展 SparSamp 与 RRC 两条路线 | 融合成一个新算法 |
| Verified-RRC 在 500 个 Mock 样本上精确恢复（R012） | 形式化验证了所有输入 / 任意模型必然终止 |
| 原局部规则在 R012 样本上恢复率 87%–96% | RRC 原论文所有实现都错误（正确说法：在本项目采用的 Algorithm 3/4 形式化下，局部停止条件不是精确恢复的充分条件） |
| R020 Mock 400/400 恢复、0 错 key 接受 | 固定长度 RRC 已消除所有统计泄漏 |
| Qwen smoke N=224 完成 4/4（小样本） | 已证明现实不可检测 / 语义质量更高 |
| R044：指定环境中校正后 60/60、未校正 10/60、平均修正率 2.16% [1.80,2.53] | 跨模型、跨硬件通用结论 |
| R051：SPRC 1,148 B = 完整轨迹的 24.76%（引用共享 bundle 口径） | 任何口径下都小于完整轨迹（三个口径是不同估计量） |
| R059：独立 seed 40/40 精确回放、0 false-safe（Qwen2.5-1.5B + RTX 3060 Laptop + 指定栈） | 跨硬件绝对可复现 |
| R002：1,193/1,200 完成、846/846 无歧义精确解码、16/16 容量误差 ≤5% | 严格复现官方 Torch 2.2.2 依赖环境（实为兼容环境） |
| 当前为 working paper / 项目阶段成果 | 已发表 / 已投稿 |
| 逐步 token 分布匹配 + 固定公开长度可缓解停止长度通道 | 零 KL / 完全不可检测 / 通用安全证明 |

引用建议：SparSamp（USENIX Security 2025, arXiv:2503.19499）；RRC（Yan & Murawaki,
*Efficient Provably Secure Linguistic Steganography via Range Coding*, ACL 2026）。
如面试中被要求给论文链接，一律回答“working paper / 项目仓库”，不给虚假发表状态。
