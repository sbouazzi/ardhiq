export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export type AnalyzeResponse = {
  analysis_id: string;
  report_markdown: string;
  report_ar_markdown?: string | null;
  report_fr_markdown?: string | null;
  score_total?: number | null;
  score_breakdown?: Record<string, number> | null;
};

export type HistoryItem = {
  id: string;
  created_at: string;
  location_text?: string | null;
  score_total?: number | null;
  short_summary?: string | null;
};

export type AnalysisDetail = {
  id: string;
  created_at: string;
  offer_text: string;
  user_context?: string | null;
  report_markdown: string;
  report_ar_markdown?: string | null;
  report_fr_markdown?: string | null;
  score_total?: number | null;
  score_breakdown?: Record<string, number> | null;
  location_text?: string | null;
  area_ha?: number | null;
  price_tnd?: number | null;
  price_per_m2_tnd?: number | null;
  water_source?: string | null;
  water_depth_m?: number | null;
  tree_type?: string | null;
  tree_count?: number | null;
  short_summary?: string | null;
};

export async function analyzeOffer(params: { offerText?: string; userContext?: string; imageFile?: File | null }) {
  const fd = new FormData();
  if (params.offerText) fd.append('offer_text', params.offerText);
  if (params.userContext) fd.append('user_context', params.userContext);
  if (params.imageFile) fd.append('image', params.imageFile);

  const res = await fetch(`${API_BASE}/api/analyze`, { method: 'POST', body: fd });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as AnalyzeResponse;
}

export async function fetchHistory(limit = 50) {
  const res = await fetch(`${API_BASE}/api/history?limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as HistoryItem[];
}

export async function fetchAnalysis(id: string) {
  const res = await fetch(`${API_BASE}/api/analysis/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as AnalysisDetail;
}

export async function fetchAdminStats(adminKey: string) {
  const res = await fetch(`${API_BASE}/api/admin/stats`, {
    headers: { 'x-admin-key': adminKey },
    cache: 'no-store'
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as any;
}
