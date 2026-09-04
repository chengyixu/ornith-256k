import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';

const host = process.env.GEMINI_BRIDGE_HOST ?? '127.0.0.1';
const port = Number(process.env.GEMINI_BRIDGE_PORT ?? '7872');
const upstreamBaseUrl = (process.env.ORNITH_UPSTREAM_URL ?? 'http://127.0.0.1:7871/v1').replace(/\/+$/, '');
const apiKeyFile = process.env.ORNITH_API_KEY_FILE ?? new URL('./llama-server-api-keys.txt', import.meta.url);
const functionCallIds = new Map();
let nextFunctionCallId = 1;

function readApiKeys() {
  return new Set(
    readFileSync(apiKeyFile, 'utf8')
      .split(/\r?\n/)
      .flatMap((line) => {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) return [];
        const assignment = trimmed.match(/^[^:=]+\s*[:=]\s*(.+)$/);
        return [trimmed, assignment?.[1]?.trim()].filter(Boolean);
      }),
  );
}

function requestApiKey(request) {
  const authorization = request.headers.authorization;
  if (authorization?.toLowerCase().startsWith('bearer ')) return authorization.slice(7).trim();
  return request.headers['x-goog-api-key']?.trim() ?? request.headers['x-api-key']?.trim() ?? '';
}

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(payload));
}

function sendError(response, statusCode, message, status = 'UNKNOWN') {
  sendJson(response, statusCode, { error: { code: statusCode, message, status } });
}

function modelIdFromPath(pathname) {
  const encoded = pathname.match(/\/models\/(.+?)(?::(?:generateContent|streamGenerateContent|countTokens))?$/)?.[1];
  return encoded ? decodeURIComponent(encoded).replace(/^models\//, '') : '';
}

function normalizeSchema(value) {
  if (Array.isArray(value)) return value.map(normalizeSchema);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, entry]) => [
      key,
      key === 'type' && typeof entry === 'string' ? entry.toLowerCase() : normalizeSchema(entry),
    ]),
  );
}

function textFromParts(parts = []) {
  return parts
    .flatMap((part) => {
      if (typeof part.text === 'string') return [part.text];
      if (part.inlineData?.data) return [`[inline data: ${part.inlineData.mimeType ?? 'application/octet-stream'}]`];
      return [];
    })
    .join('');
}

function functionCallId(name, args, requestedId) {
  if (requestedId) return requestedId;
  const signature = `${name}:${JSON.stringify(args ?? {})}`;
  if (!functionCallIds.has(signature)) functionCallIds.set(signature, `call_${nextFunctionCallId++}`);
  return functionCallIds.get(signature);
}

function toOpenAiRequest(payload, model, stream) {
  const messages = [];
  const systemInstruction = textFromParts(payload.systemInstruction?.parts);
  if (systemInstruction) messages.push({ role: 'system', content: systemInstruction });

  for (const content of payload.contents ?? []) {
    const role = content.role === 'model' ? 'assistant' : 'user';
    const text = textFromParts(content.parts);
    const functionCalls = content.parts?.filter((part) => part.functionCall) ?? [];
    const functionResponses = content.parts?.filter((part) => part.functionResponse) ?? [];

    if (functionCalls.length) {
      messages.push({
        role: 'assistant',
        content: text || null,
        tool_calls: functionCalls.map((part) => {
          const call = part.functionCall;
          const id = functionCallId(call.name, call.args, call.id);
          return {
            id,
            type: 'function',
            function: { name: call.name, arguments: JSON.stringify(call.args ?? {}) },
          };
        }),
      });
    } else if (text) {
      messages.push({ role, content: text });
    }

    for (const part of functionResponses) {
      const result = part.functionResponse;
      const id = functionCallId(result.name, undefined, result.id);
      messages.push({ role: 'tool', tool_call_id: id, content: JSON.stringify(result.response ?? {}) });
    }
  }

  const request = {
    model,
    messages,
    stream,
    max_tokens: payload.generationConfig?.maxOutputTokens,
    temperature: payload.generationConfig?.temperature,
    top_p: payload.generationConfig?.topP,
    stop: payload.generationConfig?.stopSequences,
  };

  // Gemini callers use a zero thinking budget to request a direct answer.
  // llama.cpp exposes the equivalent through the Qwen chat-template kwarg.
  if (payload.generationConfig?.thinkingConfig?.thinkingBudget === 0) {
    request.chat_template_kwargs = { enable_thinking: false };
  }

  const declarations = payload.tools?.flatMap((tool) => tool.functionDeclarations ?? []) ?? [];
  if (declarations.length) {
    request.tools = declarations.map((declaration) => ({
      type: 'function',
      function: {
        name: declaration.name,
        description: declaration.description,
        parameters: normalizeSchema(declaration.parameters ?? { type: 'object', properties: {} }),
      },
    }));
  }

  return Object.fromEntries(Object.entries(request).filter(([, value]) => value !== undefined));
}

function finishReason(reason) {
  if (reason === 'length') return 'MAX_TOKENS';
  if (reason === 'tool_calls') return 'STOP';
  return 'STOP';
}

