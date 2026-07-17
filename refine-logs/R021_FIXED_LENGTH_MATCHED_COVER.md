# R021 Fixed-Length Matched Cover 与量化偏差审计

日期：2026-07-17

## 研究问题

R020 证明固定公开长度可以移除直接停止长度通道，但当时缺少两个必要门禁：同控制器的
fixed-length cover 基线，以及论文方向的量化偏差 `KL(Q||R)`。R021 补齐这两个门禁，回答：

1. stego 与同配置 cover 是否使用相同的可见长度和量化条件分布；
2. `1e-15` Decimal 量化实际把 top-p 目标 `Q_t` 改变了多少；
3. 小样本 Qwen 轨迹中是否出现明显的熵、候选数或 Token Ambiguity 差异。

## 实现升级

- `FixedLengthCoverSampler` 在相同 prompt、模型、采样控制器、量化规则和公开长度 `N` 下，
  逐步直接采样 `R_t`，不嵌入 payload。
- cover、嵌入和 padding 使用独立 HMAC domain；payload seed 只派生可复现的 cover 随机流。
- `DistributionSnapshot` 直接计算每步 `KL(Q_t||R_t)` 与 `TV(Q_t,R_t)`。
- `StepRecord` 保存逐步量化指标；实验结果保存均值、最大值和路径累计值。
- 新增 `mean_visible_entropy_bits`，平均所有公开 token 的条件熵；原
  `mean_entropy_bits` 继续只表示嵌入步骤，不能用于纯 cover 比较。

## 数学口径

对第 `t` 步给定相同历史 `h`，令 top-p 归一化分布为 `Q_t(.|h)`，量化实现为
`R_t(.|h)`：

```text
KL(Q_t||R_t) = sum_x Q_t(x|h) log(Q_t(x|h) / R_t(x|h)),
TV(Q_t,R_t) = 1/2 sum_x |Q_t(x|h) - R_t(x|h)|.
```

完整自回归联合 KL 的链式公式是：

```text
KL(Q^N||R^N)
  = E_{X~Q^N} [sum_t KL(Q_t(.|X_<t)||R_t(.|X_<t))].
```

因此，单条生成轨迹上的条件 KL 和是路径诊断，不是无需期望的完整联合 KL。已观测路径上的
逐步 TV 和也不能直接升级为所有历史上的全文 TV 上界。R021 报告这些量用于检查量化误差，
不把它们当作现实不可检测证明。

`truncation_kl_nats` 仍记录 `KL(Q_t||P_t)=-log Z_t` 的路径累计值；若 `P_t` 在被删除支持上
有正概率，则相反方向 `KL(P_t||Q_t)=infinity`。它与 `KL(Q_t||R_t)` 是不同偏差来源。

## 实验设置

- 模型：本地 Qwen2.5-1.5B-Instruct，FP16；
- `top_p=0.95`，temperature `0.8`，`probability_quantum=1e-15`；
- payload 128 bits，HMAC 标签 64 bits；
- 固定公开长度 `N=224`；
- 2 个中文 prompt x 2 个 payload seed；
- 每个 prompt/seed 生成一条 stego 和一条独立 matched cover；
- 密钥只通过进程环境变量注入，未写入配置或仓库。

原始结果保存在忽略提交的 `outputs/R021_qwen_matched_cover_v2.jsonl`。

## 原始轨迹表

| Variant | Prompt | Seed | 状态 | 可见熵 | 候选数 | 累计 KL(Q||R) | 平均每步 TV | 截断 KL | 完成前缀 | Ambiguity |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| stego | 0 | 0 | complete | 1.1707 | 7.3705 | 1.0646e-26 | 8.9859e-16 | 6.2490 | 175 | true |
| cover | 0 | 0 | cover | 0.9159 | 5.4554 | 6.8734e-27 | 6.3386e-16 | 5.8993 | 0 | true |
| stego | 0 | 1 | complete | 1.2597 | 6.8080 | 5.5754e-27 | 8.5189e-16 | 7.3110 | 151 | false |
| cover | 0 | 1 | cover | 1.2399 | 7.6875 | 1.0301e-26 | 9.7142e-16 | 6.9636 | 0 | false |
| stego | 1 | 0 | complete | 0.9160 | 4.1875 | 1.6851e-27 | 4.8275e-16 | 6.0113 | 218 | false |
| cover | 1 | 0 | cover | 1.3075 | 8.0402 | 1.2976e-26 | 1.0354e-15 | 6.9270 | 0 | false |
| stego | 1 | 1 | complete | 1.0927 | 5.3259 | 3.2269e-27 | 6.2958e-16 | 6.6179 | 193 | false |
| cover | 1 | 1 | cover | 1.0339 | 5.2768 | 3.4876e-27 | 6.4115e-16 | 6.4964 | 0 | false |

