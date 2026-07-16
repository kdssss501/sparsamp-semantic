# SparSamp 本地研究 API

## 边界

- Base URL：`http://127.0.0.1:8000/api/v1`
- 默认只监听 loopback，不提供公网认证方案。
- GPU 操作串行执行，避免 6GB 显存上的并发模型副本。
- `secret_key` 只用于当前 operation，不写入日志、状态响应或实验文件。
- API 结果用于授权科研、可靠性评估和可复现实验。

## 资源

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/system/status` | CUDA、显卡、模型文件和任务状态 |
| `POST` | `/operations` | 创建 `encode`、`decode` 或 `native` 长任务 |
| `GET` | `/operations/{id}` | 轮询任务状态与结果 |
| `GET` | `/operations?limit=20` | 最近任务 |
| `GET` | `/artifacts?limit=20&cursor=0` | 分页读取脱敏实验记录 |
| `GET` | `/artifacts/{id}` | 读取单个实验 artifact |
| `GET` | `/grid-results?limit=100&cursor=0` | 分页读取 JSONL 消融结果 |

`POST /operations` 返回 `202 Accepted`，`Location` 指向新建的任务资源。

## 创建编码任务

```json
{
  "kind": "encode",
  "prompt": "请解释可复现研究的价值。",
  "message": "实验编号 A-17",
  "secret_key": "至少十六字节的共享密钥",
  "sampling": {
    "model": "models/qwen2.5-1.5b-instruct",
    "device": "cuda",
    "dtype": "float16",
    "top_p": 0.95,
    "temperature": 0.8,
    "seed": 42
  },
  "codec": {
    "block_size": 32,
    "max_tokens": 2048,
    "repetitions": 1
  }
}
```

## 错误模型

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数不合法",
    "details": {},
    "request_id": "e10d..."
  }
}
```

后台模型异常不会让轮询接口返回 500；任务会进入 `failed` 状态并携带稳定错误码
`OPERATION_FAILED`。所有响应包含 `X-Request-ID` 和 `Cache-Control: no-store`。

解码有两条明确路径：传入 `artifact_id` 时使用保存的 token IDs 与原始配置，适合
可靠复现；传入 `prompt`、`cover_text`、`sampling` 和 `codec` 时从公开文本重新分词，
用于测量真实传输后的 Token Ambiguity。两者不会静默互相降级。
