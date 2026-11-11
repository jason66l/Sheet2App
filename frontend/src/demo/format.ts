import type { Entity, Field, Computed } from './types';

export const num = (v: unknown): number => {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
};

export const money = (v: unknown) => num(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });

export const percent = (v: unknown) => `${Math.round(num(v) * 100)}%`;

export function date(v: unknown): string {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(v)) return v == null ? '' : String(v);
  const [y, m, d] = v.slice(0, 10).split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}

export function column(entity: Entity, name: string): Field | Computed | undefined {
  return entity.fields.find((f) => f.name === name) ?? entity.computed?.find((c) => c.name === name);
}

/** Format a cell by its field type. */
export function cell(entity: Entity, name: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  const col = column(entity, name);
  switch (col?.type) {
    case 'money':
      return money(value);
    case 'percent':
      return percent(value);
    case 'date':
      return date(value);
    case 'number':
      return num(value).toLocaleString('en-US');
    default:
      return String(value);
  }
}

export const STATE_LABEL: Record<string, string> = {
  draft: 'Draft',
  submitted: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
};
