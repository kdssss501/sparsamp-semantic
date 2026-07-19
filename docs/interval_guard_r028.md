# R028：稀疏区间格点 Guard

## 目标

SparSamp 每一步通过两个取整端点更新剩余消息区间：

\[
a=\lceil (L-r)n\rceil,\qquad b=\lceil(U-r)n\rceil.
\]

R028 不再尝试让全部概率完全相等，而是判断当前端点是否离整数边界足够远。若不能证明安全，编码端主动放弃整个固定窗口；解码端无需同步 guard，窗口认证会把它转换成擦除。

## 条件保证

定义有理数到最近整数的距离

\[
d(x)=\min(x-\lfloor x\rfloor,\lceil x\rceil-x)\in[0,1/2].
\]

若编码端与解码端候选支持和顺序相同，且上下 CDF 端点误差均不超过 `epsilon`，则当

\[
\min(d((L-r)n),d((U-r)n)) > n\epsilon
\]

时，两个 `ceil` 结果保持不变。由于左侧最大为 `1/2`，初始 `n=2^b` 时存在安全点的必要条件为

\[
\epsilon < 2^{-(b+1)}.
\]

该条件不是充分的消息恢复保证：实际采样端点还可能靠近整数，候选支持也可能发生 churn。

## 算法

```text
ENCODE WINDOW j
  reset sparse interval (k, n)
  for each token position in public window:
    compute candidate interval [L, U) and PRF value r
    margin = min(distance_to_integer((L-r)n),
                 distance_to_integer((U-r)n))
    required = n * calibrated_cdf_uncertainty_bound
    if margin <= required:
       abort this window and use native model sampling for the remainder
    else:
       perform the normal SparSamp interval update

DECODE
  run the ordinary fixed-window decoder
  an aborted or drifted window fails authentication and becomes an erasure
```

## 复杂度与边界

Guard 每步增加常数次 Fraction 运算，渐进复杂度不变。保证依赖一个外部校准的 CDF 误差上界；用经验最大值只能描述已测轨迹，不能自动推广到新模型、prompt 或硬件。若使用全局 worst-case bound，guard 可能全部 abstain，得到可靠但零容量的系统。