function toGeminiResponse(upstream, model) {
  const choice = upstream.choices?.[0] ?? {};
  const message = choice.message ?? {};
  const parts = [];
  if (message.content) parts.push({ text: message.content });
  for (const call of message.tool_calls ?? []) {
    let args = {};
    try {
      args = JSON.parse(call.function?.arguments || '{}');
    } catch {
      args = { raw: call.function?.arguments ?? '' };
    }
    const id = functionCallId(call.function?.name, args, call.id);
    parts.push({ functionCall: { id, name: call.function?.name, args } });
  }

  return {
    candidates: [{
      content: { role: 'model', parts: parts.length ? parts : [{ text: '' }] },
      finishReason: finishReason(choice.finish_reason),
    }],
    usageMetadata: {
      promptTokenCount: upstream.usage?.prompt_tokens ?? 0,
      candidatesTokenCount: upstream.usage?.completion_tokens ?? 0,
      totalTokenCount: upstream.usage?.total_tokens ?? 0,
    },
    modelVersion: model,
  };
}

async function upstreamRequest(apiKey, payload) {
  const response = await fetch(`${upstreamBaseUrl}/chat/completions`, {
    method: 'POST',
    headers: { authorization: `Bearer ${apiKey}`, 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Upstream ${response.status}: ${error.slice(0, 500)}`);
  }
  return response;
}

function modelDescriptor(model) {
  return {
    name: `models/${model}`,
    baseModelId: model,
    displayName: model,
    supportedGenerationMethods: ['generateContent', 'streamGenerateContent', 'countTokens'],
    inputTokenLimit: 262144,
    outputTokenLimit: 16384,
  };
}

async function handleStream(response, apiKey, payload, model) {
  const upstream = await upstreamRequest(apiKey, toOpenAiRequest(payload, model, true));
  response.writeHead(200, {
    'content-type': 'text/event-stream; charset=utf-8',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
  });
  const decoder = new TextDecoder();
  let buffer = '';
  const calls = new Map();

  const emit = (chunk) => response.write(`data: ${JSON.stringify(chunk)}\n\n`);
  const processEvent = (event) => {
    const data = event.trim().replace(/^data:\s*/, '');
    if (!data || data === '[DONE]') return;
    const parsed = JSON.parse(data);
    const choice = parsed.choices?.[0];
    if (!choice) return;
    const delta = choice.delta ?? {};
    if (delta.content) emit({ candidates: [{ content: { role: 'model', parts: [{ text: delta.content }] } }], modelVersion: model });
    for (const call of delta.tool_calls ?? []) {
      const current = calls.get(call.index) ?? { id: call.id, name: '', arguments: '' };
      current.id ||= call.id;
      current.name += call.function?.name ?? '';
      current.arguments += call.function?.arguments ?? '';
      calls.set(call.index, current);
    }
    if (choice.finish_reason) {
      for (const call of calls.values()) {
        let args = {};
        try {
          args = JSON.parse(call.arguments || '{}');
        } catch {
          args = { raw: call.arguments };
        }
        emit({ candidates: [{ content: { role: 'model', parts: [{ functionCall: { id: functionCallId(call.name, args, call.id), name: call.name, args } }] } }], modelVersion: model });
      }
      emit({ candidates: [{ content: { role: 'model', parts: [{ text: '' }] }, finishReason: finishReason(choice.finish_reason) }], modelVersion: model });
    }
  };

  for await (const chunk of upstream.body) {
    buffer += decoder.decode(chunk, { stream: true });
    let boundary;
    while ((boundary = buffer.indexOf('\n\n')) >= 0) {
      processEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
    }
  }
  response.end();
}

async function parseBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host}`);
    const apiKey = requestApiKey(request);
    if (!readApiKeys().has(apiKey)) return sendError(response, 401, 'Invalid API key', 'UNAUTHENTICATED');

    if (request.method === 'GET' && /\/models$/.test(url.pathname)) {
      const modelsResponse = await fetch(`${upstreamBaseUrl}/models`, { headers: { authorization: `Bearer ${apiKey}` } });
      if (!modelsResponse.ok) throw new Error(`Upstream model discovery returned ${modelsResponse.status}`);
      const data = await modelsResponse.json();
      return sendJson(response, 200, { models: (data.data ?? []).map((item) => modelDescriptor(item.id)) });
    }

    if (request.method === 'GET' && /\/models\/.+$/.test(url.pathname)) {
      return sendJson(response, 200, modelDescriptor(modelIdFromPath(url.pathname)));
    }

    const model = modelIdFromPath(url.pathname);
    if (!model) return sendError(response, 404, 'Not found', 'NOT_FOUND');
    const payload = await parseBody(request);

    if (url.pathname.endsWith(':countTokens')) {
      const text = [textFromParts(payload.systemInstruction?.parts), ...(payload.contents ?? []).map((content) => textFromParts(content.parts))].join('');
      return sendJson(response, 200, { totalTokens: Math.max(1, Math.ceil(text.length / 4)) });
    }

    if (url.pathname.endsWith(':generateContent')) {
      const upstream = await upstreamRequest(apiKey, toOpenAiRequest(payload, model, false));
      return sendJson(response, 200, toGeminiResponse(await upstream.json(), model));
    }

    if (url.pathname.endsWith(':streamGenerateContent')) {
      await handleStream(response, apiKey, payload, model);
      return;
    }

    return sendError(response, 404, 'Not found', 'NOT_FOUND');
  } catch (error) {
    sendError(response, 500, error instanceof Error ? error.message : String(error), 'INTERNAL');
  }
});

server.listen(port, host, () => console.log(`Gemini bridge listening on http://${host}:${port}`));
