import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamChat } from './api';

afterEach(() => vi.unstubAllGlobals());

function response(text: string, split = false) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({ start(controller) {
    if (split) for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
    else controller.enqueue(bytes);
    controller.close();
  } }));
}

describe('SSE completion contract', () => {
  it('decodes split UTF-8 and CRLF frames and sends no employee identifier', async () => {
    const fetchMock = vi.fn(async () => response('event: token\r\ndata: "年假"\r\n\r\nevent: done\r\ndata: "年假"\r\n\r\n', true));
    vi.stubGlobal('fetch', fetchMock);
    const events: string[] = [];
    await streamChat('問題', [], (event) => events.push(event));
    expect(events).toEqual(['token', 'done']);
    const body = JSON.parse((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body as string);
    expect(body).toEqual({ message: '問題', history: [] });
  });

  it('rejects server error events and interrupted streams', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response('event: error\ndata: {"message":"搜尋失敗"}\n\n')));
    await expect(streamChat('問題', [], () => {})).rejects.toThrow('搜尋失敗');
    vi.stubGlobal('fetch', vi.fn(async () => response('event: token\ndata: "未完成"\n\n')));
    await expect(streamChat('問題', [], () => {})).rejects.toThrow('連線提早結束');
  });
});
