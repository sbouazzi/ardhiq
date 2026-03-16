'use client';

import { useEffect, useState } from 'react';
import { fetchAdminStats } from '@/lib/api';

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState('');
  const [stats, setStats] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const k = localStorage.getItem('ardhiq_admin_key');
    if (k) setAdminKey(k);
  }, []);

  async function load() {
    setErr(null);
    try {
      localStorage.setItem('ardhiq_admin_key', adminKey);
      const s = await fetchAdminStats(adminKey);
      setStats(s);
    } catch (e: any) {
      setErr(e?.message || 'Failed to load admin stats');
      setStats(null);
    }
  }

  return (
    <div className="grid">
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Admin dashboard</h1>
        <div className="muted">Protected by <code>x-admin-key</code> header.</div>
        <div style={{ height: 10 }} />
        <input
          className="input"
          placeholder="Enter admin key"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn primary" onClick={load}>Load stats</button>
          <button className="btn secondary" onClick={() => { localStorage.removeItem('ardhiq_admin_key'); setAdminKey(''); setStats(null); }}>Clear</button>
        </div>
        {err ? <div className="badge danger" style={{ marginTop: 12 }}>{err}</div> : null}
      </div>

      <div className="card">
        <h2>Stats</h2>
        {stats ? (
         <div className="card">
  <div>Total analyses: {stats.total_analyses}</div>
  <div>Analyses today: {stats.analyses_today}</div>
  <div>Last 7 days: {stats.analyses_last_7_days}</div>
  <div>Last 30 days: {stats.analyses_last_30_days}</div>

  <div style={{height:10}} />

  <div>Average score: {stats.average_score_total ?? "N/A"}</div>
  <div>Average score (7 days): {stats.average_score_last_7_days ?? "N/A"}</div>

  <div style={{height:10}} />

  <div>Has score: {stats.completion_health?.has_score?.count}</div>
  <div>Bilingual OK: {stats.completion_health?.bilingual_ok?.count}</div>
  <div>Parsing failed: {stats.completion_health?.parsing_failed?.count}</div>

  <div style={{height:10}} />

  <div>Total tokens (30 days): {stats.tokens_total_last_30_days}</div>
  <div>Avg tokens / analysis: {Math.round(stats.avg_tokens_per_analysis_last_30_days || 0)}</div>
</div>
        ) : (
          <div className="muted">No stats loaded.</div>
        )}
      </div>
    </div>
  );
}
