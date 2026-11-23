import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { streamChat } from './api';

const question = '每年有多少天有薪年假？';
const answer = '全職僱員每年享有 25 天有薪年假。';

vi.mock('./api', () => ({
  fetchDemoEmployee: vi.fn(async () => ({
    id: 'alex-chen', name: 'Alex Chen', role: 'Software Engineer', start_day: 1, company: 'Acme Corp',
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
});

async function openChat() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText(/軟件工程師/);
  return user;
}

async function visitEvalsAndReturn(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('link', { name: '評估結果' }));
  await screen.findByRole('heading', { name: '評估結果' });
  await user.click(screen.getByRole('link', { name: '返回對話' }));
}

describe('chat navigation', () => {
  it('keeps messages, citations and follow-up context after visiting evals', async () => {
    const user = await openChat();
    await user.click(screen.getByRole('button', { name: question }));
    await screen.findByText(answer);

    await visitEvalsAndReturn(user);

    await screen.findByText(answer);
    expect(screen.getByText('僱員手冊')).toBeDefined();
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
    await user.click(screen.getByRole('button', { name: question }));
    await waitFor(() => expect(finishReply).toBeTypeOf('function'));
    await user.click(screen.getByRole('link', { name: '評估結果' }));
    await screen.findByRole('heading', { name: '評估結果' });

    await act(async () => finishReply());
    await user.click(screen.getByRole('link', { name: '返回對話' }));

    await screen.findByText(answer);
    expect(screen.getByRole('textbox', { name: '輸入問題' }).hasAttribute('disabled')).toBe(false);
  });
});
