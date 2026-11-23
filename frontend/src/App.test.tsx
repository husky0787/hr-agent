import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { resetOnboarding, streamChat } from './api';

const question = '每年有多少天有薪年假？';
const answer = '全職僱員每年享有 25 天有薪年假。';

vi.mock('./api', () => ({
  fetchDemoEmployee: vi.fn(async () => ({
    id: 'alex-chen', name: 'Alex Chen', role: 'Software Engineer', start_day: 1,
    company: 'Harbour Finch Labs', company_zh: '港雀科技', department: 'Engineering',
    manager: 'Maya Wong', buddy: 'Jamie Lau', is_demo: true,
  })),
  fetchOnboardingStatus: vi.fn(async () => ({
    employee_id: 'alex-chen', total_tasks: 0, completed_tasks: 0, completion_percent: 0, tasks: [],
  })),
  fetchEvalResults: vi.fn(async () => ({
    results_dir: 'evals/results',
    golden: { available: false, report: null, path: '' },
    deepeval: { available: false, report: null, path: '' },
  })),
  fetchCheckins: vi.fn(async () => []),
  completeTask: vi.fn(async () => {}),
  resetOnboarding: vi.fn(async () => {}),
  streamChat: vi.fn(async (_message, _employee, _history, onEvent) => {
    onEvent('citations', ['employee-handbook.md']);
    onEvent('token', '全職僱員每年享有 25 天有薪年假。');
    onEvent('done', '全職僱員每年享有 25 天有薪年假。');
  }),
}));

beforeEach(() => {
  window.history.replaceState({}, '', '/');
  vi.clearAllMocks();
  vi.mocked(resetOnboarding).mockResolvedValue(undefined);
});

async function openChat() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText('HR Agent');
  return user;
}

async function visitEvalsAndReturn(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('link', { name: '評估結果' }));
  await screen.findByRole('heading', { name: '評估結果' });
  await user.click(screen.getByRole('link', { name: '返回對話' }));
}

async function askAnnualLeave(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole('textbox', { name: '輸入問題' }), question);
  await user.click(screen.getByRole('button', { name: '傳送訊息' }));
}

describe('chat navigation', () => {
  it('keeps messages, citations and follow-up context after visiting evals', async () => {
    const user = await openChat();
    await askAnnualLeave(user);
    await screen.findByText(answer);

    await visitEvalsAndReturn(user);

    await screen.findByText(answer);
    expect(screen.getByRole('button', { name: '僱員手冊' })).toBeDefined();
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '如何申請？');
    await user.click(screen.getByRole('button', { name: '傳送訊息' }));
    expect(vi.mocked(streamChat).mock.calls.at(-1)?.[2]).toEqual(expect.arrayContaining([
      { role: 'user', content: question },
      expect.objectContaining({ role: 'assistant', content: answer }),
    ]));
  });

  it('keeps an unsent draft after visiting evals', async () => {
    const user = await openChat();
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '我想查詢強積金');

    await visitEvalsAndReturn(user);

    expect((screen.getByRole('textbox', { name: '輸入問題' }) as HTMLTextAreaElement).value)
      .toBe('我想查詢強積金');
  });

  it('finishes an in-flight reply while the user views evals', async () => {
    let finishReply!: () => void;
    vi.mocked(streamChat).mockImplementationOnce((_message, _employee, _history, onEvent) => (
      new Promise<void>((resolve) => {
        finishReply = () => {
          onEvent('token', answer);
          onEvent('done', answer);
          resolve();
        };
      })
    ));
    const user = await openChat();
    await askAnnualLeave(user);
    await waitFor(() => expect(finishReply).toBeTypeOf('function'));
    await user.click(screen.getByRole('link', { name: '評估結果' }));
    await screen.findByRole('heading', { name: '評估結果' });

    await act(async () => finishReply());
    await user.click(screen.getByRole('link', { name: '返回對話' }));

    await screen.findByText(answer);
    expect(screen.getByRole('textbox', { name: '輸入問題' }).hasAttribute('disabled')).toBe(false);
  });
});

