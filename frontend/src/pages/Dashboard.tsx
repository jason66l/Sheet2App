import '../landing/landing.css';
import '../demo/demo.css';
import { useEffect, useState } from 'react';
import UploadDrop from '../landing/UploadDrop';
import Analyzing from '../demo/Analyzing';
import type { Me } from '../demo/types';
import { api } from '../lib/api';
import { signOut } from '../lib/supabase';
import { importAndCreateApp } from './importFile';

const ROLE_LABEL = { admin: 'Admin', approver: 'Approver', submitter: 'Submitter' } as const;

type Props = {
  /** A file chosen before signing in, picked up after the Google redirect. */
  pendingFile?: File | null;
  onPendingUsed?: () => void;
};

/** Signed-in home: my saved apps, plus upload to create a new one. */
export default function Dashboard({ pendingFile, onPendingUsed }: Props) {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<{ name: string; error?: string } | null>(null);

  useEffect(() => {
    api<Me>('/me')
      .then(setMe)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const upload = async (file: File) => {
    setUploading({ name: file.name });
    try {
      const appId = await importAndCreateApp(file);
      window.location.hash = `#/apps/${appId}`;
    } catch (e) {
      setUploading({ name: file.name, error: e instanceof Error ? e.message : String(e) });
    }
  };

  useEffect(() => {
    if (!pendingFile) return;
    onPendingUsed?.(); // use it once, so coming back here doesn't upload it again
    void upload(pendingFile);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingFile]);

  return (
    <div className="s2a gen">
      <header className="gen-bar">
        <div className="container gen-bar-inner">
          <a href="#/" className="logo" aria-label="Sheet2App home">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <rect x="1" y="1" width="20" height="20" rx="5" stroke="currentColor" strokeWidth="1.5" />
              <path d="M1 8h20M8 8v13" stroke="currentColor" strokeWidth="1.5" />
              <rect x="11" y="11" width="7" height="7" rx="1.5" fill="var(--accent)" />
            </svg>
            <span>Sheet2App</span>
          </a>
          <div className="gen-bar-actions">
            <span className="muted">{me?.email}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => void signOut()}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="container dash">
        <section aria-labelledby="apps-h">
          <h2 id="apps-h">Your apps</h2>
          {error && <p className="gen-alert" role="alert">{error}</p>}
          <div className="dash-apps">
            {me === null && !error && <p className="dash-empty">Loading…</p>}
            {me && me.apps.length === 0 && (
              <p className="dash-empty">No apps yet. Upload a spreadsheet to create your first one.</p>
            )}
            {me?.apps.map((a) => (
              <a key={a.id} href={`#/apps/${a.id}`}>
                <span className="dash-app-name">{a.name}</span>
                <span className="dash-app-meta">Created {new Date(a.created_at).toLocaleDateString()}</span>
                <span className={`gen-role gen-role-${a.role} dash-app-role`}>{ROLE_LABEL[a.role]}</span>
              </a>
            ))}
          </div>
        </section>

        <aside className="dash-side" aria-labelledby="new-h">
          <h2 id="new-h">New app</h2>
          <p>Upload a spreadsheet. The AI designs the app and it's saved to your account.</p>
          <UploadDrop onUpload={(f) => void upload(f)} continueLabel="Build my app" />
        </aside>
      </div>

      {uploading && (
        <Analyzing fileName={uploading.name} error={uploading.error} onCancel={() => setUploading(null)} />
      )}
    </div>
  );
}
