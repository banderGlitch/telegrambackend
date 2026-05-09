function Kpi({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="panel p-6">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 font-display text-3xl font-bold text-white">{value}</p>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function RunsVolumeChart({
  rows,
}: {
  rows: { date: string; count: number }[];
}) {
  const max = Math.max(...rows.map((r) => r.count), 1);
  return (
    <div className="panel p-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Engagement pulse</p>
          <p className="mt-1 text-sm text-slate-400">
            Completed runs per day (UTC) — trailing 7 days
          </p>
        </div>
      </div>
      <div className="mt-8 flex h-40 items-end gap-2">
        {rows.map((r) => (
          <div key={r.date} className="flex flex-1 flex-col items-center gap-2">
            <div
              className="w-full max-w-[2.75rem] rounded-t-md bg-gradient-to-t from-cyan-600/80 to-cyan-400 shadow-[0_0_22px_-4px_rgba(34,211,238,0.9)] transition hover:brightness-110"
              style={{
                height: `${Math.round((r.count / max) * 100)}%`,
                minHeight: r.count > 0 ? "8%" : "2px",
              }}
              title={`${r.date}: ${r.count} runs`}
            />
            <span className="truncate text-[10px] uppercase text-slate-500">{r.date.slice(5)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export { Kpi };
