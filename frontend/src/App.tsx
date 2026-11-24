import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from './ThemeContext';
import ChatPage from './pages/ChatPage';

function AppRoutes() {
  return (
    <div className="flex h-dvh flex-col">
      <div className="min-h-0 flex-1">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="*" element={<div className="p-8 text-center"><p>找不到此頁面。</p><Link to="/" className="text-violet-600">返回對話</Link></div>} />
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
