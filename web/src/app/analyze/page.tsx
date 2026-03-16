'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { analyzeOffer } from '@/lib/api';

export default function AnalyzePage() {
  const router = useRouter();
  const [offerText, setOfferText] = useState('');
  const [userContext, setUserContext] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onAnalyze() {
    setErr(null);
    if (!offerText.trim() && !imageFile) {
      setErr('Please paste offer text or upload a screenshot.');
      return;
    }
    setBusy(true);
    try {
      const resp = await analyzeOffer({ offerText, userContext, imageFile });
      router.push(`/result/${resp.analysis_id}`);
    } catch (e: any) {
      setErr(e?.message || 'Failed to analyze.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <div className="card">
        <h1 style={{ marginTop: 0 }}>Analyze a land offer</h1>
        <div className="muted" style={{ marginBottom: 10 }}>
          Option A: paste the offer copied from Facebook, WhatsApp, Instagram, brokers, or listing websites.
        </div>
        <label className="small">Offer text</label>
        <textarea
          placeholder="Example: أرض فلاحية للبيع… / Terrain agricole à vendre…"
          value={offerText}
          onChange={(e) => setOfferText(e.target.value)}
        />

        <div style={{ height: 12 }} />

        <div className="muted" style={{ marginBottom: 10 }}>
          Option B: upload a screenshot of the ad. We’ll extract the text with OCR.
        </div>
        <input
          className="input"
          type="file"
          accept="image/*"
          onChange={(e) => setImageFile(e.target.files?.[0] || null)}
        />

        <div style={{ height: 12 }} />

        <label className="small">Investment context (optional)</label>
        <input
          className="input"
          placeholder="Budget 100000 TND · Looking for olive farm · Prefer reliable water source"
          value={userContext}
          onChange={(e) => setUserContext(e.target.value)}
        />

        {err ? (
          <div className="badge danger" style={{ marginTop: 12 }}>
            {err}
          </div>
        ) : null}

        <div className="row" style={{ marginTop: 14 }}>
          <button className="btn primary" onClick={onAnalyze} disabled={busy}>
            {busy ? 'Analyzing…' : 'Analyze Offer'}
          </button>
          <button
            className="btn secondary"
            onClick={() => {
              setOfferText('');
              setUserContext('');
              setImageFile(null);
              setErr(null);
            }}
            disabled={busy}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Tips for better results</h2>
        <ul className="muted">
          <li>Include price + area + exact location text if possible.</li>
          <li>If a well is mentioned, note depth and whether it’s legal / declared.</li>
          <li>Tree offers: include number, age (if known), irrigation type.</li>
          <li>For screenshots: crop to the ad text for better OCR.</li>
        </ul>
        <div className="badge warn">ArdhIQ never invents facts — missing info increases risk.</div>
      </div>
    </div>
  );
}
