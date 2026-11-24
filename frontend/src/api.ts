const API_BASE = import.meta.env.VITE_API_URL || '';

export interface CompanyDocument { filename: string; title: string }
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  failed?: boolean;
}

export async function fetchDocuments(signal?: AbortSignal): Promise<CompanyDocument[]> {
  const response = await fetch(`${API_BASE}/api/documents`, { signal });
  if (!response.ok) throw new Error('暫時未能載入文件清單。');
  return (await response.json()).documents;
}

export async function fetchSourceDocument(filename: string, signal?: AbortSignal): Promise<string> {
  const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(filename)}`, { signal });
  if (!response.ok) throw new Error(response.status === 404 ? '找不到這份公司文件。' : '暫時未能載入文件，請稍後再試。');
  return (await response.json()).content;
}

export async function streamChat(
  message: string,
  history: ChatMessage[],
  onEvent: (event: string, data: unknown) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
    body: JSON.stringify({ message, history: history.filter((item) => !item.failed && item.content)
      .map(({ role, content }) => ({ role, content })) }),
  });
  if (!response.ok || !response.body) throw new Error('暫時未能連接文件助理，請稍後再試。');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completed = false;
  function dispatch(part: string) {
    let event = 'message';
    const data: string[] = [];
    for (const line of part.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    const payload = JSON.parse(data.join('\n'));
    if (event === 'error') throw new Error(payload.message || '暫時未能完成回覆，請稍後再試。');
    if (completed) throw new Error('收到重複的回覆，請稍後再試。');
    if (event === 'done') completed = true;
    onEvent(event, payload);
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n');
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';
      parts.forEach(dispatch);
      if (done) break;
    }
    if (buffer.trim()) dispatch(buffer);
    if (!completed) throw new Error('連線提早結束，未收到完整回覆，請重新傳送問題。');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
