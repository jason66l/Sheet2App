import './landing.css';
import ProductPreview from './ProductPreview';
import RuleDemo from './RuleDemo';
import UploadDrop from './UploadDrop';
import { BUDGET_LINES, PENDING_REQUESTS, WARNING_THRESHOLD, money, percent, remaining } from './data';

type Props = {
  /** Called with the chosen .xlsx when the visitor continues. Wire to sign-in + POST /imports. */
  onUpload?: (file: File) => void;
  /** Signed-in user's email, or null when signed out. */
  userEmail?: string | null;
  onSignIn?: () => void;
  onSignOut?: () => void;
};

type AuthProps = Pick<Props, 'userEmail' | 'onSignIn' | 'onSignOut'>;

const Arrow = () => (
  <svg className="arrow" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M3 8h10m0 0L9 4m4 4l-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const Check = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

function Logo() {
  return (
    <a href="#top" className="logo" aria-label="Sheet2App home">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="20" height="20" rx="5" stroke="currentColor" strokeWidth="1.5" />
        <path d="M1 8h20M8 8v13" stroke="currentColor" strokeWidth="1.5" />
        <rect x="11" y="11" width="7" height="7" rx="1.5" fill="var(--accent)" />
      </svg>
      <span>even</span>
    </a>
  );
}

function Nav({ userEmail, onSignIn, onSignOut }: AuthProps) {
  return (
    <header className="nav">
      <div className="container nav-inner">
        <Logo />
        <nav aria-label="Main" className="nav-links">
          <a href="#how">How it works</a>
          <a href="#product">Product</a>
          <a href="#demo">Try it</a>
          <a href="#who">Who it's for</a>
        </nav>
        <div className="nav-actions">
          {userEmail ? (
            <>
              <span className="nav-user" title={userEmail}>
                {userEmail}
              </span>
              <button type="button" className="nav-signin" onClick={onSignOut}>
                Sign out
              </button>
            </>
          ) : onSignIn ? (
            <button type="button" className="nav-signin" onClick={onSignIn}>
              Sign in
            </button>
          ) : null}
          <a href="#upload" className="btn btn-primary btn-sm">
            Upload a spreadsheet
          </a>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="container">
        <p className="eyebrow hero-eyebrow">Spreadsheet in, app out</p>
        <h1 id="hero-title">
          Your budget spreadsheet,
          <br />
          now a working app.
        </h1>
        <p className="hero-sub">
          Upload the Excel file your club or team already runs on. Sheet2App reads its tables and formulas, then builds
          a shared app with expense forms, approvals and a budget that updates itself.
        </p>
        <div className="hero-actions">
          <a href="#upload" className="btn btn-primary">
            Upload a spreadsheet
          </a>
          <a href="#how" className="arrow-link">
            See how it works <Arrow />
          </a>
        </div>
        <p className="hero-meta">Works with .xlsx · Sign in with Google · Nothing is shared until you publish</p>
        <ProductPreview />
      </div>
    </section>
  );
}

/* ---------- How it works ---------- */

function StepUpload() {
  return (
    <div className="mini" aria-hidden="true">
      <div className="mini-file">
        <span>Event_Budget_2026.xlsx</span>
        <span className="mono muted">48 KB</span>
      </div>
      <div className="mini-progress">
        <span />
      </div>
      <ul className="mini-log mono">
        <li><Check /> 3 sheets found</li>
        <li><Check /> 6 budget lines, 11 expenses</li>
        <li><Check /> 29 formulas translated</li>
        <li><Check /> Totals match your file</li>
      </ul>
    </div>
  );
}

function StepReview() {
  const rows: [string, string, string][] = [
    ['Line', 'Text', 'Budget!A'],
    ['Budget', 'Money', 'Budget!B'],
    ['Status', 'Choice · 3', 'Expenses!G'],
    ['Approved by', 'People', 'Expenses!H'],
  ];
  return (
    <div className="mini" aria-hidden="true">
      <table className="mini-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Type</th>
            <th>From</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([f, t, s]) => (
            <tr key={f}>
              <td>{f}</td>
              <td>
                <span className="mini-select">{t}</span>
              </td>
              <td className="mono muted">{s}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mini-foot">
        <span className="muted">Rule found: 2 approvals over $200</span>
        <span className="mini-button">Publish app</span>
      </div>
    </div>
  );
}

function StepInvite() {
  const people: [string, string, string][] = [
    ['KP', 'Kai Patel', 'Admin'],
    ['AB', 'Ava Brooks', 'Approver'],
    ['MC', 'Maya Chen', 'Member'],
  ];
  return (
    <div className="mini" aria-hidden="true">
      <div className="mini-invite">
        <span className="mini-input mono">sheet2app.com/join/7f3k-q9</span>
        <span className="mini-select">Member</span>
        <span className="mini-button">Copy</span>
      </div>
      <ul className="mini-people">
        {people.map(([i, n, r]) => (
          <li key={n}>
            <span className="avatar">{i}</span>
            <span>{n}</span>
            <span className="muted">{r}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    {
      n: '01',
      title: 'Upload the file you already have',
      body: 'Budgets, expense logs and invoice trackers all work. We read every sheet, column type and formula, including the notes you typed in the margins.',
      art: <StepUpload />,
    },
    {
      n: '02',
      title: 'Check what we found',
      body: 'See each detected field, where it came from and how totals are calculated. Rename, retype or remove anything before you publish.',
      art: <StepReview />,
    },
    {
      n: '03',
      title: 'Invite the people who use it',
      body: 'Share one link. Members submit expenses, approvers approve, and the budget recalculates on its own. No more emailing the latest version.',
      art: <StepInvite />,
    },
  ];
  return (
    <section id="how" className="section" aria-labelledby="how-title">
      <div className="container">
        <div className="section-head">
          <p className="eyebrow">How it works</p>
          <h2 id="how-title">Three steps, and the spreadsheet you built still does the thinking.</h2>
        </div>
        <ol className="steps">
          {steps.map((s) => (
            <li key={s.n} className="step">
              <span className="step-num" aria-hidden="true">
                {s.n}
              </span>
              <div className="step-text">
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
              <div className="step-art">{s.art}</div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ---------- Product features ---------- */

function ExpenseFormShot() {
  return (
    <div className="shot" aria-hidden="true">
      <div className="shot-head">
        <span>New expense</span>
        <span className="muted">Spring Showcase Budget</span>
      </div>
      <div className="form-shot">
        <div className="field">
          <span className="field-label">Description</span>
          <span className="field-input">Pizza for build night</span>
        </div>
        <div className="field-row">
          <div className="field">
            <span className="field-label">Amount</span>
            <span className="field-input mono">$240.00</span>
          </div>
          <div className="field">
            <span className="field-label">Budget line</span>
            <span className="field-input field-select">Food &amp; drinks</span>
          </div>
        </div>
        <div className="field">
          <span className="field-label">Receipt</span>
          <span className="field-input field-file">
            <span>receipt_010.jpg</span>
            <span className="mono muted">1.2 MB</span>
          </span>
        </div>
        <div className="form-shot-foot">
          <span className="muted">Over $200 · needs 2 approvals</span>
          <span className="mini-button mini-button-primary">Submit for approval</span>
        </div>
      </div>
    </div>
  );
}

function ApprovalQueueShot() {
  return (
    <div className="shot" aria-hidden="true">
      <div className="shot-head">
        <span>Approvals</span>
        <span className="muted">2 waiting on you</span>
      </div>
      <ul className="queue-shot">
        {PENDING_REQUESTS.map((r) => (
          <li key={r.id}>
            <div className="queue-shot-top">
              <div>
                <span className="queue-title">{r.title}</span>
                <span className="queue-meta">
                  {r.submittedBy} · {r.line} · {r.date}
                </span>
              </div>
              <span className="queue-amount">{money(r.amount)}</span>
            </div>
            <div className="approvals-track" aria-hidden="true">
              {Array.from({ length: r.required }, (_, i) => (
                <span key={i} className={i < r.approvals ? 'is-done' : ''} />
              ))}
              <span className="muted">
                {r.approvals} of {r.required} approvals{r.approvedBy ? ` · ${r.approvedBy}` : ''}
              </span>
            </div>
            <div className="queue-shot-actions">
              <span className="mini-button mini-button-primary">Approve</span>
              <span className="mini-button">Reject</span>
              <span className="muted queue-receipt">View receipt</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BudgetShot() {
  return (
    <div className="shot" aria-hidden="true">
      <div className="shot-head">
        <span>Budget by line</span>
        <span className="muted">Updated when an expense is approved</span>
      </div>
      <div className="budget-shot-scroll">
        <table className="budget-shot">
          <thead>
            <tr>
              <th>Line</th>
              <th className="num">Budget</th>
              <th className="wide">Committed</th>
              <th className="num">Left</th>
            </tr>
          </thead>
          <tbody>
            {BUDGET_LINES.map((l) => {
              const committed = percent(l.approved + l.pending, l.budget);
              const warn = committed >= WARNING_THRESHOLD && committed < 100;
              return (
                <tr key={l.name} className={warn ? 'is-warning' : ''}>
                  <td>
                    {l.name}
                    {warn && <span className="warn-text"> · {committed}% committed</span>}
                  </td>
                  <td className="num">{money(l.budget)}</td>
                  <td className="wide">
                    <div className="bar">
                      <span className="bar-approved" style={{ width: `${(l.approved / l.budget) * 100}%` }} />
                      <span className="bar-pending" style={{ width: `${(l.pending / l.budget) * 100}%` }} />
                    </div>
                  </td>
                  <td className="num">{money(remaining(l))}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="shot-legend">
        <span><i className="swatch swatch-approved" /> Approved</span>
        <span><i className="swatch swatch-pending" /> Pending</span>
      </div>
    </div>
  );
}

function Features() {
  return (
    <section id="product" className="section section-tight" aria-labelledby="product-title">
      <div className="container">
        <h2 id="product-title" className="sr-only">
          Product
        </h2>

        <article className="feature">
          <div className="feature-text">
            <p className="eyebrow">Expense forms</p>
            <h3>A form built from your columns, not a template.</h3>
            <p>
              Every field comes from your spreadsheet. Dropdowns come from its data validation, and amounts are checked
              before anyone submits. Members attach the receipt and they're done.
            </p>
            <dl className="feature-facts">
              <div>
                <dt>Fields</dt>
                <dd>From your header row</dd>
              </div>
              <div>
                <dt>Dropdowns</dt>
                <dd>From your data validation lists</dd>
              </div>
            </dl>
          </div>
          <ExpenseFormShot />
        </article>

        <article className="feature feature-reverse">
          <div className="feature-text">
            <p className="eyebrow">Approvals</p>
            <h3>Rules your treasurer wrote down, now enforced.</h3>
            <p>
              "Over $200 needs two signatures" stops being a note in cell A12. Approvers see the request, the receipt and
              the budget left on that line. Nobody can approve their own expense.
            </p>
          </div>
          <ApprovalQueueShot />
        </article>

        <article className="feature feature-wide">
          <div className="feature-wide-head">
            <div>
              <p className="eyebrow">Live budget</p>
              <h3>Always the current number. Never the latest-version file.</h3>
            </div>
            <p>
              Approved and pending spending roll up the moment they change. Lines close to their limit are flagged on
              the dashboard, so you find out before you overspend, not after.
            </p>
          </div>
          <BudgetShot />
        </article>
      </div>
    </section>
  );
}

/* ---------- Demo ---------- */

function DemoSection() {
  return (
    <section id="demo" className="demo-band" aria-labelledby="demo-title">
      <div className="container demo">
        <div className="demo-text">
          <p className="eyebrow">Try it</p>
          <h2 id="demo-title">Change the app by describing the change.</h2>
          <p>
            Type a request the way you'd say it in a meeting. Sheet2App shows exactly what changes and who it affects.
            You confirm, or you don't.
          </p>
          <ul className="demo-list">
            <li>Fields: add, rename, retype</li>
            <li>Approval rules and limits</li>
            <li>Budget warnings</li>
          </ul>
        </div>
        <RuleDemo />
      </div>
    </section>
  );
}

/* ---------- Trust ---------- */

function Trust() {
  return (
    <section className="section" aria-labelledby="trust-title">
      <div className="container trust">
        <div className="trust-text">
          <p className="eyebrow">Accuracy</p>
          <h2 id="trust-title">AI designs the app. It never touches the math.</h2>
          <p>
            Every total, every rule and every approval runs in tested code, and is checked against your original file
            before you publish.
          </p>
        </div>
        <div className="ledger">
          <div className="ledger-col">
            <h3 className="eyebrow">The AI</h3>
            <ul>
              <li>Reads your sheets and formulas</li>
              <li>Proposes fields, links and rules</li>
              <li>Turns your requests into changes you review</li>
            </ul>
          </div>
          <div className="ledger-col">
            <h3 className="eyebrow">Tested code</h3>
            <ul>
              <li>Calculates every total, to the cent</li>
              <li>Enforces approval rules</li>
              <li>Records who approved what, and when</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------- Audience ---------- */

function Audience() {
  const rows: [string, string][] = [
    ['Student organizations', 'Event budgets and reimbursements, with the treasurer and president signing off.'],
    ['Small businesses', 'Expense tracking and purchase approvals without buying a finance platform.'],
    ['Teams with their own budget', "Department and project budgets that live outside the company's main system."],
  ];
  return (
    <section id="who" className="section section-tight" aria-labelledby="who-title">
      <div className="container audience">
        <h2 id="who-title">Built for the people who keep the spreadsheet.</h2>
        <dl className="audience-list">
          {rows.map(([t, d]) => (
            <div key={t}>
              <dt>{t}</dt>
              <dd>{d}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

/* ---------- Upload CTA ---------- */

function UploadCta({ onUpload, needsSignIn }: { onUpload: (file: File) => void; needsSignIn: boolean }) {
  return (
    <section id="upload" className="section cta" aria-labelledby="upload-title">
      <div className="container cta-inner">
        <div>
          <h2 id="upload-title">Start with the file you already have.</h2>
          <p>Upload it to see your app. You'll sign in with Google before anything is saved or shared.</p>
        </div>
        <UploadDrop onUpload={onUpload} continueLabel={needsSignIn ? 'Continue with Google' : 'Build my app'} />
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <Logo />
        <nav aria-label="Footer">
          <a href="#privacy">Privacy</a>
          <a href="#terms">Terms</a>
          <a href="#contact">Contact</a>
        </nav>
      </div>
    </footer>
  );
}

export default function Landing({
  onUpload = (f) => console.info('Upload selected:', f.name),
  userEmail = null,
  onSignIn,
  onSignOut,
}: Props) {
  return (
    <div className="s2a" id="top">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Nav userEmail={userEmail} onSignIn={onSignIn} onSignOut={onSignOut} />
      <main id="main">
        <Hero />
        <HowItWorks />
        <Features />
        <DemoSection />
        <Trust />
        <Audience />
        <UploadCta onUpload={onUpload} needsSignIn={!userEmail && Boolean(onSignIn)} />
      </main>
      <Footer />
    </div>
  );
}