describe('fictional company demo', () => {
  it('shows each source and tool badge once after repeated searches', async () => {
    vi.mocked(streamChat).mockImplementationOnce(async (_message, _employee, _history, onEvent) => {
      onEvent('citations', ['employee-handbook.md', 'employee-handbook.md']);
      onEvent('tool_calls', [{ name: 'search_handbook_tool' }, { name: 'search_handbook_tool' }]);
      onEvent('token', answer);
      onEvent('done', answer);
    });
    const user = await openChat();
    await askAnnualLeave(user);
    await screen.findByText(answer);
    expect(screen.getAllByRole('button', { name: '僱員手冊' })).toHaveLength(1);
    expect(screen.getAllByText('查閱公司文件')).toHaveLength(1);
  });

  it('offers guided scenarios and keeps the disclosure on admin pages', async () => {
    const user = await openChat();
    await screen.findByRole('heading', { name: 'Harbour Finch Labs｜港雀科技' });
    for (const name of ['我是今天入職的工程師', '查詢公司福利', '建立第一星期待辦']) {
      expect(screen.getByRole('button', { name })).toBeDefined();
    }
    await user.click(screen.getByRole('button', { name: '查詢公司福利' }));
    await screen.findByText(answer);
    expect(vi.mocked(streamChat).mock.calls.at(-1)?.[0]).toContain('健康津貼');
    await user.click(screen.getByRole('link', { name: '評估結果' }));
    await screen.findByRole('heading', { name: '評估結果' });
    expect(screen.getByText('示範環境：公司、員工及內部政策均為虛構')).toBeDefined();
  });

  it('resets the demo employee and clears chat, citations and draft after success', async () => {
    const user = await openChat();
    await askAnnualLeave(user);
    await screen.findByText(answer);
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '未傳送草稿');
    await user.click(screen.getByRole('button', { name: '重設示範' }));
    await screen.findByText('示範已重設，可重新開始。');
    expect(resetOnboarding).toHaveBeenCalledWith('alex-chen');
    expect(screen.queryByText(answer)).toBeNull();
    expect(screen.queryByRole('button', { name: '僱員手冊' })).toBeNull();
    expect((screen.getByRole('textbox', { name: '輸入問題' }) as HTMLTextAreaElement).value).toBe('');
    expect(screen.getByRole('button', { name: '建立第一星期待辦' })).toBeDefined();
  });

  it('preserves the current chat when reset fails', async () => {
    vi.mocked(resetOnboarding).mockRejectedValueOnce(new Error('未能重設示範，請稍後再試。'));
    const user = await openChat();
    await askAnnualLeave(user);
    await screen.findByText(answer);
    await user.type(screen.getByRole('textbox', { name: '輸入問題' }), '保留草稿');
    await user.click(screen.getByRole('button', { name: '重設示範' }));
    await screen.findByText('未能重設示範，請稍後再試。');
    expect(screen.getByText(answer)).toBeDefined();
    expect((screen.getByRole('textbox', { name: '輸入問題' }) as HTMLTextAreaElement).value).toBe('保留草稿');
  });

  it('disables reset until an active reply completes', async () => {
    let finishReply!: () => void;
    vi.mocked(streamChat).mockImplementationOnce((_message, _employee, _history, onEvent) => (
      new Promise<void>((resolve) => {
        finishReply = () => { onEvent('done', answer); resolve(); };
      })
    ));
    const user = await openChat();
    await askAnnualLeave(user);
    await waitFor(() => expect(finishReply).toBeTypeOf('function'));
    const reset = screen.getByRole('button', { name: '重設示範' });
    expect(reset.hasAttribute('disabled')).toBe(true);
    await user.click(reset);
    expect(resetOnboarding).not.toHaveBeenCalled();
    await act(async () => finishReply());
    await waitFor(() => expect(reset.hasAttribute('disabled')).toBe(false));
  });
});
