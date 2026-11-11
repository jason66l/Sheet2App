/** Shape of GET/POST /imports responses (backend/app/routes/imports.py). */
export type ImportSummary = {
  id: string;
  file_name: string;
  status: 'processing' | 'ready' | 'failed';
  error: string | null;
  proposal: {
    name: string;
    entities: { name: string; fields?: { name: string; type: string }[] }[];
    approval_rule?: unknown;
  } | null;
  reconciliation: { formulas_total: number; formulas_translated: number; matched: number; mismatches: unknown[] } | null;
  warnings: string[];
  app_id: string | null;
};

export type ImportState =
  | { phase: 'idle' }
  | { phase: 'uploading'; fileName: string }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; data: ImportSummary }
  | { phase: 'confirming'; data: ImportSummary }
  | { phase: 'confirmed'; data: ImportSummary; appId: string; records: number };
