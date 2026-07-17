# R014 认证语义收尾 V1 消融

日期：2026-07-17

## 结论

原生采样尾部在不改变隐写前缀、不降低认证解码率的前提下改善了部分截断文本，但简单的
“末字符为标点”规则会把编号列表 `1.` 误判为完整句末，因此 V1 不能直接作为最终方法。

## 配置与门禁

- Qwen2.5-1.5B-Instruct，FP16，top-p 0.95，temperature 0.8。
- 3 个中文 prompt，128-bit payload，Fixed-16，160-token 嵌入预算。
- Immediate、punctuation-32、fixed-tail-16、fixed-tail-32，共 12 条运行。
- 每个 prompt 的四种策略拥有完全相同的嵌入 token 前缀。
- 12/12 token-ID payload 精确解码；尾部未计入嵌入 bit/token。

## 结果

| Prompt | Embedded tokens | Punctuation tail | Punctuation visible bit/token | Finishing latency | 观察 |
|---:|---:|---:|---:|---:|---|
| 0 | 108 | 9 | 1.094 | 0.525 s | 补全“安全威胁的来源和方式。” |
| 1 | 150 | 6 | 0.821 | 0.416 s | 错停在编号 `1.`，列表尚未展开 |
| 2 | 93 | 19 | 1.143 | 1.242 s | 补全“以此提高软件质量。” |

Punctuation-32 平均增加 11.3 tokens、0.73 秒；平均 visible bit/token 为 1.019，而立即停止
为 1.138。该下降是现实传输成本，不能隐藏在嵌入容量指标中。

## 决策

保留原生尾部和双 token 计数设计，拒绝 V1 标点检测。V2 必须排除行首数字编号、项目符号
和仅含 Markdown 结构的伪句末，然后在同一批 prompt 上重跑 punctuation variant。
