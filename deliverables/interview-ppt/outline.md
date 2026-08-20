# Deck Outline：大语言模型生成式文本隐写的可靠编码与跨精度回放研究

用途：科研面试 / 保研面试，8 分钟，听众为计算机学院老师（了解机器学习基础，不熟悉文本隐写）。
页数：10 页，16:9。风格：学术白底、深灰正文、深蓝强调、青绿=改进、橙色=风险/边界、红=禁止表述。
生成方式（用户确认）：codex-ppt 编排 + 原生可编辑幻灯片承载（文字/图表用 PPT 原生元素，符合用户视觉要求）；
插图通过 imagegen 技能调用九秋工作台（dingdangapii.cn，模型 gpt-image-2）生成，nature 风格、白底、无文字。

## Slide 1 标题页
- 项目名、汇报场景（科研面试 / 保研面试 · 8 分钟）
- 姓名 / 学校 / 专业（占位，待填写）
- 一句定位：复现、比较并扩展 SparSamp 与 RRC 两条生成式文本隐写路线
- 状态：working paper / 项目阶段成果（不写已发表/已投稿）
- 视觉：概念插图 fig_cover_stego_channel（可选，原生概率条示意兜底）
- 角色：cover

## Slide 2 研究背景
- LLM 每步给出 next-token 概率分布；生成式隐写利用概率表嵌入秘密消息
- 接收端需相同密钥、模型、配置才能回放恢复
- 随机生成对数值精度敏感：一个 token 分叉会沿自回归轨迹放大（R044：未校正仅 10/60 精确重放）
- 视觉：fig_stego_channel（背景概念图）或原生卡片
- 角色：context

## Slide 3 问题定义
- 四目标：自然性、容量、可恢复性、可检测性（相互牵制）
- 逐步匹配 token 分布 ≠ 变长全文分布匹配（精确反例 TV=1/2，docs/verified_rrc_theory.md）
- 本项目聚焦：可恢复性 + 数值回放一致性；其余目标只报告证据边界
- 边界：不宣称零 KL、完全不可检测、通用安全
- 角色：problem framing（2×2 卡片，原生绘制）

## Slide 4 技术路线
- 路线 A：SparSamp（USENIX Security 2025, arXiv:2503.19499）—— 复现与比较对象
  - 官方 artifact 兼容复现：105 tokens / 576 bits / 5.486 bit/token 精确解码
  - R002：1,193/1,200 完成；846/846 无 Token Ambiguity 精确解码；16/16 容量误差 ≤5%（最大 4.12%）
- 路线 B：RRC（Yan & Murawaki, ACL 2026，Algorithm 3/4）—— 本项目可靠性审计对象
- 项目动作：复现、比较、扩展；不宣称“融合成新算法”
- 角色：comparison（原生双卡对比）

## Slide 5 SparSamp 原理
- 概率分布：模型给候选 token 分配概率
- 密钥偏移：共享密钥/PRF 产生受控偏移，双方可重放
- 稀疏采样：消息块决定稀疏区间内落点，block 收缩到单点后恢复全部 bit
- 本项目角色：复现与对比（FH-SparSamp v1 已被负面结果拒绝，不作为推荐）
- 视觉：fig_sparsamp_sampling（概念图）
- 角色：concept

## Slide 6 RRC 原理
- 消息 m ∈ [0, M)，M=2^l；初始区间 I=[0,M)
- 每步共享偏移 o_t 旋转秘密点；模型概率把区间切成 token 子区间
- 选择含秘密点的子区间，输出 token；区间逐 token 收缩
- 接收端按相同前缀/偏移/分割反向重放恢复 m
- 视觉：fig_rrc_interval（概念图）
- 角色：concept / process

## Slide 7 关键发现
- 论文局部停止条件：-1/2 < mid(I^t)-d^t ≤ 1/2
- 精确两步有理数反例：M=8, m=3，条件满足但恢复 5≠3（docs/verified_rrc_theory.md §4）
- 失败不是零概率：独立偏移落入正测度失败区域概率 = 1/1024
- 根因：反向模旋转跨越切点，圆周距离保持 ≠ 线性距离保持
- 表述边界：在本项目采用的 Algorithm 3/4 形式化下不充分；不说“原论文全部错误”
- 视觉：fig_counterexample_wrap（几何示意）
- 角色：key finding

## Slide 8 方法改进
- Verified-RRC：局部条件满足后先完整逆重放，确认能恢复才停止
  - R012：500/500 Mock 精确恢复；原规则 87%–96%；平均仅 +0.04–0.15 token（最大 +2）
- Fixed-Length RRC：固定公开长度 N，payload||HMAC 帧；缓解停止长度泄露
  - R020 Mock：400/400 恢复、0 错 key 接受；Qwen smoke N=224 完成 4/4（小样本）
- 认证帧：F = m || HMAC(K_auth, domain||l||context||m)[:a]（默认 a=128）
- 边界：非任意模型必然有限终止；小样本不构成不可检测证明
- 视觉：fig_hmac_frame（认证帧/固定长度概念图）
- 角色：method

## Slide 9 工程可靠性
- 问题：FP16→BF16 未校正仅 10/60 精确；平均修正率 2.16% [1.80, 2.53]
- BDS：公开整数概率合同 + 有限枚举可行决策集；稳定步省略、不稳定步记录
- R059 独立 seed：40/40 精确回放、0 false-safe、证书负载/完整轨迹 ≈54.6%
- 边界：Qwen2.5-1.5B-Instruct、RTX 3060 Laptop、指定软件栈；≠跨硬件保证
- 视觉：fig_bds_replay（分叉/证书概念图）
- 角色：method / evidence

## Slide 10 结果与总结
- 结果 1：RRC 停止正确性审计 + Verified-RRC（500/500 Mock）
- 结果 2：跨精度回放 60/60 vs 10/60；SPRC 1,148B = 完整轨迹的 24.76%（R051）
- 结果 3：BDS 独立确认 40/40、0 false-safe（R059）
- 局限：单模型单 GPU、无真人盲评、无跨硬件、无通用安全；working paper 阶段
- 未来：扩大模型/硬件矩阵、固定长度失败率区间、整数频数合同、盲评与检测
- 视觉：真实数据图 assets/fig2_main_scale.png（R044，真实数据）
- 角色：summary

## 需要的生图（九秋工作台，gpt-image-2，nature 风格，白底无文字）
1. fig_cover_stego_channel.png —— 标题/背景：概率分布与隐写通道概念
2. fig_sparsamp_sampling.png —— SparSamp 稀疏采样
3. fig_rrc_interval.png —— RRC 区间旋转收缩
4. fig_counterexample_wrap.png —— 跨边界反例几何
5. fig_hmac_frame.png —— HMAC 认证帧与固定长度
6. fig_bds_replay.png —— FP16/BF16 分叉与稀疏修正证书

## 必须嵌入的真实数据图（已有）
- deliverables/assets/fig2_main_scale.png（R044：60/60 vs 10/60）
- deliverables/assets/fig4_precision_direction.png（R046：双向 20/20）
- paper/ccfa_bounded_decision/figures/figure_01_architecture.png（BDS 概念图，已由九秋生成）
