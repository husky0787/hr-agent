import type { AgentEvent } from './api';

export const TOOL_LABELS: Record<string, string> = {
  search_handbook_tool: '查閱公司文件',
  create_onboarding_task_tool: '建立入職事項',
  list_onboarding_tasks_tool: '查看入職事項',
  schedule_checkin_tool: '安排跟進會面',
};

export const SOURCE_LABELS: Record<string, string> = {
  'employee-handbook.md': '僱員手冊',
  'benefits-guide.md': '福利及開支報銷指南',
  'it-setup.md': 'IT 設定及資訊保安指南',
  'onboarding-checklist.md': '首 30 天入職安排',
};

export const CATEGORY_LABELS: Record<string, string> = {
  HR: '人事', IT: '資訊科技', Team: '團隊',
};

export const AGENT_LABELS: Record<string, string> = {
  orchestrator: '流程協調', research: '文件查詢', workflow: '入職安排',
  synthesizer: '回覆整理', security: '安全檢查',
};

export function agentDescription(entry: AgentEvent): string {
  if (entry.status === 'blocked') return '已中止不適當的要求';
  if (entry.status === 'tool') {
    return TOOL_LABELS[entry.detail.split('(')[0]] ?? '正在處理入職事項';
  }
  const descriptions: Record<string, [string, string]> = {
    orchestrator: ['正在分析你的問題…', '已安排所需處理步驟'],
    research: ['正在查閱公司文件…', '已完成文件查詢'],
    workflow: ['正在處理入職事項…', '已處理入職安排'],
    synthesizer: ['正在整理回覆…', '回覆已準備好'],
    security: ['正在檢查要求…', '安全檢查已完成'],
  };
  return descriptions[entry.agent]?.[entry.status === 'completed' ? 1 : 0] ?? '正在處理…';
}

export function formatHongKongDate(iso?: string): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '日期不詳';
  return date.toLocaleString('zh-HK', {
    timeZone: 'Asia/Hong_Kong', dateStyle: 'medium', timeStyle: 'short',
  });
}
