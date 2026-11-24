import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { fetchDocuments, fetchSourceDocument, streamChat } from './api';

vi.mock('./api', () => ({ fetchDocuments: vi.fn(), fetchSourceDocument: vi.fn(), streamChat: vi.fn() }));
const answer = '全職僱員每年享有 25 天有薪年假。';

beforeEach(() => {
  window.history.replaceState({}, '', '/');
  vi.clearAllMocks();
  vi.mocked(fetchDocuments).mockReset();
  vi.mocked(fetchSourceDocument).mockReset();
  vi.mocked(streamChat).mockReset();
  vi.mocked(fetchDocuments).mockResolvedValue([{ filename: 'employee-handbook.md', title: '僱員手冊' }]);
  vi.mocked(fetchSourceDocument).mockResolvedValue('# 僱員手冊\n\n完整政策文件。');
  vi.mocked(streamChat).mockImplementation(async (_message, _history, onEvent) => {
    onEvent('citations', ['employee-handbook.md', 'employee-handbook.md']);
    onEvent('token', answer);
    onEvent('done', answer);
  });
});

async function openChat() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole('button', { name: '僱員手冊' });
  return user;
}

async function ask(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '年假有幾多日？');
  await user.click(screen.getByRole('button', { name: '傳送訊息' }));
}

describe('chat and document demo', () => {
  it('provides documents directly and has no employee or workflow controls', async () => {
    await openChat();
    expect(screen.queryByText('Alex Chen')).toBeNull();
    for (const text of ['入職進度', '跟進會面', '評估結果', '建立第一星期待辦', '重設示範']) {
      expect(screen.queryByText(text)).toBeNull();
    }
    expect(fetchSourceDocument).not.toHaveBeenCalled();
    expect(fetchDocuments).toHaveBeenCalledTimes(1);
  });

  it('preserves an unsent draft while reading and closing a document', async () => {
    const user = await openChat();
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '我想查詢強積金');
    await user.click(screen.getByRole('button', { name: '僱員手冊' }));
    const dialog = screen.getByRole('dialog');
    await within(dialog).findByText('完整政策文件。');
    await user.click(within(dialog).getByRole('button', { name: '關閉' }));
    expect((screen.getByRole('textbox', { name: '輸入問題' }) as HTMLTextAreaElement).value).toBe('我想查詢強積金');
  });

  it('keeps follow-up context and deduplicates citation buttons', async () => {
    const user = await openChat();
    await ask(user);
    await screen.findByText(answer);
    // One library button and one citation button.
    expect(screen.getAllByRole('button', { name: '僱員手冊' })).toHaveLength(2);
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '如何申請？');
    await user.click(screen.getByRole('button', { name: '傳送訊息' }));
    expect(vi.mocked(streamChat).mock.calls.at(-1)?.[1]).toEqual(expect.arrayContaining([
      { role: 'user', content: '年假有幾多日？' },
      expect.objectContaining({ role: 'assistant', content: answer }),
    ]));
  });

  it('finishes a reply while a document is open and disables clear until done', async () => {
    let finish!: () => void;
    vi.mocked(streamChat).mockImplementationOnce((_message, _history, onEvent) => new Promise<void>((resolve) => {
      finish = () => { onEvent('done', answer); resolve(); };
    }));
    const user = await openChat();
    await ask(user);
    expect(screen.getByRole('button', { name: '清除對話' }).hasAttribute('disabled')).toBe(true);
    await user.click(screen.getByRole('button', { name: '僱員手冊' }));
    await act(async () => finish());
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: '關閉' }));
    await screen.findByText(answer);
    expect(screen.getByRole('button', { name: '清除對話' }).hasAttribute('disabled')).toBe(false);
  });

  it('clears messages and draft locally without reloading documents', async () => {
    const user = await openChat();
    await ask(user);
    await screen.findByText(answer);
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '草稿');
    await user.click(screen.getByRole('button', { name: '清除對話' }));
    expect(screen.queryByText(answer)).toBeNull();
    expect((screen.getByRole('textbox', { name: '輸入問題' }) as HTMLTextAreaElement).value).toBe('');
    expect(fetchDocuments).toHaveBeenCalledTimes(1);
  });

  it('recovers from a failed reply without displaying an empty assistant answer', async () => {
    vi.mocked(streamChat).mockRejectedValueOnce(new Error('文件搜尋暫時不可用。'));
    const user = await openChat();
    await ask(user);
    await screen.findByRole('alert');
    expect(screen.queryByText('正在搜尋文件…')).toBeNull();
    expect((screen.getByRole('textbox', { name: '輸入問題' }) as HTMLTextAreaElement).value).toBe('年假有幾多日？');
    expect(screen.getByRole('button', { name: '傳送訊息' }).hasAttribute('disabled')).toBe(false);
    await user.click(screen.getByRole('button', { name: '傳送訊息' }));
    await screen.findByText(answer);
    expect(screen.getAllByText('年假有幾多日？')).toHaveLength(1);
  });

  it('does not gate chat on document list availability', async () => {
    vi.mocked(fetchDocuments).mockRejectedValueOnce(new Error('文件清單暫時不可用。'));
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole('alert');
    await ask(user);
    await screen.findByText(answer);
  });

  it('does not expose retired admin pages', async () => {
    window.history.replaceState({}, '', '/admin/evals');
    render(<App />);
    await screen.findByText('找不到此頁面。');
    expect(fetchDocuments).not.toHaveBeenCalled();
  });

  it('aborts the active request when stopped', async () => {
    vi.mocked(streamChat).mockImplementationOnce((_message, _history, _onEvent, signal) => new Promise<void>((_resolve, reject) => {
      signal?.addEventListener('abort', () => reject(new DOMException('Stopped', 'AbortError')));
    }));
    const user = await openChat();
    await ask(user);
    await user.click(screen.getByRole('button', { name: '停止回覆' }));
    await waitFor(() => expect(screen.getByRole('alert').textContent).toBe('已停止回覆。'));
    expect(vi.mocked(streamChat).mock.calls[0][3]?.aborted).toBe(true);
  });
});
