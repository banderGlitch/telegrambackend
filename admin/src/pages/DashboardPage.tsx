import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { AdminInsight, AdminLiveSessions, AdminOverview } from "../types";
import { ApiError, downloadUsersCsv, fetchDormantInsight, fetchLiveSessions, fetchOverview } from "../api";
import { Kpi, RunsVolumeChart } from "../components/dashboardWidgets";

export function DashboardPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [dormant, setDormant] = useState<AdminInsight | null>(null);
  const [live, setLive] = useState<AdminLiveSessions | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [autoRefreshSessions, setAutoRefreshSessions] = useState(true);

  const loadLive = useCallback(async () => {
    try {
      const L = await fetchLiveSessions(45);
      setLive(L);
    } catch {
      /* keep last snapshot; avoid flashing global error for optional panel */
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [o, d] = await Promise.all([fetchOverview(), fetchDormantInsight(14, 6)]);
        if (!alive) return;
        setOverview(o);
        setDormant(d);
        await loadLive();
      } catch (e) {
        if (!alive) return;
        setErr(e instanceof ApiError ? e.message : String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [loadLive]);

  useEffect(() => {
    if (!autoRefreshSessions) return;
    const id = setInterval(() => {
      void loadLive();
    }, 15000);
    return () => clearInterval(id);
  }, [autoRefreshSessions, loadLive]);

  return (
    <div className="mx-auto max-w-6xl space-y-10 pb-24 md:pb-6">
      <header className="flex flex-col gap-4 border-b border-white/10 pb-8 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-500">Operations</p>
          <h1 className="mt-2 font-display text-3xl font-bold text-white md:text-4xl">Fleet overview</h1>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Live picture of every pilot, run throughput, and dormancy so you can target campaigns with intent.
          </p>
        </div>
        <button
          type="button"
          className="btn-ghost self-start md:self-auto"
          disabled={exporting}
          onClick={async () => {
            setExporting(true);
            try {
              await downloadUsersCsv();
            } catch (e) {
              alert(e instanceof ApiError ? e.message : String(e));
            } finally {
              setExporting(false);
            }
          }}
        >
          {exporting ? "Preparing CSV…" : "Export roster (CSV)"}
        </button>
      </header>

      {err ? (
        <p className="rounded-xl border border-orange-500/40 bg-orange-950/40 px-4 py-3 text-sm text-orange-100">
          {err}
        </p>
      ) : null}

      {overview ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Kpi label="Registered pilots" value={overview.totalUsers} />
          <Kpi
            label="Completed runs (all time)"
            value={overview.totalCompletedRuns}
            hint={`${overview.openRuns} sessions still open`}
          />
          <Kpi label="Runs · last 24h" value={overview.runsLast24h} />
          <Kpi label="New pilots · 7d" value={overview.newUsers7d} />
          <Kpi
            label="Re-engagement pool"
            value={overview.dormantUsers14d}
            hint="No finished run in 14 days"
          />
        </section>
      ) : !err ? (
        <p className="text-slate-500">Loading telemetry…</p>
      ) : null}

      {live ? (
        <section className="panel overflow-hidden p-0">
          <div className="flex flex-col gap-4 border-b border-white/10 px-6 py-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-400/90">Live sessions</p>
              <h2 className="mt-1 font-display text-xl text-white">Open runs (in flight)</h2>
              <p className="mt-1 max-w-2xl text-xs text-slate-500">{live.caveat}</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={autoRefreshSessions}
                  onChange={(e) => setAutoRefreshSessions(e.target.checked)}
                  className="rounded border-white/20 bg-orbit-900"
                />
                Auto-refresh · 15s
              </label>
              <button type="button" className="btn-ghost text-xs" onClick={() => void loadLive()}>
                Refresh now
              </button>
            </div>
          </div>
          {live.totalReturned === 0 ? (
            <p className="px-6 py-10 text-center text-sm text-slate-500">
              No open run rows right now — nobody is mid-session (or everyone finished their last game).
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-500">
                  <tr className="border-b border-white/10">
                    <th className="px-6 py-3">Pilot</th>
                    <th className="px-6 py-3">Run</th>
                    <th className="px-6 py-3">Started</th>
                    <th className="px-6 py-3">Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {live.items.map((row) => (
                    <tr key={row.runId} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="px-6 py-3">
                        <Link className="font-medium text-cyan-400 hover:underline" to={`/players/${row.userId}`}>
                          {row.name}
                        </Link>
                        <div className="text-xs text-slate-500">
                          #{row.userId}
                          {row.username ? ` · @${row.username}` : ""}
                        </div>
                      </td>
                      <td className="px-6 py-3 font-mono text-xs text-slate-400">{row.runId}</td>
                      <td className="px-6 py-3 text-xs text-slate-500">
                        {new Date(row.startedAt).toLocaleString()}
                      </td>
                      <td className="px-6 py-3">
                        {row.presumedInGame ? (
                          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-300">
                            Likely playing · last {live.thresholdMinutes}m
                          </span>
                        ) : (
                          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-200">
                            Stale open run
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {overview ? <RunsVolumeChart rows={overview.runsByDay} /> : null}

      {dormant && dormant.sample.length > 0 ? (
        <section className="panel p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Innovation radar</p>
              <h2 className="mt-2 font-display text-lg text-white">{dormant.title}</h2>
              <p className="mt-1 text-sm text-slate-400">
                Surface pilots worth a personalised nudge. Jump into a profile to DM them instantly.
              </p>
            </div>
          </div>
          <ul className="mt-6 divide-y divide-white/10">
            {dormant.sample.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center gap-4 py-3 text-sm">
                <Link className="font-mono text-cyan-400 hover:underline" to={`/players/${row.id}`}>
                  #{row.id}
                </Link>
                <span className="font-medium text-white">{row.name}</span>
                {row.username ? (
                  <span className="text-slate-500">@{row.username}</span>
                ) : (
                  <span className="text-slate-600">no @username</span>
                )}
                <span className="ml-auto rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-400">
                  best {row.best_score}
                </span>
                <Link className="text-xs uppercase tracking-wide text-cyan-500 hover:text-cyan-300" to="/messages">
                  Message →
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
