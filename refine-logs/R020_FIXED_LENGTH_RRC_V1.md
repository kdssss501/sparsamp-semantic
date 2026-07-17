# R020 Fixed-Length Verified-RRC V1

日期：2026-07-17

## 研究问题

Verified-RRC 在 payload 完成时立即停止，公开文本长度因此携带内部停止时间。R019 已用精确
反例证明：即使活动步骤 token 条件分布和长度边缘分布都匹配，数据相关停止仍可使完整变长
序列的总变差距离达到 `1/2`。

V1 的目标是隐藏真实完成前缀 `T`，把输出形状固定为公开 token 数 `N`，同时让接收端无需
旁路元数据即可定位 payload 前缀。

## 算法升级

1. 对任意 raw bit payload 添加 domain-separated HMAC 标签。
2. 使用 Verified-RRC 嵌入 `payload || tag`。
3. 完成后不立即输出，而是从相同量化目标分布继续采样至公开长度 `N`。
4. 解码器只前向重放模型一次，在每个前缀执行逆重放并检查认证标签。
5. 不公开真实嵌入 token 数；该值仅保留在本地审计记录。
6. 预算不足时默认抛出 `IncompleteEncodeError`；`cover` 模式可返回固定长度 fallback，但明确
   标记未携带有效消息。

## 数学边界

- 条件正确性：真实 Verified-RRC 前缀必然成为一个认证候选。
- 理想 `a` bit 标签扫描至多 `N` 次的误接受 union bound 为 `N/2^a`。
- 若嵌入和 padding 每一步都条件采样自相同量化分布 `R_t`，总长度固定为 `N`，则理想随机
  偏移下的全文联合分布由链式法则匹配同配置固定长度 cover。
- 真实 HMAC 结论依赖 PRF/MAC 假设；Decimal 重放和有限随机网格仍保留 R019 的限制。
- 删除失败样本或反复重试会按成功事件条件化，不能继续声称无条件分布匹配。

## 预算选择

先用 seed `0-19` 做预算 pilot。初始公式 `ceil(frame_bits/1.25)+8` 无 fallback，但 padding
过多，128-bit payload 的公开净容量仅为 `0.790 bit/token`。

随后固定 holdout 预算公式：

```text
N = ceil((payload_bits + 64) / 1.7) + 8.
```

预算固定后，使用不重叠 seed `1000-1099`，不再根据 holdout 结果修改参数。

## Mock Holdout 结果

Provider 概率固定为 `(0.4,0.3,0.2,0.1)`，每种 payload 100 个样本，标签 64 bits。

| Payload | Public N | 成功恢复 | Fallback | Wrong-key 接受 | 平均私有前缀 | 平均 padding | 净 bit/token |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 56 | 100/100 | 0 | 0 | 42.72 | 13.28 | 0.286 |
| 32 | 65 | 100/100 | 0 | 0 | 51.85 | 13.15 | 0.492 |
| 64 | 84 | 100/100 | 0 | 0 | 69.20 | 14.80 | 0.762 |
| 128 | 121 | 100/100 | 0 | 0 | 103.99 | 17.01 | 1.058 |

总计 400/400 完整恢复、0 fallback、0 wrong-key 接受。这只是确定性 Mock holdout，不代表
Qwen、跨硬件重放或真实文本 steganalysis 已通过。

128-bit、`N=121`、64-bit 标签时，理想认证扫描误接受 union bound 为

```text
121 / 2^64 approximately 6.56e-18.
```

## 当前代价

- 短 payload 的认证开销明显：16-bit payload 中标签占 frame 的 80%。
- 固定长度 padding 降低净容量，但 128-bit Mock 仍达到 `1.058 bit/token`。
- 解码在首次认证前缀 `T_auth` 返回，需 `T_auth <= N` 次模型前向；每个前缀完整逆重放，
  算术最坏复杂度仍为 `O(N^2)`。
- 固定 token 长度不保证自然句尾，不能再附加数据相关标点收尾而声称同一固定长度定理。

## 下一门禁

1. 为同配置量化分布实现 fixed-length cover baseline。
2. 直接计算 cover `Q` 到实现 `R` 的论文方向 `KL(Q||R)`。
3. 扩展 Qwen prompt/seed，估计 224-token fallback 率置信区间。
4. 在成功率稳定后比较固定长度 RRC 与变长 Verified-RRC 的 steganalysis。

## Qwen 单样本 Smoke

模型为本地 Qwen2.5-1.5B-Instruct、FP16、`top_p=0.95`、temperature `0.8`，128-bit raw
payload 加 64-bit 标签。使用同一 prompt 和 payload seed 比较两个预设公开长度：

| Public N | 状态 | 私有完成前缀 | Padding | 认证解码 | Token Ambiguity | 净 bit/token |
|---:|---|---:|---:|---|---|---:|
| 160 | cover fallback | 未完成 | 0 | 不适用 | false | 0 |
| 192 | complete | 181 | 11 | exact | false | 0.667 |

成功样本的编码吞吐为 `12.94 token/s`。该结果只证明真实 Qwen 链路能够完成固定长度认证恢复，
同时说明 160-token 预算不足；`1/1` 成功不能外推为 Qwen 完成率，必须继续运行多 prompt、
多 seed 预算实验。

完成首轮 2 prompts x 2 seeds 后，160-token 完成率为 `1/4`，192-token 完成率为 `3/4`；
所有成功样本均认证解码正确，8/8 无 Token Ambiguity。唯一的 192-token fallback 平均熵仅
`0.854 bit/token`、平均候选数约 4.05，是本轮最低熵轨迹。基于这一结果，第二阶段新增
`N in {224,256}` 用于定位可靠预算；这是事后自适应扩展，必须与首轮预设预算分开报告。

第二阶段首次运行发现：224-token 四条轨迹均成功，但 256-token 中两条在解码 padding 时出现
`fixed-length RRC interval collapsed to zero`。根因不是消息未完成，而是解码器在已经发现
认证前缀后仍继续缩小区间。V1.1 改为首次认证立即返回，并新增 256-token 长 padding 回归
测试。该修复不改变生成 token，只移除不必要的 padding 解码。

修复后重跑两条 256-token 错误均成功，认证前缀保持不变。按 `run_id` 取最新结果后的完整
预算曲线为：

| Public N | 完成 | Fallback | Error | 精确解码 | Ambiguity | 完成前缀 | 平均 padding | 净 bit/token |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 160 | 1/4 | 3 | 0 | 1/1 | 0/4 | 158 | 2.00 | 0.800 |
| 192 | 3/4 | 1 | 0 | 3/3 | 0/4 | 181,172,158 | 21.67 | 0.667 |
| 224 | 4/4 | 0 | 0 | 4/4 | 0/4 | 181,172,220,158 | 41.25 | 0.571 |
| 256 | 4/4 | 0 | 0 | 4/4 | 0/4 | 181,172,220,158 | 73.25 | 0.500 |

在当前四条轨迹中，224 是最小全成功公开预算；这只是小样本观察，不是完成前缀的理论上界
或可靠完成率证明。256 不提高本组成功率，只增加 padding 并把净容量从 `0.571` 降至 `0.500`。

## 可复现命令

```powershell
python scripts/audit_fixed_length_rrc.py `
  --samples 100 --seed-start 1000 --rate-floor 1.7 --slack 8
```

原始结果：`outputs/R020_fixed_length_mock_holdout.json`。

Qwen smoke：`outputs/R020_qwen_fixed_length_smoke.jsonl`。
