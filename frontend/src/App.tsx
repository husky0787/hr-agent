import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom';
import { ThemeProvider } from './ThemeContext';
import ChatPage from './pages/ChatPage';
import CheckinsAdmin from './pages/CheckinsAdmin';
import EvalsAdmin from './pages/EvalsAdmin';

function AppRoutes() {
  const { pathname } = useLocation();

  return (
    <>
      {/* Keep the chat mounted so navigation preserves drafts and active replies. */}
      <div hidden={pathname !== '/'}>
        <ChatPage />
      </div>
      <Routes>
        <Route path="/" element={<></>} />
        <Route path="/admin/checkins" element={<CheckinsAdmin />} />
        <Route path="/admin/evals" element={<EvalsAdmin />} />
      </Routes>
    </>
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
