# Fixed-Length Verified-RRC 设计

## 目的

普通 RRC 和 Verified-RRC 在 payload 完成时立即停止，因此可见文本长度与内部停止时间相关。
逐步 token 条件分布匹配不足以证明这种变长全文与正常生成同分布。固定长度版本规定公开总
长度 `N`，在认证 payload 完成后继续按同一量化目标分布采样到 `N`。

## 输入与输出

输入：

- 固定长度 payload `m in {0,1}^l`；
- 公开总 token 数 `N`；
- HMAC 认证标签长度 `a`，当前允许 `32 <= a <= 256`；
- 共享密钥、prompt、模型、tokenizer 和概率量化配置；
- 失败模式：`raise` 或 `cover`。

输出：

- 成功时恰好 `N` 个 token 和经过认证恢复的 `l` bit payload；
- `raise` 模式在 `N` 内未完成时返回 `IncompleteEncodeError`；
- `cover` 模式在未完成时仍返回恰好 `N` 个 token，但明确标记
  `payload_embedded=False`，不能作为成功通信。

真实嵌入前缀长度 `T` 只进入本地审计结果，不写入 stegotext 或公开协议头。

## 算法

认证帧为

```text
F = m || HMAC(K_auth, domain || l || context || m)[:a].
```

`K_auth` 由主密钥通过独立 domain 派生。RRC 采样、padding 采样和纯 cover 采样使用不同
domain，避免复用同一 PRF 输入。

```text
ALGORITHM FIXED-EMBED(m, K, N)
INPUT: l-bit payload, shared key, public token count, model configuration
OUTPUT: exactly N tokens, success flag

1. Construct authenticated frame F of l+a bits.
2. Run Verified-RRC(F) for at most N tokens.
3. If an authenticated prefix completes at T <= N:
   3.1 Continue sampling tokens T,...,N-1 from the same quantized target R_t.
   3.2 Return N tokens and success=true.
4. If no prefix completes:
   4.1 raise mode: return IncompleteEncodeError with the N-token attempt.
   4.2 cover mode: return the N tokens and success=false.
```

```text
ALGORITHM FIXED-DECODE(S, K, N)
INPUT: exactly N tokens, shared key, public model configuration
OUTPUT: unique authenticated l-bit payload

1. Replay the RRC interval once over all N tokens.
2. At every prefix t, reverse the current midpoint and obtain candidate frame F_t.
3. Validate the HMAC tag of every F_t.
4. If one distinct payload validates, return it.
5. Otherwise reject as missing or ambiguous authentication.
```

## 正确性与安全边界

条件恢复：若 Verified-RRC 在真实前缀 `T` 完成，编码器和解码器确定性重放相同区间，且
HMAC 验证正确，则扫描解码至少会在 `T` 找到原 payload。若出现不同 payload 的伪认证，
解码器拒绝而不猜测。

认证误接受：在理想 `a` bit 标签或标准 PRF/MAC 假设下，扫描至多 `N` 个候选的粗略 union
bound 为 `N/2^a`。当前默认 `a=128`；Qwen smoke 为控制容量成本使用 `a=64`，必须显式报告。

固定长度分布：假设嵌入阶段每个 token 的条件分布为量化目标 `R_t`，完成后的 padding 也
条件采样自同一个 `R_t`，并且总长度固定为 `N`，则由链式法则，全文 token 分布等于使用
同一控制器和量化配置的固定长度 cover。该结论针对理想独立均匀偏移；真实 HMAC 需要 PRF
假设，有限 256-bit 网格仍有已记录的离散误差。

未解决边界：

- Verified-RRC 仍未证明对任意模型必然在 `N` 内完成；
- 只发布成功样本或反复重试会按成功事件条件化，可能重新引入选择偏差；
- `cover` fallback 保持固定输出形状，但不传递消息，调用方必须记录通信失败；
- 固定 token 数不保证句子自然结束；数据相关句号收尾不能直接附加在固定长度之后；
- Decimal 和浮点概率重放仍是条件正确，整数频数版本尚未实现。

## 复杂度

设公开长度为 `N`，第 `t` 步候选数为 `K_t`。

- 编码模型调用：`N` 次；区间/采样时间 `O(sum K_t)`。
- 解码模型调用：`N` 次，不为每个前缀重新运行模型。
- 当前每个前缀执行完整逆重放，算术最坏时间 `O(N^2)`。
- 区间历史和记录空间：`O(N)`。
- 后续可维护增量逆状态或认证检查窗口，降低前缀扫描开销。

## 实验指标

- payload 成功率与 cover fallback 率；
- 公开固定长度、私有嵌入前缀长度和 padding token 数；
- 净 payload bits/public token；
- 包含认证标签的 framed bits/public token；
- 错 key、错 prompt、篡改 token 的误接受率；
- `KL(Q||R)`、Token Ambiguity、固定长度 steganalysis 和语义质量。

可复现 Mock 审计：

```powershell
python scripts/audit_fixed_length_rrc.py --samples 100
```
