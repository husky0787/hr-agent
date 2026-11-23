import { useEffect, useId, useRef, useState } from 'react';
import { fetchSourceDocument } from '../api';
import { SOURCE_LABELS } from '../locale';
import ChatMarkdown from './ChatMarkdown';

type DocumentState = { content: string; error?: never } | { error: string; content?: never } | null;

export default function SourceDocument({ filename }: { filename: string }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [document, setDocument] = useState<DocumentState>(null);
  const title = SOURCE_LABELS[filename] ?? filename;

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    fetchSourceDocument(filename, controller.signal).then(
      (content) => { if (!controller.signal.aborted) setDocument({ content }); },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setDocument({ error: error instanceof Error ? error.message : '暫時未能載入文件。' });
        }
      },
    );
    return () => controller.abort();
  }, [open, filename, attempt]);

  function showDocument() {
    setDocument(null);
    setOpen(true);
    dialogRef.current?.showModal();
  }

  return (
    <>
      <button
        type="button"
        onClick={showDocument}
        title={`閱讀 ${filename}`}
        aria-haspopup="dialog"
        className="inline-flex items-center rounded-md border border-violet-200/60 bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 transition-colors hover:bg-violet-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 dark:border-violet-800/50 dark:bg-violet-900/40 dark:text-violet-400 dark:hover:bg-violet-900/70"
      >
        {title} <span aria-hidden="true" className="ml-1">↗</span>
      </button>
      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        onClose={() => setOpen(false)}
        onClick={(event) => { if (event.target === event.currentTarget) dialogRef.current?.close(); }}
        className="m-auto max-h-[85dvh] w-[calc(100%-2rem)] max-w-3xl overflow-hidden rounded-2xl border border-zinc-200 bg-white p-0 text-zinc-800 shadow-2xl backdrop:bg-black/50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
      >
        <div className="flex max-h-[85dvh] flex-col">
          <header className="flex shrink-0 items-start justify-between gap-4 border-b border-zinc-200 p-5 dark:border-zinc-700">
            <div className="min-w-0">
              <h2 id={titleId} className="text-lg font-semibold">{title}</h2>
              <p className="mt-1 break-all text-xs text-zinc-500 dark:text-zinc-400">{filename}</p>
            </div>
            <button type="button" autoFocus onClick={() => dialogRef.current?.close()} className="shrink-0 rounded-lg px-3 py-2 text-sm hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-violet-500 dark:hover:bg-zinc-800">
              關閉
            </button>
          </header>
          <div className="min-h-0 overflow-y-auto overscroll-contain p-5 text-sm leading-relaxed sm:p-7">
            {!document && <p role="status">正在載入文件…</p>}
            {document?.error && (
              <div role="alert">
                <p>{document.error}</p>
                <button type="button" className="mt-3 rounded-lg bg-violet-100 px-3 py-2 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300" onClick={() => { setDocument(null); setAttempt((value) => value + 1); }}>重試</button>
              </div>
            )}
            {document?.content !== undefined && <article className="break-words"><ChatMarkdown content={document.content} /></article>}
          </div>
        </div>
      </dialog>
    </>
  );
}
