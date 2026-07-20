# R036-D2：List-decoding PSS 全文与理论审计

## Material Passport

- Origin Skill: academic-research-suite / deep-research
- Origin Mode: fact-check
- Origin Date: 2026-07-20
- Verification Status: ANALYZED
- Version Label: r036d2_list_decoding_pss_audit_v1

## Source Verification Report

### Overall Assessment

- **Source**: Pang, Kaiyi, and Minhao Bai. *Provably Secure Steganography Based on List Decoding*.
- **Primary identifier**: [arXiv:2604.21394v3](https://arxiv.org/abs/2604.21394v3)
- **Published**: 2026-04-23; v3 updated 2026-04-29
- **Affiliation**: Tsinghua University
- **Existence**: VERIFIED against the official arXiv API, PDF, and TeX source
- **Peer review**: not confirmed; current source is a preprint
- **Public implementation**: UNVERIFIED / NOT FOUND
- **Semantic Scholar cross-check**: unavailable because the public API returned HTTP 429
- **Overall use decision**: include as a recent mechanism baseline with major theoretical caveats

Downloaded primary artifacts:

| Artifact | SHA-256 |
|---|---|
| arXiv v3 PDF | `5619E7F14B2D964D7B8C23553929B781F2DECE3CEA67E1887B89F484320D4B54` |
| arXiv v3 TeX source | `8C80F3EA7A2A7E2940D1D113C8BF324646B58FC43348B86D0FEB283E637ADA5E` |

TeX source保存在本地 Git-ignored 目录
`.artifacts/papers/list-decoding-pss-v3/source/`。论文正文和参考文献没有作者代码链接；
GitHub 官方 repository search 对完整标题、arXiv ID 和作者加主题三组查询均返回 0。
这只能说明本次检索未找到公开仓库，不能证明代码永远不存在。

### Source Quality Matrix

| Dimension | Assessment | Evidence |
|---|---|---|
| Venue | WARN | arXiv preprint，未确认同行评审 |
| Author | PASS | arXiv source给出清华大学 affiliation 与机构邮箱 |
| Method disclosure | PASS/WARN | 有编码/解码伪代码、证明和实验设置，但无可核验代码 |
| Mathematical support | RED FLAG | 正确性界与容量下界存在关键推导缺口 |
| Currency | PASS | 2026 年当前工作 |
| COI/funding | WARN | 正文未发现明确 funding/COI disclosure |
| Reproducibility | FAIL | 未找到公开代码，无法核验 7 个基线和主要数值 |

## Verified Mechanism

论文方法不是维护多个概率分布，而是在**同一个共享模型分布和同一个 PRG 采样映射**下维护
消息前缀列表：

1. 初始化 `2^N` 个 N-bit 候选消息；
2. 用共享 PRG 为每个候选从模型分布独立采样，构造消息到 token 的映射 `F`；
3. 输出真实消息前缀对应的 token，并保留该 token 的全部 pre-image；
4. 当列表不超过 `2^(N-1)` 时给每个候选追加 0/1，恢复较大列表；
5. 负载后追加共享伪随机 suffix，从最终列表中选出唯一匹配消息。

论文默认 `N=20`、suffix `b=20`，即每一步最多维护和采样约 1,048,576 个候选。
Alias table准备复杂度为 `O(|V|)`，每步候选采样/映射/过滤仍为 `O(2^N)`；论文实验使用
3 个约 7B 模型、2 张 A5000 和 24 核 CPU。

论文报告 Qwen2 上 ours 为 `1.5971 bit/token`、利用率 `0.9906`，SparSamp 为
`1.3562 bit/token`、利用率 `0.9069`。这些是作者报告值，本项目尚未独立复现。

## Compatibility Verdict

该机制**不能直接修复 R036-D1**。论文 TeX `main.tex:174-175` 明确假设发送端和接收端
都能访问相同的完整条件分布，并把不同模型/非对称场景排除在范围外。编码和解码还必须
重建完全相同的 alias mapping `F`。FP32/FP16 的 support 或 integer counts 一旦不同，
同一个 PRG 数值可能映射到不同 token，消息候选列表也会失步。

因此：

- 它可以在 R038 中作为“相同概率合同上的容量 coder”基线；
- 它不是 precision-hardened PSS，也不是 R036-D1 的现成修复；
- 在未取得作者代码前，按既定规则标记为缺失实现基线，不根据摘要自行补写完整实现。

## Mathematical Audit

### 1. Correctness bound lacks a list-level union bound

Proposition 3.1 只给出任意一个非真实候选 `m` 通过 suffix 的概率上界

\[
\alpha = \frac{2^{-b}}{(1+\sqrt{\lambda/2^N})^n}.
\]

但唯一解码失败事件是“至多 `2^N-1` 个错误候选中至少一个通过”。即使接受单候选上界，
也只能先得到

\[
\Pr[\text{any false candidate survives}] \le (2^N-1)\alpha.
\]

论文从单候选直接跳到全列表唯一性，并在实验中用 `N=b=20` 报告约
`8.695e-7` 的错误上界，没有计入候选数量因子。该具体正确性界不能视为已证明。

### 2. Hoeffding threshold directions are inconsistent

在 `main.tex:341-348` 中，要使 `exp(-2 delta^2 2^(N-1)) <= exp(-lambda)`，选取的
偏差阈值平方应至少达到相应量级；正文却将其写成 `delta <= sqrt(lambda/2^N)`，随后又用
更大的 denominator 得到更小概率上界，方向不成立。若把 delta 解释为固定阈值而非实际
偏差，相关符号和条件仍需重新表述与证明。

### 3. Capacity proof contains an invalid weighted-to-unweighted inference

`main.tex:464-483` 从

\[
\sum_i p_i^2\delta_i^2 \le \lambda/2^N
\]

推得

\[
\sum_i \delta_i^2 \le \lambda/2^N.
\]

由于 `0 <= p_i <= 1`，可得的是
`sum p_i^2 delta_i^2 <= sum delta_i^2`，不能由较小的带权和上界推出较大的无权和上界。
同一段把指数尾界小于 `exp(-lambda)` 对应的条件也写成了相反方向。因此论文给出的接近
熵极限容量下界在当前 v3 推导下未被验证。

### 4. Security claim depends on exact synchronized sampling

固定候选索引对应 i.i.d. 模型样本，因此在理想精确采样下单步边缘分布为模型分布；这一
hybrid 思路是合理的。但是全文证明没有处理：

- FP32/FP16 或不同硬件导致的 alias table 差异；
- 有限精度采样偏差；
- PRG 每轮 domain separation 和多查询形式化；
- `2^N` 与安全参数的关系及多项式时间要求；
- 可变停止长度可能泄漏的信息（定义只比较相同输出长度）。

因此其安全结论只能在论文的理想、对称、精确分布假设下引用。

## Research Integration

真正对应 R036-D1 的新方向不是复制消息列表，而是 **Contract-List SparSamp**：

- 编码端继续使用已定义的 Bin-Mass 分布，不改变 stegotext 采样分布；
- 解码端为 support 边界交换、量化 bin 邻域和稀疏区间状态维护有限 beam；
- observed token 只淘汰不兼容合同路径，不因单一 FP16 top-2 support 缺失立即失败；
- byte/window suffix 或认证标签用于剪枝并选择唯一消息路径；
- 正确性改为证明或实测“真实 FP32 合同路径留在 beam 中”的概率。

这和论文的 message-prefix list 是不同对象，不能宣称复现或直接继承其理论。优点是解码器
列表不改变编码分布，理论上不会额外增加 stegotext 分布偏差；代价是 beam 宽度、路径
爆炸和正确合同覆盖率需要独立分析。

下一步先做 oracle 可行性审计：对每个 FP32 top-2 合同，测它是否包含在 FP16 top-`K`
支持与量化 bin 邻域中，并计算覆盖正确路径所需的最小 `K`、bin 半径和 beam width。
只有小 beam 能覆盖至少 `5/6` 消息轨迹，才实现 Contract-List decoder。

## Verification Limitations

- Semantic Scholar API 因 HTTP 429 未完成 Tier-0 交叉核验，已按 graceful degradation 记录；
- 未联系作者索取代码；
- 未复现作者 7B 模型实验；
- 数学问题为对 arXiv v3 TeX 的本地审计，不等同于正式同行评审结论；后续版本可能修正。
