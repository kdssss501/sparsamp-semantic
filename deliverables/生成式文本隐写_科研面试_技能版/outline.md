# Deck Outline：大语言模型生成式文本隐写的可靠编码与跨精度回放研究

- 用途：科研面试 / 保研面试，8 分钟；听众为计算机学院老师（懂机器学习基础，不熟悉文本隐写）
- 页数：10 页；比例：16:9；语言：中文
- 生成方式：codex-ppt 技能，整页生成图模式（每页为一张完整幻灯片图，文字由生图模型渲染，样张环节验证中文质量）
- 内容原则：每页关键信息都有项目材料出处；未经材料支持的内容一律不写
- 本文件为大纲草稿：尚未生成 deck_spec.json、提示词、样张或 .pptx

## Slide 1 封面（cover）
- 项目名：《大语言模型生成式文本隐写的可靠编码与跨精度回放研究》
- 汇报场景：科研面试 / 保研面试 · 8 分钟
- 姓名 / 学校 / 专业（占位，待用户提供）
- 一句话定位：复现、比较并扩展 SparSamp 与 RRC 两条生成式文本隐写路线
- 状态：working paper / 项目阶段成果（不写“已发表/已投稿”）
- 视觉：深蓝学术封面 + 概率条/隐写通道概念示意
- 依据：README.md、RESEARCH_BRIEF.md

## Slide 2 研究背景与动机（context）
- 生成式隐写：利用 next-token 概率分布嵌入秘密消息，接收端凭相同密钥/模型/配置回放
- 难点 1：自然性、容量、可恢复性、可检测性互相牵制
- 难点 2：随机生成对数值精度敏感，一个 token 分叉会沿自回归轨迹放大
- 实证引子：FP16→BF16 未校正时 60 条轨迹仅 10 条精确重放（R044）
- 视觉：背景概念图（token 概率分布 + 隐写通道）
- 依据：README.md、docs/reproducibility/R044_ANALYSIS.md

## Slide 3 研究问题与证据边界（problem framing）
- 核心问题：可靠恢复 + 数值回放一致性如何做到“可验证”
- 关键边界 1：逐步匹配 token 分布 ≠ 变长全文分布匹配（精确反例 TV=1/2）
- 关键边界 2：本项目不宣称零 KL、完全不可检测、通用安全或跨硬件确定性
- 研究问题的表述：公开离散概率合同 + 稀疏目标特定修正能否实现精确重放
- 视觉：四目标矛盾图 + 边界标注
- 依据：docs/verified_rrc_theory.md §3/§4、RESEARCH_BRIEF.md

## Slide 4 技术路线总览（comparison）
- 路线 A：SparSamp（USENIX Security 2025, arXiv:2503.19499）—— 复现与比较对象
- 路线 B：RRC（Yan & Murawaki, ACL 2026，Algorithm 3/4）—— 可靠性审计与扩展对象
- 官方复现实证：Basic Test 105 tokens / 576 bits / 5.486 bit/token 精确解码（R001）
- 兼容矩阵：R002 共 1,200 配置、1,193 完成；无歧义子集 846/846 精确解码；16/16 容量误差 ≤5%（最大 4.12%）
- 动作词：复现、比较、扩展；不写“融合成新算法”
- 视觉：双路线对比 + 复现数据卡
- 依据：docs/rrc.md、docs/reproducibility/R002_OFFICIAL_MATRIX.md、RESEARCH_BRIEF.md

## Slide 5 SparSamp 原理与复现（concept）
- 原理：候选 token 概率分布 + 共享密钥受控偏移 + 消息块决定稀疏区间落点
- 恢复：block 区间收缩到单点后确定全部 bit，接收端反向回放
- 项目角色：复现与对比；FH-SparSamp v1 在 128-token 预算下 2/6，已被负面结果拒绝，不作为推荐
- 表述：关键不是“强行指定词”，而是可回放的受控采样
- 视觉：概率分布稀疏采样示意（原生绘图风格可由样张确认）
- 依据：docs/fh_sparsamp.md、refine-logs/R005_FH_V1_RESULTS.md

## Slide 6 RRC 原理与关键审计发现（key finding）
- 原理：消息 m∈[0,2^l)；每步共享偏移旋转秘密点，按 token 概率分割区间，选中含秘密点子区间
- 关键发现：论文局部停止条件 -1/2<mid−d≤1/2 不是精确恢复的充分条件
- 精确反例：M=8, m=3，条件满足但恢复 5≠3；失败区域正测度 1/1024
- 根因：反向模旋转跨越切点，圆周距离保持 ≠ 线性距离保持
- 表述边界：限定“本项目采用的 Algorithm 3/4 形式化下”；不写“原论文全部错误”
- 视觉：区间收缩示意 + 跨边界几何示意
- 依据：docs/rrc.md、docs/verified_rrc_theory.md §4、refine-logs/R019_VERIFIED_RRC_THEORY_AUDIT.md

