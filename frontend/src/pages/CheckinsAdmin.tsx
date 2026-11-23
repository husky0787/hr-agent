import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCheckins } from '../api';
import type { Checkin } from '../api';
import { formatHongKongDate } from '../locale';

export default function CheckinsAdmin() {
  const [checkins, setCheckins] = useState<Checkin[]>([]);
  const [employeeFilter, setEmployeeFilter] = useState('');
  const [appliedFilter, setAppliedFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCheckins = useCallback(async (filter?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCheckins(filter);
      setCheckins(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '未能載入跟進會面，請稍後再試。');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCheckins(appliedFilter);
  }, [appliedFilter, loadCheckins]);

  const handleRefresh = () => {
    const filter = employeeFilter.trim() || undefined;
    setAppliedFilter(filter);
    if (filter === appliedFilter) {
      loadCheckins(filter);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-indigo-600">管理頁面</p>
            <h1 className="text-xl font-semibold text-slate-900">已安排的跟進會面</h1>
            <p className="text-sm text-slate-500">
              查看入職助理安排的主管及人力資源部跟進會面
            </p>
          </div>
          <Link
            to="/"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            返回對話
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="employee-filter" className="mb-1 block text-xs font-medium text-slate-500">
              按僱員編號篩選
            </label>
            <input
              id="employee-filter"
              type="text"
              value={employeeFilter}
              onChange={(e) => setEmployeeFilter(e.target.value)}
              placeholder="例如：alex-chen"
              className="w-56 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? '載入中…' : '重新整理'}
          </button>
          <p className="text-sm text-slate-500">
            共 {checkins.length} 個跟進會面
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">編號</th>
                <th className="px-4 py-3 font-medium">僱員</th>
                <th className="px-4 py-3 font-medium">入職日數</th>
                <th className="px-4 py-3 font-medium">會面主題</th>
                <th className="px-4 py-3 font-medium">建立時間（香港）</th>
              </tr>
            </thead>
            <tbody>
              {!loading && checkins.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400 italic">
                    暫時沒有跟進會面。你可以向助理提出：「幫我安排入職第 7 天與主管見面，討論工作目標。」
                  </td>
                </tr>
              )}
              {checkins.map((checkin) => (
                <tr key={checkin.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 text-slate-500">{checkin.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">{checkin.employee_id}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                      第 {checkin.day} 天
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-800">{checkin.topic}</td>
                  <td className="px-4 py-3 text-slate-500">{formatHongKongDate(checkin.scheduled_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
