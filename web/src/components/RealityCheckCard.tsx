'use client';

import { toPng } from 'html-to-image';
import { useRef, useState } from 'react';

export type RealityCheckCardData = {
  location?: string | null;
  area_ha?: number | null;
  price_tnd?: number | null;
  score_total?: number | null;
  verdict?: string | null;
  risks?: string[];
};

function fmtMoney(n?: number | null) {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('fr-TN', { maximumFractionDigits: 0 }).format(n) + ' TND';
}

function fmtNum(n?: number | null, digits = 2) {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('fr-TN', { maximumFractionDigits: digits }).format(n);
}

export function RealityCheckCard({ data }: { data: RealityCheckCardData }) {
  const ref = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);

  async function download() {
    if (!ref.current) return;
    setBusy(true);
    try {
      const png = await toPng(ref.current, { cacheBust: true, pixelRatio: 2 });
      const a = document.createElement('a');
      a.href = png;
      a.download = `ardhiq-reality-check.png`;
      a.click();
    } finally {
      setBusy(false);
    }
  }

  const score = data.score_total ?? null;
  const scoreColor = score === null ? 'rgba(255,255,255,.14)' : score >= 70 ? 'rgba(61,220,151,.35)' : score >= 40 ? 'rgba(255,199,0,.35)' : 'rgba(255,77,77,.35)';

  return (
    <div>
      <div
        ref={ref}
        style={{
          width: '100%',
          borderRadius: 16,
          padding: 16,
          background: 'linear-gradient(135deg, rgba(124,92,255,.22), rgba(18,26,51,.92) 40%, rgba(0,0,0,.25))',
          border: `1px solid ${scoreColor}`
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18 }}>Reality Check</div>
            <div className="small">Analyzed with ArdhIQ</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 900, fontSize: 28 }}>{score ?? '—'}</div>
            <div className="small">ArdhIQ Score</div>
          </div>
        </div>

        <div style={{ height: 12 }} />

        <table className="table" style={{ fontSize: 13 }}>
          <tbody>
            <tr><td className="small">Location</td><td style={{ textAlign: 'right' }}>{data.location || '—'}</td></tr>
            <tr><td className="small">Area</td><td style={{ textAlign: 'right' }}>{fmtNum(data.area_ha)} ha</td></tr>
            <tr><td className="small">Price</td><td style={{ textAlign: 'right' }}>{fmtMoney(data.price_tnd)}</td></tr>
          </tbody>
        </table>

        <div style={{ height: 12 }} />

        <div className="small" style={{ marginBottom: 6 }}>Top risks (verify):</div>
        <ol className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          {(data.risks?.length ? data.risks : ['Missing legal/title verification', 'Unverified water reliability', 'Unclear access/electricity']).slice(0, 3).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ol>

        <div style={{ height: 10 }} />

        <div className="badge" style={{ width: 'fit-content' }}>{data.verdict || 'Verdict: Needs verification'}</div>
      </div>

      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn secondary" onClick={download} disabled={busy}>
          {busy ? 'Generating…' : 'Download card (PNG)'}
        </button>
      </div>
    </div>
  );
}
