import { useEffect, useState } from "react";
import type { AdminMessageLogRow } from "../types";
import { ApiError, broadcastMessage, fetchMessageLog, sendDirectMessage } from "../api";

export function MessagesPage() {
  const [text, setText] = useState("");
  const [parseMode, setParseMode] = useState("");
  const [directId, setDirectId] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [log, setLog] = useState<AdminMessageLogRow[]>([]);

  async function refreshLog() {
    try {
      const r = await fetchMessageLog();
      setLog(r.items);
    } catch {
      /* ignore on initial */
    }
  }

  useEffect(() => {
    void refreshLog();
  }, []);

  async function handleBroadcast() {
    if (!confirm("Send this message to EVERY stored pilot (excl. id 0)?")) return;
    setBusy(true);
    setStatus(null);
    try {
      const r = await broadcastMessage(text, parseMode || null);
      setStatus(`Broadcast finished: ${r.sent} delivered, ${r.failed} failed.`);
      if (r.errors.length) setStatus((s) => `${s} First errors: ${r.errors.slice(0, 5).join(" | ")}`);
      setText("");
      await refreshLog();
    } catch (e) {
      setStatus(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleDirect() {
    const id = Number(directId);
    if (!Number.isFinite(id)) {
      setStatus("Enter a numeric Telegram user id.");
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      const r = await sendDirectMessage(id, text, parseMode || null);
      setStatus(r.failed ? `Failed: ${r.errors.join("; ")}` : "Message sent.");
      setText("");
      await refreshLog();
    } catch (e) {
      setStatus(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-10 pb-24 md:pb-10">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-500">Campaigns</p>
        <h1 className="mt-2 font-display text-3xl font-bold text-white">Telegram outreach</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          One-to-one or fleet-wide pushes use the same bot token as the Mini App launcher. Messages are logged for
          compliance review.
        </p>
      </header>

      <section className="panel space-y-6 p-8">
        <textarea
          className="input min-h-[160px] resize-y font-mono text-sm"
          placeholder="Compose campaign copy… Respect Telegram rate limits on large blasts."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />

        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Parse mode
            <select className="input mt-2" value={parseMode} onChange={(e) => setParseMode(e.target.value)}>
              <option value="">Plain</option>
              <option value="HTML">HTML</option>
              <option value="MarkdownV2">MarkdownV2</option>
            </select>
          </label>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Direct — Telegram user id
            <input
              className="input mt-2 font-mono"
              value={directId}
              onChange={(e) => setDirectId(e.target.value)}
              placeholder="61000123456"
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn-primary" disabled={busy || text.trim().length < 2} onClick={handleDirect}>
            Send to ID
          </button>
          <button
            type="button"
            className="btn-ghost border-orange-400/40 text-orange-100 hover:bg-orange-950/40"
            disabled={busy || text.trim().length < 4}
            onClick={() => void handleBroadcast()}
          >
            Blast all pilots
          </button>
          <button type="button" className="btn-ghost text-xs" onClick={() => void refreshLog()}>
            Refresh audit log
          </button>
        </div>

        {status ? <p className="text-sm text-slate-400">{status}</p> : null}
      </section>

      <section className="panel overflow-x-auto p-0">
        <div className="border-b border-white/10 px-6 py-4">
          <h2 className="font-display text-lg text-white">Delivery audit ({log.length})</h2>
        </div>
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr className="border-b border-white/10">
              <th className="px-6 py-3">When</th>
              <th className="px-6 py-3">Scope</th>
              <th className="px-6 py-3 text-right">Reach</th>
              <th className="px-6 py-3 text-right">OK</th>
              <th className="px-6 py-3 text-right">Fail</th>
              <th className="px-6 py-3">Preview</th>
            </tr>
          </thead>
          <tbody>
            {log.map((row) => (
              <tr key={row.id} className="border-b border-white/5">
                <td className="px-6 py-3 text-xs text-slate-500">{new Date(row.createdAt).toLocaleString()}</td>
                <td className="px-6 py-3">
                  <span className="rounded-md bg-white/10 px-2 py-0.5 text-xs uppercase">{row.scope}</span>
                  {row.recipientUserId ? (
                    <span className="ml-2 font-mono text-cyan-400">#{row.recipientUserId}</span>
                  ) : null}
                </td>
                <td className="px-6 py-3 text-right">{row.recipientCount}</td>
                <td className="px-6 py-3 text-right text-emerald-400">{row.successCount}</td>
                <td className="px-6 py-3 text-right text-orange-400">{row.failCount}</td>
                <td className="max-w-[240px] truncate px-6 py-3 text-xs text-slate-400">{row.textPreview}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
