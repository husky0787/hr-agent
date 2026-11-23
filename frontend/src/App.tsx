import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom';
import { ThemeProvider } from './ThemeContext';
import ChatPage from './pages/ChatPage';
import CheckinsAdmin from './pages/CheckinsAdmin';
import EvalsAdmin from './pages/EvalsAdmin';

function AppRoutes() {
  const { pathname } = useLocation();

  return (
    <div className="flex h-dvh flex-col">
      {/* Keep the chat mounted so navigation preserves drafts and active replies. */}
      <div hidden={pathname !== '/'} className="min-h-0 flex-1">
        <ChatPage />
      </div>
      <div hidden={pathname === '/'} className="min-h-0 flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<></>} />
          <Route path="/admin/checkins" element={<CheckinsAdmin />} />
          <Route path="/admin/evals" element={<EvalsAdmin />} />
        </Routes>
      </div>
      <footer className="shrink-0 border-t border-zinc-200 bg-white px-3 py-2 text-center text-[11px] leading-4 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        示範環境：公司、員工及內部政策均為虛構
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}
