'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchAnalysis } from '@/lib/api';
import { Markdown } from '@/components/Markdown';
import { RealityCheckCard } from '@/components/RealityCheckCard';

function badgeKind(score?: number | null) {
  if (score === null || score === undefined) return 'warn';
  if (score >= 70) return 'ok';
  if (score >= 40) return 'warn';
  return 'danger';
}

export default function ResultPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await fetchAnalysis(id);
        setData(d);
      } catch (e: any) {
        setErr(e?.message || 'Failed to load');
      }
    })();
  }, [id]);

  const breakdown = useMemo(() => {
    const b = data?.score_breakdown || null;
    if (!b) return null;
    const entries = Object.entries(b) as Array<[string, number]>;
    return entries.sort((a, b) => a[0].localeCompare(b[0]));
  }, [data]);

  if (err) return <div className="card"><div className="badge danger">{err}</div></div>;
  if (!data) return <div className="card"><div className="muted">Loading…</div></div>;

  return (
    <div className="grid">
      <div className="card">
        <div className="kpi">
          <div className="score">{data.score_total ?? '—'}</div>
          <div>
            <div className={`badge ${badgeKind(data.score_total)}`}>ArdhIQ Score</div>
            <div className="small">Created: {new Date(data.created_at).toLocaleString()}</div>
          </div>
        </div>

        {breakdown ? (
          <div style={{ marginTop: 12 }}>
            <h2>Score breakdown</h2>
            <table className="table">
              <tbody>
                {breakdown.map(([k, v]) => (
                  <tr key={k}>
                    <td className="small">{k}</td>
                    <td style={{ textAlign: 'right' }}>{v} / 25</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <hr />

        <h2>Arabic analysis</h2>
        <Markdown markdown={data.report_ar_markdown || '—'} />

        <hr />

        <h2>French analysis</h2>
        <Markdown markdown={data.report_fr_markdown || '—'} />
      </div>

      <div className="card">
        <h2>Reality Check card</h2>
        <div className="muted">Download a shareable summary (use it to remind yourself what to verify).</div>
        <div style={{ height: 10 }} />
        <RealityCheckCard
          data={{
            location: data.location_text,
            area_ha: data.area_ha,
            price_tnd: data.price_tnd,
            score_total: data.score_total,
            verdict: null,
            risks: []
          }}
        />

        <hr />

        <h2>Raw offer text</h2>
        <div className="muted" style={{ whiteSpace: 'pre-wrap' }}>{data.offer_text}</div>
      </div>
    </div>
  );
}
