# 认证语义收尾设计

## 目的

SparSamp 在最后一个 payload block 完成时立即停止，容易截断句子、列表项或 Markdown 标记。
语义收尾在嵌入结束后切换到模型原生采样，直到公开停止规则成立。尾部不承载秘密，因此不能
计入嵌入容量，也不改变已经生成的隐写前缀。

## 模式

- `none`：立即停止，作为容量基线。
- `punctuation`：至少生成 `min_tokens`，在句号、问号或感叹号处停止，最多
  `max_tokens`。
- `fixed`：固定生成 `max_tokens`，用于判断改进来自句末规则还是仅来自文本变长。

每个尾部 token 必须来自 provider 的 `native_token_id`，不能使用秘密消息或 PRF 选择。
句末判断排除独立行上的数字列表标记，避免把 `1.` 误判为已经完成的句子。

## 解码与指标

认证 payload 帧携带 magic、密文长度和 ChaCha20-Poly1305 tag。SparSamp 对完整可见文本
解码时，尾部可能产生额外随机 block，但 `PayloadCodec.open()` 只读取帧声明的长度并忽略
尾随 bits。Artifact 同时保存完整 `token_ids` 和 `embedded_token_count`，artifact 解码只重放
嵌入前缀，避免无意义计算。

必须分别报告：

- `embedded_token_count` 与 `bits_per_token`：算法嵌入能力；
- `visible_token_count`、`tail_token_count` 与 `visible_bits_per_token`：现实传输成本；
- `embedding_elapsed_seconds` 与 `finishing_elapsed_seconds`：速度分解；
- 完整文本的 Token Ambiguity：公开文本能否重新分词；
- 句末命中率和盲评完整性：语义收益。

该机制不修复 Token Ambiguity，也不能把原生尾部描述为零成本。对于 RRC，公开文本无旁路
解码还需要认证前缀搜索；当前 artifact 可通过公开的 `embedded_token_count` 精确解码。
