import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchSourceDocument } from '../api';
import SourceDocument from './SourceDocument';

vi.mock('../api', () => ({ fetchSourceDocument: vi.fn() }));

beforeEach(() => {
  vi.mocked(fetchSourceDocument).mockReset();
  // jsdom does not implement native modal focus and dismissal; browser QA covers them.
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open');
    this.dispatchEvent(new Event('close'));
  };
});

describe('source document reader', () => {
  it('fetches only on click and renders the original markdown in a dialog', async () => {
    vi.mocked(fetchSourceDocument).mockResolvedValue('# 公司文件\n\n原始內容 **25 天**。');
    const user = userEvent.setup();
    render(<SourceDocument filename="employee-handbook.md" />);
    expect(fetchSourceDocument).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: '僱員手冊' }));
    const dialog = screen.getByRole('dialog', { name: '僱員手冊' });
    await within(dialog).findByText('25 天');
    expect(fetchSourceDocument).toHaveBeenCalledWith('employee-handbook.md', expect.any(AbortSignal));
    await user.click(within(dialog).getByRole('button', { name: '關閉' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(screen.getByRole('button', { name: '僱員手冊' })).toBeDefined();
  });

  it('lets the user retry a failed read', async () => {
    vi.mocked(fetchSourceDocument).mockRejectedValueOnce(new Error('找不到這份公司文件。'));
    vi.mocked(fetchSourceDocument).mockResolvedValueOnce('重試成功');
    const user = userEvent.setup();
    render(<SourceDocument filename="it-setup.md" />);
    await user.click(screen.getByRole('button', { name: 'IT 設定及資訊保安指南' }));
    await screen.findByRole('alert');
    await user.click(screen.getByRole('button', { name: '重試' }));
    await screen.findByText('重試成功');
    expect(fetchSourceDocument).toHaveBeenCalledTimes(2);
  });
});