## Slide 7 方法改进一：Verified-RRC 与 Fixed-Length（method）
- Verified-RRC：局部条件满足后完整逆重放，确认能恢复才停止
- 实证：R012 Mock 500/500 精确恢复；原局部规则 87%–96%；平均仅 +0.04–0.15 token（最大 +2）
- Fixed-Length RRC：固定公开长度 N，payload‖HMAC 帧，缓解停止长度泄露
- 实证：R020 Mock 400/400、0 错 key 接受；Qwen smoke N=224 完成 4/4（小样本）
- 边界：非任意模型必然有限终止；R021 4 对 matched cover 未见稳定熵偏移（1.110 vs 1.124 bit/token），不构成不可检测结论
- 视觉：验证流程 + 认证帧结构示意
- 依据：refine-logs/R012_VERIFIED_RRC_RESULTS.md、R020_FIXED_LENGTH_RRC_V1.md、R021_FIXED_LENGTH_MATCHED_COVER.md、docs/fixed_length_rrc.md

## Slide 8 方法改进二：BDS 跨精度回放（method/evidence）
- 问题：FP16→BF16 未校正仅 10/60 精确；平均修正率 2.16% [1.80, 2.53]
- 机制：公开整数概率合同（量化 bin、top-16 envelope、top-2、整数 mass）+ 有限枚举可行决策集
- 实证：R059 独立 seed 40/40 精确回放、0 false-safe；证书负载/完整轨迹 ≈54.6%
- 边界：Qwen2.5-1.5B-Instruct、RTX 3060 Laptop、指定软件栈；≠跨硬件保证
- 视觉：分叉-证书概念图；可复用工作论文 Figure 1
- 依据：docs/reproducibility/R055/R056/R058/R059、RESEARCH_BRIEF.md
- 可选输入图：paper/ccfa_bounded_decision/figures/figure_01_architecture.png（已生成概念图）

## Slide 9 实验结果汇总（data evidence）
- 主图（真实数据）：校正后 60/60 vs 未校正 10/60，平均修正率 2.16%（R044，fig2_main_scale）
- 方向消融（真实数据）：BF16→FP16 双向 20/20（R046，fig4_precision_direction）
- 开销对比（真实数据）：SPRC 1,148 B = 完整轨迹的 24.76%，小于 4-token block-repair 1,408 B（R051）
- 边界：三类开销口径（payload-only 6.65% / referenced 24.76% / self-contained 63.89%）是不同估计量
- 视觉：真实数据图 + 结果卡
- 必用输入图：figures/fig2_main_scale.png（严格输入）、deliverables/assets/fig4_precision_direction.png（严格输入）
- 依据：figures/source_data/figure_02_source.csv、docs/reproducibility/R044_ANALYSIS.md、R046_ABLATION_ANALYSIS.md、R051_REPLAY_BASELINES.md

## Slide 10 局限、未来与总结（summary）
- 三点总结：RRC 停止正确性审计 + Verified-RRC；跨精度稀疏修正回放；BDS 独立确认
- 局限：单模型单 GPU、无真人盲评（R048 未收集）、无跨硬件验证、无任意模型终止证明
- 未来：扩大模型/硬件矩阵、固定长度失败率区间、整数频数合同、盲评与检测实验
- 状态声明：working paper / 项目阶段成果
- 视觉：三结果卡 + 边界行
- 依据：RESEARCH_BRIEF.md、paper/CLAIM_EVIDENCE_MAP.md、paper/AUTHOR_NOTES_ZH.md

## 必用/可选输入图汇总
- Slide 9（严格输入，真实数据）：figures/fig2_main_scale.png；deliverables/assets/fig4_precision_direction.png
- Slide 8（可选，已有概念图）：paper/ccfa_bounded_decision/figures/figure_01_architecture.png
- Slide 1/2/5/6/7/8 的概念视觉：由生图后端生成（九秋 gpt-image-2 或经确认的后端）

## 内容真实性红线（贯穿全 deck）
- 不写：已发表/已投稿、融合新算法、零 KL、完全不可检测、通用安全、跨硬件保证、原论文全部错误
- 可写（带限定）：Mock 范围、小样本、指定模型/GPU/软件栈、working paper
