import { useEffect, useRef, useState } from 'react';
import { fetchDocuments, streamChat } from '../api';
import type { ChatMessage, CompanyDocument } from '../api';
import { useTheme } from '../ThemeContext';
import ChatMarkdown from '../components/ChatMarkdown';
import SourceDocument from '../components/SourceDocument';

const SUGGESTIONS = [
  { title: '查詢公司福利', message: '請介紹公司的有薪年假、醫療保險登記期限及健康津貼。' },
  { title: '了解入職安排', message: '第一天入職要準備甚麼？' },
  { title: '查閱報銷流程', message: '公司開支報銷的流程及付款時間是甚麼？' },
];

export default function ChatPage() {
  const { theme, toggle } = useTheme();
  const [documents, setDocuments] = useState<CompanyDocument[]>([]);
  const [documentError, setDocumentError] = useState('');
  const [reload, setReload] = useState(0);
  const [showDocuments, setShowDocuments] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
  const [error, setError] = useState('');
  const activeRequest = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    setDocumentError('');
    fetchDocuments(controller.signal).then(setDocuments).catch((err: unknown) => {
      if (!controller.signal.aborted) setDocumentError(err instanceof Error ? err.message : '未能載入文件。');
    });
    return () => controller.abort();
  }, [reload]);
  useEffect(() => () => activeRequest.current?.abort(), []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, stage]);

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || loading) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    let conversation = messages;
    if (error && conversation.at(-1)?.failed) conversation = conversation.slice(0, -1);
    if (error && conversation.at(-1)?.role === 'user' && conversation.at(-1)?.content === question) {
      conversation = conversation.slice(0, -1);
    }
    const history = conversation.filter((item) => !item.failed && item.content);
    setInput('');
    setError('');
    setLoading(true);
    setStage('正在辨識主題…');
    setMessages([...conversation, { role: 'user', content: question }, { role: 'assistant', content: '' }]);
    let content = '';
    let citations: string[] = [];
    const update = () => setMessages((previous) => [
      ...previous.slice(0, -1), { role: 'assistant', content, citations },
    ]);
    try {
      await streamChat(question, history, (event, data) => {
        if (event === 'agent_log') {
          const entry = data as { agent: string; status: string };
          setStage(entry.agent === 'answer' ? '正在準備回答…' : entry.agent === 'identify_topics' ? '正在辨識主題…' : '正在搜尋文件…');
        }
        if (event === 'citations') citations = [...new Set(data as string[])];
        if (event === 'token') { content += data as string; update(); }
        if (event === 'done') { content = data as string; update(); }
      }, controller.signal);
    } catch (err) {
      const cancelled = controller.signal.aborted;
      setError(cancelled ? '已停止回覆。' : err instanceof Error && err.message !== 'Failed to fetch'
        ? err.message : '未能連接服務，請稍後再試。');
      setInput(question);
      setMessages((previous) => content
        ? [...previous.slice(0, -1), { role: 'assistant', content, citations, failed: true }]
        : previous.slice(0, -1));
    } finally {
      setLoading(false);
      setStage('');
      activeRequest.current = null;
    }
  }

  function clearChat() {
    if (loading) return;
    setMessages([]); setInput(''); setError('');
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-lg text-white">H</div>
          <div className="min-w-0"><span className="font-semibold">HR Agent</span><p className="truncate text-xs text-zinc-500">港雀科技 · 公司文件助理</p></div>
        </div>
        <div className="flex shrink-0 items-center gap-1 text-xs sm:gap-3">
          <button type="button" aria-expanded={showDocuments} onClick={() => setShowDocuments(!showDocuments)} className="rounded-lg px-2 py-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 md:hidden">公司文件</button>
          <button type="button" onClick={clearChat} disabled={loading} className="rounded-lg px-2 py-2 hover:bg-zinc-100 disabled:opacity-40 dark:hover:bg-zinc-800">清除對話</button>
          <button type="button" onClick={toggle} aria-label={theme === 'dark' ? '切換淺色模式' : '切換深色模式'} className="rounded-lg px-2 py-2 hover:bg-zinc-100 dark:hover:bg-zinc-800">{theme === 'dark' ? '☀' : '☾'}</button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside className={`${showDocuments ? 'block' : 'hidden'} max-h-[40dvh] shrink-0 overflow-y-auto border-b border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900 md:block md:max-h-none md:w-64 md:border-b-0 md:border-r`}>
          <h2 className="mb-2 text-sm font-semibold">公司文件</h2>
          <p className="mb-4 text-xs leading-relaxed text-zinc-500">直接閱讀原文，或在對話中查詢政策及入職安排。</p>
          <div className="flex flex-col items-start gap-3">{documents.map((document) => <SourceDocument key={document.filename} filename={document.filename} />)}</div>
          {!documents.length && !documentError && <p role="status" className="text-xs text-zinc-500">正在載入文件…</p>}
          {documentError && <div className="text-xs"><p role="alert">{documentError}</p><button type="button" className="mt-2 text-violet-600" onClick={() => setReload((value) => value + 1)}>重試文件清單</button></div>}
        </aside>
        <main className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="mx-auto max-w-3xl">
              {!messages.length && <section className="mx-auto flex max-w-lg flex-col items-center gap-5 py-8 text-center sm:py-16">
                <span aria-hidden="true" className="rounded-2xl bg-violet-100 px-4 py-3 text-2xl text-violet-600 dark:bg-violet-900/40">✦</span>
                <div><h1 className="text-lg font-semibold">Harbour Finch Labs｜港雀科技</h1><p className="mt-3 text-sm leading-6 text-zinc-500">查詢公司政策、福利及入職安排。回答附有來源，方便你閱讀完整文件。</p></div>
                <div className="grid w-full gap-2">{SUGGESTIONS.map((item) => <button key={item.title} type="button" onClick={() => send(item.message)} className="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left text-sm transition-colors hover:border-violet-300 dark:border-zinc-800 dark:bg-zinc-900">{item.title}<span aria-hidden="true" className="float-right text-zinc-400">↗</span></button>)}</div>
              </section>}
              <div className="space-y-6" aria-label="對話紀錄">{messages.map((message, index) => <article key={index} className={message.role === 'user' ? 'ml-auto max-w-[85%] rounded-2xl bg-violet-600 px-4 py-3 text-sm leading-6 text-white' : 'max-w-full text-sm leading-7'}>
                {message.role === 'user' ? <p className="whitespace-pre-wrap break-words">{message.content}</p> : <>
                  {message.content ? <ChatMarkdown content={message.content} /> : <p role="status" className="animate-pulse text-zinc-500">{stage || '正在準備回答…'}</p>}
                  {message.failed && <p className="mt-2 text-xs text-amber-600">回覆未完成</p>}
                  {!!message.citations?.length && <div className="mt-3 flex flex-wrap items-center gap-2"><span className="text-xs text-zinc-500">參考文件</span>{message.citations.map((name) => <SourceDocument key={name} filename={name} />)}</div>}
                </>}
              </article>)}</div>
              <div ref={bottom} />
            </div>
          </div>
          <div className="shrink-0 border-t border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900 sm:px-6">
            <div className="mx-auto max-w-3xl">
              {error && <p role="alert" className="mb-3 text-sm text-rose-600 dark:text-rose-400">{error}</p>}
              <form onSubmit={(event) => { event.preventDefault(); void send(); }} className="flex items-end gap-3 rounded-2xl border border-zinc-200 bg-zinc-50 p-2 dark:border-zinc-700 dark:bg-zinc-950">
                <textarea aria-label="輸入問題" placeholder="詢問公司政策或文件內容…" value={input} onChange={(event) => setInput(event.target.value)} maxLength={4000} disabled={loading} rows={2} onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) { event.preventDefault(); void send(); }
                }} className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-2 py-1 text-sm leading-6 outline-none placeholder:text-zinc-400 disabled:opacity-60" />
                {loading ? <button type="button" aria-label="停止回覆" onClick={() => activeRequest.current?.abort()} className="rounded-xl bg-zinc-800 px-4 py-2 text-sm text-white dark:bg-zinc-700">停止</button> : <button type="submit" aria-label="傳送訊息" disabled={!input.trim()} className="rounded-xl bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-40">傳送</button>}
              </form>
              <p className="mt-2 text-center text-[11px] text-zinc-400">回答僅供參考，請以來源文件為準。Enter 傳送 · Shift+Enter 換行</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
