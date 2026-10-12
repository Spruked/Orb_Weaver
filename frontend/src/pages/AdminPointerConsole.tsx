import React, { useEffect, useState } from 'react';
import { ArrowLeft, ExternalLink, Loader2, ShieldCheck } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { api, Customer } from '../services/api';

const AdminPointerConsole: React.FC<{ customer: Customer }> = ({ customer }) => {
  const { projectId } = useParams();
  const [consoleData, setConsoleData] = useState<Awaited<ReturnType<typeof api.getAdminPointerConsole>> | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!projectId || !customer.is_admin) return;
    void api.getAdminPointerConsole(projectId)
      .then(setConsoleData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Pointer console unavailable'));
  }, [customer.is_admin, projectId]);

  if (!customer.is_admin) {
    return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">Admin access required.</div>;
  }
  if (error) {
    return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</div>;
  }
  if (!consoleData) {
    return <div className="flex items-center gap-2 p-8 text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading pointer authority console…</div>;
  }

  return (
    <div className="-m-4 flex min-h-[calc(100vh-2rem)] flex-col bg-slate-950 md:-m-6">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 bg-slate-900 px-5 py-3 text-white">
        <div className="flex items-center gap-3">
          <Link to="/admin/customers" className="rounded-lg p-2 text-slate-300 hover:bg-white/10" aria-label="Back to admin"><ArrowLeft className="h-4 w-4" /></Link>
          <div><p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">Admin only · live proxy</p><h1 className="text-lg font-bold">Pointer Authority Console</h1><p className="text-xs text-slate-400">{consoleData.project.name || consoleData.project.domain} · {consoleData.target_count} targets · job {consoleData.job_id}</p></div>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-300"><ShieldCheck className="h-4 w-4 text-emerald-300" /> Decisions use the existing authority route <a href={consoleData.target_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-cyan-300 hover:text-white"><ExternalLink className="h-3 w-3" /> source</a></div>
      </header>
      <div className="min-h-0 flex-1 p-2 md:p-3">
        <iframe title={`Pointer authority review for ${consoleData.project.domain}`} src={consoleData.proxy_url} className="h-[calc(100vh-8rem)] min-h-[680px] w-full rounded-xl border border-slate-700 bg-white" />
      </div>
    </div>
  );
};

export default AdminPointerConsole;
