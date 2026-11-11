import type { DemoResponse } from './types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/** Upload a spreadsheet to the demo server and get the generated app back. */
export async function demoImport(file: File): Promise<DemoResponse> {
  const form = new FormData();
  form.append('file', file);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/demo/import`, { method: 'POST', body: form });
  } catch {
    throw new Error(`Can't reach the demo server at ${API_URL}. Is it running? (uv run uvicorn backend.demo_server:app --reload --port 8000)`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* no JSON body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<DemoResponse>;
}
