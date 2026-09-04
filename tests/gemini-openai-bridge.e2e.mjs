import assert from 'node:assert/strict';

const baseUrl = process.env.GEMINI_BRIDGE_URL ?? 'http://127.0.0.1:7872';
const configuredModel = process.env.ORNITH_MODEL;
const apiKey = process.env.GEMINI_API_KEY;

assert(apiKey, 'Set GEMINI_API_KEY before running this live bridge test.');

const request = async (path, options = {}) => fetch(`${baseUrl}${path}`, {
  ...options,
  headers: {
    'content-type': 'application/json',
    'x-goog-api-key': apiKey,
    ...options.headers,
  },
});

const models = await request('/v1beta/models');
assert.equal(models.status, 200);
const modelList = (await models.json()).models ?? [];
const model = configuredModel ?? modelList[0]?.baseModelId;
assert(model, 'Gemini bridge returned no models');
assert(modelList.some((entry) => entry.baseModelId === model));

const countTokens = await request(`/v1beta/models/${encodeURIComponent(model)}:countTokens`, {
  method: 'POST',
  body: JSON.stringify({ contents: [{ role: 'user', parts: [{ text: 'one two three four' }] }] }),
});
assert.equal(countTokens.status, 200);
assert((await countTokens.json()).totalTokens > 0);

const expected = 'GEMINI_BRIDGE_TEST_OK';
const generate = await request(`/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
  method: 'POST',
  body: JSON.stringify({
    contents: [{ role: 'user', parts: [{ text: `Return exactly ${expected}` }] }],
    generationConfig: { maxOutputTokens: 32, thinkingConfig: { thinkingBudget: 0 } },
  }),
});
assert.equal(generate.status, 200);
assert.equal((await generate.json()).candidates[0].content.parts[0].text, expected);

const streamExpected = 'GEMINI_BRIDGE_STREAM_TEST_OK';
const stream = await request(`/v1beta/models/${encodeURIComponent(model)}:streamGenerateContent?alt=sse`, {
  method: 'POST',
  body: JSON.stringify({
    contents: [{ role: 'user', parts: [{ text: `Return exactly ${streamExpected}` }] }],
    generationConfig: { maxOutputTokens: 32, thinkingConfig: { thinkingBudget: 0 } },
  }),
});
assert.equal(stream.status, 200);
const streamText = (await stream.text())
  .split('\n\n')
  .filter((event) => event.startsWith('data: '))
  .flatMap((event) => JSON.parse(event.slice(6)).candidates ?? [])
  .flatMap((candidate) => candidate.content?.parts ?? [])
  .map((part) => part.text ?? '')
  .join('');
assert.equal(streamText, streamExpected);

const unauthorized = await fetch(`${baseUrl}/v1beta/models`, { headers: { 'x-goog-api-key': 'invalid' } });
assert.equal(unauthorized.status, 401);

console.log('Gemini bridge smoke test passed.');
