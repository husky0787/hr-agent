import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import ChatMarkdown from './ChatMarkdown';

it('shows readable legacy citations while preserving URLs and code', () => {
  render(<ChatMarkdown content={'25 天 [employee-handbook.md]；[benefits-guide.md](https://example.com/benefits-guide.md)。`it-setup.md`'} />);
  expect(screen.getByText(/25 天 \[僱員手冊\]/)).toBeDefined();
  expect(screen.getByRole('link', { name: '福利及開支報銷指南' }).getAttribute('href')).toBe('https://example.com/benefits-guide.md');
  expect(screen.getByText('it-setup.md').tagName).toBe('CODE');
});
