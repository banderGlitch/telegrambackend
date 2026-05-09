import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { AdminUserDetail } from "../types";
import { ApiError, fetchUserDetail, sendDirectMessage } from "../api";

export function UserDetailPage() {
  const { id } = useParams();
  const userId = Number(id);
  const [data, setData] = useState<AdminUserDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [parseMode, setParseMode] = useState<string>("");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(userId)) return;
    let alive = true;
    (async () => {
      try {
        const d = await fetchUserDetail(userId);
        if (alive) setData(d);
      } catch (e) {
        if (alive) setErr(e instanceof ApiError ? e.message : String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [userId]);

  if (!Number.isFinite(userId)) {
    return <p className="text-orange-300">Invalid user id.</p>;
  }

  async function onSend() {
    setSendResult(null);
    setSending(true);
    try {
      const res = await sendDirectMessage(
        userId,
        msg,
        parseMode || null,
      );
      setSendResult(
        res.failed
          ? `Partial: ${res.sent} ok, ${res.failed} failed. ${res.errors.join("; ")}`
          : `Delivered (${res.sent})`,
      );
      setMsg("");
    } catch (e) {
      setSendResult(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  const u = data?.user;

  return (
    <div className="mx-auto max-w-5xl space-y-10 pb-24 md:pb-10">
      <nav className="text-sm text-slate-500">
        <Link className="hover:text-cyan-400" to="/players">
          ← Players
        </Link>
      </nav>

      {err ? <p className="text-red-300">{err}</p> : null}

      {u ? (
        <header className="panel p-8">
          <div className="flex flex-col gap-6 md:flex-row md:justify-between">
            <div>
              <p className="font-mono text-sm text-cyan-400">Telegram #{u.id}</p>
              <h1 className="mt-2 font-display text-3xl font-bold text-white">{u.name}</h1>
              <p className="mt-2 text-slate-400">
                @{u.username ?? "no username"} · language {u.language ?? "?"}
              </p>
              <dl className="mt-6 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
                <div>
                  <dt className="text-slate-500">Best score</dt>
                  <dd className="font-semibold text-white">{u.bestScore}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Runs (completed)</dt>
                  <dd className="font-semibold text-white">{u.runsPlayed}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Coins (lifetime)</dt>
                  <dd className="font-semibold text-white">{u.totalCoins}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Member since</dt>
                  <dd className="font-semibold text-white">{new Date(u.createdAt).toLocaleDateString()}</dd>
                </div>
              </dl>
            </div>
            <div className="md:w-80">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Direct message</p>
              <textarea
                className="input mt-2 min-h-[120px] resize-y"
                placeholder="Short operator note — appears in their Telegram chat from the bot."
                value={msg}
                onChange={(e) => setMsg(e.target.value)}
              />
              <label className="mt-3 block text-xs text-slate-500">
                Parse mode (optional)
                <select
                  className="input mt-1"
                  value={parseMode}
                  onChange={(e) => setParseMode(e.target.value)}
                >
                  <option value="">Plain text</option>
                  <option value="HTML">HTML</option>
                  <option value="MarkdownV2">MarkdownV2</option>
                </select>
              </label>
              <button
                type="button"
                className="btn-primary mt-4 w-full"
                disabled={sending || !msg.trim()}
                onClick={() => void onSend()}
              >
                {sending ? "Transmitting…" : "Send Telegram message"}
              </button>
              {sendResult ? <p className="mt-3 text-xs text-slate-400">{sendResult}</p> : null}
            </div>
          </div>
        </header>
      ) : !err ? (
        <p className="text-slate-500">Loading dossier…</p>
      ) : null}

      {data ? (
        <section className="panel overflow-x-auto p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
            <h2 className="font-display text-lg text-white">Session log</h2>
            <p className="text-xs text-slate-500">
              Sample: {data.runs.length} rows · {data.runsOpenInSample} open · {data.runsCompletedInSample}{" "}
              completed
            </p>
          </div>
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr className="border-b border-white/10">
                <th className="px-6 py-3">Run</th>
                <th className="px-6 py-3">State</th>
                <th className="px-6 py-3 text-right">Score</th>
                <th className="px-6 py-3 text-right">Coins</th>
                <th className="px-6 py-3 text-right">Duration</th>
                <th className="px-6 py-3">Started</th>
              </tr>
            </thead>
            <tbody>
              {data.runs.map((r) => (
                <tr key={r.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-6 py-3 font-mono text-xs text-slate-400">{r.id}</td>
                  <td className="px-6 py-3">
                    {r.endedAt ? (
                      <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                        Completed
                      </span>
                    ) : (
                      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-200">
                        Open
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-3 text-right tabular-nums">{r.score}</td>
                  <td className="px-6 py-3 text-right tabular-nums">{r.coins}</td>
                  <td className="px-6 py-3 text-right tabular-nums text-slate-400">
                    {(r.durationMs / 1000).toFixed(1)}s
                  </td>
                  <td className="px-6 py-3 text-xs text-slate-500">{new Date(r.startedAt).toLocaleString()}</td>
                </tr>
              ))}
              {data.runs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-slate-500">
                    No runs recorded yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
