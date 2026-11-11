import { api } from '../lib/api';

type ImportSummary = { id: string; status: 'processing' | 'ready' | 'failed'; error: string | null };

/** Upload a spreadsheet, let the AI design the app, and save it to my account. Returns the new app id. */
export async function importAndCreateApp(file: File): Promise<string> {
  const form = new FormData();
  form.append('file', file);
  const imp = await api<ImportSummary>('/imports', { method: 'POST', body: form });
  if (imp.status !== 'ready') throw new Error(imp.error ?? 'Could not read this spreadsheet.');
  const res = await api<{ app_id: string }>(`/imports/${imp.id}/confirm`, { method: 'POST' });
  return res.app_id;
}