## 汇总比较

均值后的 `+/-` 为 4 条轨迹的样本标准差。

| 指标 | Stego | Matched cover | Stego - cover |
|---|---:|---:|---:|
| 可见熵 bit/token | 1.1098 +/- 0.1461 | 1.1243 +/- 0.1812 | -0.0145 +/- 0.2716 |
| 平均候选数 | 5.9230 +/- 1.4430 | 6.6150 +/- 1.4511 | -0.6920 |
| 每轨迹累计 KL(Q||R) | 5.2835e-27 +/- 3.9168e-27 | 8.4095e-27 +/- 4.1236e-27 | -3.1260e-27 |
| 平均每步 TV | 7.1570e-16 +/- 1.9466e-16 | 8.2046e-16 +/- 2.1289e-16 | -1.0476e-16 |
| 路径累计截断 KL | 6.5473 | 6.5716 | -0.0243 |
| Token Ambiguity | 1/4 | 1/4 | 0 |

相对 matched cover，stego 可见熵均值低 `1.29%`，平均候选数低 `10.46%`。但只有 4 对样本，
可见熵配对差的标准差 `0.2716` 远大于均值差 `0.0145`；候选数差也受 prompt 1/seed 0 的
单条大差异影响。这里不能声称存在提升或退化，只能说未观察到稳定方向。

## 恢复与现实信道

- 4/4 stego 在 `N=224` 内完成，私有完成前缀为 `151-218`，平均 `184.25` token；
- 4/4 从生成 token IDs 认证并精确恢复 128-bit payload；
- 固定公开净容量为 `128/224 = 0.571 bit/token`；包含 64-bit 标签的帧率为
  `192/224 = 0.857 bit/token`；
- stego prompt 0/seed 0 在 index 200 重分词 token ID 不同；
- cover prompt 0/seed 0 在 index 180 重分词 token ID 不同；
- 两个歧义样本重分词后仍为 224 token，但 token ID 序列不同。

这说明 Token Ambiguity 不是 stego 独有，却仍阻断“仅传输公开字符串即可可靠恢复”的端到端
结论。当前准确率只适用于原 token ID 信道。

## 结论

1. matched cover 基线已经实现，R020 的固定长度条件分布论证现在有可执行对照组。
2. `1e-15` 量化的每步偏差约为 `1e-15 TV`、每轨迹累计 `KL(Q||R)` 约为 `1e-27`；在当前
   数值精度下量化不是主要容量或语义瓶颈。
3. 4 对样本没有显示稳定可见熵偏移，但样本远不足以支持检测器或不可检测性结论。
4. 当前首要现实故障仍是 Token Ambiguity，其次是 224-token 预算的未知总体失败率。

## 下一门禁

1. 冻结 `N=224`，扩展到预注册的多 prompt、多 seed holdout，给完成率和 ambiguity 率报告
   二项置信区间。
2. 同时保存原 token IDs 与公开文本重分词 IDs，按首个差异位置、Unicode 边界和 token bytes
   分类 ambiguity。
3. 在样本量足够后训练固定长度 stego/cover 检测器，并使用严格分离的 prompt holdout；熵和
   候选数只能作为诊断，不能替代 steganalysis。
4. 若目标是现实文本信道，优先实现 tokenizer-synchronized 或可逆 token serialization；在此
   门禁通过前，不扩大“端到端可靠隐写”的声明。
