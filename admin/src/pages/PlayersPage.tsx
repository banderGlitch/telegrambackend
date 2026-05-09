import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { AdminUsersPage } from "../types";
import { ApiError, fetchUsers } from "../api";

export function PlayersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("updated");
  const [data, setData] = useState<AdminUsersPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function loadPage(p: number) {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetchUsers({
        page: p,
        pageSize: 20,
        search: search || undefined,
        sort,
      });
      setData(res);
      setPage(p);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial + sort changes only; search via Query
  }, [sort]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-24 md:pb-10">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-500">Directory</p>
        <h1 className="mt-2 font-display text-3xl font-bold text-white">Player intelligence</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Full roster with live aggregates. Open a pilot to inspect every run, session state, and send a 1:1 Telegram
          campaign.
        </p>
      </header>

      <div className="flex flex-col gap-4 md:flex-row md:items-end">
        <label className="flex-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Search (name, @handle, or Telegram id)
          <input
            className="input mt-2"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void loadPage(1);
            }}
            placeholder="e.g. 123456789 or @pilot"
          />
        </label>
        <div className="flex flex-wrap gap-3">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Sort
            <select
              className="input mt-2 min-w-[10rem]"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="updated">Last active</option>
              <option value="created">Newest signup</option>
              <option value="best_score">Best score</option>
              <option value="runs_played">Runs played</option>
            </select>
          </label>
          <button type="button" className="btn-primary self-end" onClick={() => void loadPage(1)}>
            Query
          </button>
        </div>
      </div>

      {err ? (
        <p className="rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-100">{err}</p>
      ) : null}

      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Pilot</th>
              <th className="px-4 py-3">Language</th>
              <th className="px-4 py-3 text-right">Best</th>
              <th className="px-4 py-3 text-right">Runs</th>
              <th className="px-4 py-3 text-right">Coins</th>
              <th className="px-4 py-3">Updated</th>
            </tr>
          </thead>
          <tbody>
            {(loading ? null : data?.items)?.map((u) => (
              <tr key={u.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono">
                  <Link className="text-cyan-400 hover:underline" to={`/players/${u.id}`}>
                    {u.id}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-white">{u.name}</div>
                  <div className="text-xs text-slate-500">{u.username ? `@${u.username}` : "—"}</div>
                </td>
                <td className="px-4 py-3 text-slate-400">{u.language ?? "—"}</td>
                <td className="px-4 py-3 text-right tabular-nums text-white">{u.bestScore}</td>
                <td className="px-4 py-3 text-right tabular-nums">{u.runsPlayed}</td>
                <td className="px-4 py-3 text-right tabular-nums">{u.totalCoins}</td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {new Date(u.updatedAt).toLocaleString()}
                </td>
              </tr>
            ))}
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                  Hydrating manifests…
                </td>
              </tr>
            ) : null}
            {!loading && data?.items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                  No records match filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {data && data.total > 0 ? (
        <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-slate-400">
          <span>
            Page {data.page} / {totalPages} · {data.total} pilots
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn-ghost text-xs disabled:opacity-30"
              disabled={page <= 1 || loading}
              onClick={() => void loadPage(page - 1)}
            >
              ← Prev
            </button>
            <button
              type="button"
              className="btn-ghost text-xs disabled:opacity-30"
              disabled={page >= totalPages || loading}
              onClick={() => void loadPage(page + 1)}
            >
              Next →
            </button>
          </div>
        </footer>
      ) : null}
    </div>
  );
}
