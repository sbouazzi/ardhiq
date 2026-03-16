import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="grid">
      <div className="card">
        <h1 style={{ marginTop: 0, fontSize: 34, letterSpacing: -0.4 }}>Reality-check farmland offers in Tunisia</h1>
        <p className="muted">
          Land offers on Facebook, WhatsApp, brokers, and listing sites are often incomplete or exaggerated.
          ArdhIQ reads the ad and produces a structured analysis: missing information, risks, questions to ask, and a cautious score.
        </p>
        <div className="row" style={{ marginTop: 16 }}>
          <Link className="btn primary" href="/analyze">Start Analysis</Link>
          <Link className="btn secondary" href="/history">View History</Link>
        </div>
        <hr />
        <div className="muted">
          What you get:
          <ul>
            <li>Extracted key facts (location, area, price, water source, trees)</li>
            <li>Missing info detection (legal, water rate, GPS, electricity…)</li>
            <li>Risk analysis + verification questions</li>
            <li>0–100 ArdhIQ score with breakdown</li>
            <li>Shareable “Reality Check” card</li>
          </ul>
        </div>
      </div>

      <div className="card">
        <h2>How it works</h2>
        <ol className="muted">
          <li>Paste offer text or upload a screenshot</li>
          <li>We OCR the screenshot (if provided)</li>
          <li>ArdhIQ analyzes only what’s explicitly stated</li>
          <li>You get a bilingual report (Arabic + French)</li>
        </ol>
        <div className="badge warn">MVP note: Always verify on-site (title, water, access).</div>
      </div>
    </div>
  );
}
