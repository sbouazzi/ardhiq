'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { fetchHistory, type HistoryItem } from '@/lib/api';

export default function HistoryPage() {
  const [rows, setRows] = useState<HistoryItem[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const h = await fetchHistory(100);
        setRows(h);
      } catch (e: any) {
        setErr(e?.message || 'Failed to load');
      }
    })();
  }, []);

  return (
    <div className="card">
      <h1 style={{ marginTop: 0 }}>Analysis history</h1>
      {err ? <div className="badge danger">{err}</div> : null}

      <table className="table">
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <div style={{ fontWeight: 700 }}>{r.location_text || 'Unknown location'}</div>
                <div className="small">{new Date(r.created_at).toLocaleString()}</div>
              </td>
              <td style={{ textAlign: 'right' }}>
                <div className="badge">Score: {r.score_total ?? '—'}</div>
                <div className="small" style={{ marginTop: 6 }}>{r.short_summary || ''}</div>
              </td>
              <td style={{ textAlign: 'right' }}>
                <Link className="btn secondary" href={`/result/${r.id}`}>Open</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {rows.length === 0 && !err ? <div className="muted">No analyses yet.</div> : null}
    </div>
  );
}
