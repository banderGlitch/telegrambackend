import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, loginAdmin, setToken } from "../api";

export function LoginPage() {
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const res = await loginAdmin(password);
      setToken(res.accessToken);
      nav("/", { replace: true });
    } catch (ex) {
      if (ex instanceof ApiError) setErr(ex.message);
      else setErr(String(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyan-900/30 via-transparent to-transparent" />
      <div className="panel relative w-full max-w-md p-10">
        <h1 className="font-display text-center text-xl font-semibold uppercase tracking-[0.35em] text-cyan-400">
          Command
        </h1>
        <p className="mt-3 text-center text-sm text-slate-400">
          Secure operator access — JWT session stored in-browser only.
        </p>
        <form className="mt-10 space-y-5" onSubmit={onSubmit}>
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Dashboard password
            <input
              className="input mt-2"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>
          {err ? (
            <p className="rounded-lg bg-orange-950/60 px-3 py-2 text-sm text-orange-200 ring-1 ring-orange-500/30">
              {err}
            </p>
          ) : null}
          <button className="btn-primary w-full" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Enter console"}
          </button>
        </form>
      </div>
    </div>
  );
}
