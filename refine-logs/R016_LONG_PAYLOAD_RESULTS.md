# R016 长 Payload 与语义尾部摊薄

日期：2026-07-17

## 研究问题

比较 256/512-bit payload 下 Fixed-16 与 Verified-RRC 的嵌入容量、现实容量和有限预算完成，
检验固定语义尾部成本是否随消息增长被摊薄。

## 256-bit 结果

| Prompt | Fixed embedded tokens | Fixed visible bit/token | RRC embedded tokens | RRC visible bit/token |
|---:|---:|---:|---:|---:|
| 0 | 273 | 0.883 | 244 | 0.928 |
| 1 | 239 | 0.945 | 278 | 0.880 |
| 2 | 273 | 0.880 | 205 | 1.094 |

- Fixed-16：3/3 完成，平均嵌入容量 0.982，平均现实容量 0.903。
- Verified-RRC：3/3 完成，平均嵌入容量 1.073，平均现实容量 0.967。
- RRC 平均少用 19.3 个嵌入 tokens，但 prompt 1 是负样本，RRC 多用 39 tokens。
- 尾部造成的平均容量折损约为 Fixed 8.1%、RRC 9.9%，低于 128-bit 短消息实验。

## 512-bit 结果

| Prompt | Fixed-16 | Fixed mean entropy | Verified-RRC | RRC mean entropy |
|---:|---|---:|---|---:|
| 0 | 800 tokens，完成 84.4% | 0.596 | 415 tokens，完成 | 1.261 |
| 1 | 800 tokens，完成 90.6% | 0.658 | 458 tokens，完成 | 1.070 |
| 2 | 465 tokens，完成 | 1.143 | 800 tokens，未完成 | 0.564 |

成功的 RRC 样本嵌入容量分别为 1.234 和 1.118 bit/token；Fixed-16 唯一成功样本为
1.101 bit/token。三条失败轨迹的文本均出现内容重复或低信息延展。

## 结论

1. 更长 payload 确实摊薄语义尾部成本，成功的 512-bit 样本尾部容量折损约 2%-5%。
2. RRC 在 256-bit 平均优于 Fixed-16，但优势不是逐 prompt 稳定。
3. 512-bit 的首要瓶颈已不是收尾，而是生成轨迹进入低熵重复状态；简单增加 max_tokens
   会继续产生低质量文本且容量增长很慢。
4. RRC 的 incomplete 指标目前是原子式 0/100%，需要新增区间信息进度，避免无法区分“接近
   完成”和“几乎没有编码信息”。
5. 下一方法候选是公开状态驱动的 entropy rescue：连续低熵时提高公开 temperature 或重置
   生成结构。它会改变 cover 分布，必须与原生自适应温度基线比较并报告可检测性风险。
