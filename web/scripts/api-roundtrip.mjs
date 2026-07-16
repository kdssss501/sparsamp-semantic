const baseUrl = process.env.SPARSAMP_WEB_URL ?? 'http://127.0.0.1:8000'
const secretKey = process.env.SPARSAMP_SMOKE_KEY
if (!secretKey || new TextEncoder().encode(secretKey).length < 16) {
  throw new Error('set SPARSAMP_SMOKE_KEY to at least 16 bytes')
}
const prompt = '请用自然、清晰的中文解释为什么可复现实验对于人工智能安全研究很重要。'
const sampling = {
  model: 'models/qwen2.5-1.5b-instruct',
  revision: null,
  device: 'cuda',
  dtype: 'float16',
  load_in_4bit: false,
  top_p: 0.95,
  top_k: null,
  temperature: 0.8,
  seed: 42,
}
const codec = {
  block_size: 32,
  max_tokens: 2048,
  min_source_mass: 0,
  probability_quantum: '1e-15',
  repetitions: 1,
}

async function postOperation(body) {
  const response = await fetch(`${baseUrl}/api/v1/operations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  if (!response.ok) throw new Error(JSON.stringify(payload))
  return payload.data
}

async function waitForOperation(id) {
  while (true) {
    const response = await fetch(`${baseUrl}/api/v1/operations/${id}`)
    const payload = await response.json()
    if (!response.ok) throw new Error(JSON.stringify(payload))
    if (['succeeded', 'failed'].includes(payload.data.status)) return payload.data
    await new Promise((resolve) => setTimeout(resolve, 750))
  }
}

const encode = await postOperation({
  kind: 'encode',
  prompt,
  message: 'A-17',
  secret_key: secretKey,
  sampling,
  codec,
})
const encoded = await waitForOperation(encode.id)
if (encoded.status !== 'succeeded') throw new Error(encoded.error.message)

const decode = await postOperation({
  kind: 'decode',
  artifact_id: encoded.result.artifact_id,
  secret_key: secretKey,
})
const decoded = await waitForOperation(decode.id)
if (decoded.status !== 'succeeded') throw new Error(decoded.error.message)

console.log(
  JSON.stringify(
    {
      artifact: encoded.result.artifact_id,
      tokens: encoded.result.metrics.token_count,
      bitsPerToken: encoded.result.metrics.bits_per_token,
      tokenAmbiguity: encoded.result.token_ambiguity,
      decodeSource: decoded.result.source,
      decoded: decoded.result.message,
    },
    null,
    2,
  ),
)
