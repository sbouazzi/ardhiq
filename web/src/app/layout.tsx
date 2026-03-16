import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'ArdhIQ — Tunisia Land Offer Reality Check',
  description: 'AI-powered land-offer analysis for Tunisia. Detect risks, missing info, and investment potential.'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <div className="nav">
            <div className="brand">
              <span className="pill">ArdhIQ</span>
              <span className="muted">Tunisia land offer analysis</span>
            </div>
            <div className="row" style={{ justifyContent: 'flex-end' }}>
              <Link className="btn secondary" href="/analyze">Start Analysis</Link>
              <Link className="btn secondary" href="/history">History</Link>
              <Link className="btn secondary" href="/admin">Admin</Link>
            </div>
          </div>
          {children}
          <div className="small" style={{ marginTop: 24, opacity: 0.8 }}>
            ArdhIQ MVP — cautious, verification-first analysis. Never treat this as legal advice.
          </div>
        </div>
      </body>
    </html>
  );
}
