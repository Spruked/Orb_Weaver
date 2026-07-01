import React, { FormEvent, useState } from 'react';
import { api, PublicPreflightReport } from '../services/api';

const PublicPreflight: React.FC = () => {
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [report, setReport] = useState<PublicPreflightReport | null>(null);
  const [error, setError] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setReport(null);
    setIsRunning(true);

    try {
      setReport(await api.publicPreflight(websiteUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preflight scan failed');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-8">
        <header className="flex items-center justify-between gap-4">
          <a href="/" className="text-sm font-bold tracking-[0.28em] text-cyan-200">
            ORB WEAVER
          </a>
          <nav className="flex items-center gap-4 text-sm text-slate-300">
            <a href="/marketplace" className="hover:text-white">Marketplace</a>
            <a href="/login" className="hover:text-white">Login</a>
          </nav>
        </header>

        <section className="flex flex-1 flex-col justify-center py-16">
          <p className="mb-3 text-sm font-semibold tracking-[0.24em] text-cyan-300">PUBLIC PREFLIGHT</p>
          <h1 className="max-w-3xl text-4xl font-black leading-tight md:text-6xl">
            Run a free ORB readiness scan.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            Check whether a website is ready for a basic Website ORB before creating an account.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
            <input
              className="min-h-[48px] flex-1 rounded-lg border border-cyan-300/20 bg-white px-4 text-slate-950 outline-none ring-cyan-300/40 focus:ring-4"
              type="text"
              value={websiteUrl}
              onChange={(event) => setWebsiteUrl(event.target.value)}
              placeholder="https://example.com"
              aria-label="Website URL"
              required
            />
            <button
              className="min-h-[48px] rounded-lg bg-cyan-300 px-6 font-bold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
              type="submit"
              disabled={isRunning}
            >
              {isRunning ? 'Scanning...' : 'Run Preflight'}
            </button>
          </form>

          {error && (
            <div className="mt-6 max-w-2xl rounded-lg border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
              {error}
            </div>
          )}

          {report && (
            <section className="mt-8 grid gap-4 rounded-lg border border-cyan-300/20 bg-white/5 p-5 shadow-2xl shadow-cyan-950/40 md:grid-cols-3">
              <div className="md:col-span-2">
                <p className="text-sm font-semibold text-cyan-200">{report.outcome_title}</p>
                <h2 className="mt-2 text-2xl font-bold">{report.site_url}</h2>
                <p className="mt-3 text-slate-300">{report.summary}</p>
                <ul className="mt-4 space-y-2 text-sm text-slate-200">
                  {report.reasons.slice(0, 4).map((reason) => (
                    <li key={reason}>- {reason}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg bg-slate-900/80 p-4">
                <p className="text-sm text-slate-400">Fit Score</p>
                <p className="mt-1 text-4xl font-black text-cyan-200">{report.fit_score}</p>
                <p className="mt-4 text-sm text-slate-400">Install Path</p>
                <p className="mt-1 text-sm font-semibold text-white">{report.install_path}</p>
                <p className="mt-4 text-sm text-slate-400">Pages Sampled</p>
                <p className="mt-1 text-sm font-semibold text-white">{report.basic_checks.sample_pages_read}</p>
              </div>
            </section>
          )}
        </section>
      </div>
    </main>
  );
};

export default PublicPreflight;
