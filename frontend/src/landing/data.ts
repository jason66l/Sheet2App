// Sample data shown in the homepage product previews.
// Numbers match the Spring Showcase example used across the mockups.

export type BudgetLine = {
  name: string;
  budget: number;
  approved: number;
  pending: number;
};

export const BUDGET_LINES: BudgetLine[] = [
  { name: 'Venue', budget: 1500, approved: 1500, pending: 0 },
  { name: 'Food & drinks', budget: 1200, approved: 742.4, pending: 240 },
  { name: 'Supplies & parts', budget: 900, approved: 418, pending: 372 },
  { name: 'Printing & signage', budget: 400, approved: 275, pending: 0 },
  { name: 'Prizes', budget: 500, approved: 0, pending: 0 },
  { name: 'Transport', budget: 300, approved: 0, pending: 0 },
];

export type PendingRequest = {
  id: string;
  title: string;
  submittedBy: string;
  line: string;
  amount: number;
  approvals: number;
  required: number;
  date: string;
  approvedBy?: string;
};

export const PENDING_REQUESTS: PendingRequest[] = [
  {
    id: 'servo',
    title: 'Servo motors (6)',
    submittedBy: 'Daniel Okafor',
    line: 'Supplies & parts',
    amount: 372,
    approvals: 0,
    required: 2,
    date: 'Nov 6',
  },
  {
    id: 'pizza',
    title: 'Pizza for build night',
    submittedBy: 'Maya Chen',
    line: 'Food & drinks',
    amount: 240,
    approvals: 1,
    required: 2,
    date: 'Nov 5',
    approvedBy: 'Ava Brooks',
  },
];

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

export const plain = (n: number) =>
  n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const remaining = (l: BudgetLine) => l.budget - l.approved - l.pending;

export const percent = (part: number, whole: number) => Math.round((part / whole) * 100);

export const TOTALS = BUDGET_LINES.reduce(
  (t, l) => ({
    budget: t.budget + l.budget,
    approved: t.approved + l.approved,
    pending: t.pending + l.pending,
  }),
  { budget: 0, approved: 0, pending: 0 },
);

export const TOTAL_LEFT = TOTALS.budget - TOTALS.approved - TOTALS.pending;

// Lines at or above this share of budget committed show a warning.
export const WARNING_THRESHOLD = 85;
