import { useEffect, useState } from 'react';
import { api } from '../lib/api';

/** Opened from an invite link (#/join/<token>) after signing in: adds me to the app with the invite's role. */
export default function JoinPage({ token }: { token: string }) {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<{ app_id: string }>(`/invites/${token}/accept`, { method: 'POST' })
      .then((res) => (window.location.hash = `#/apps/${res.app_id}`))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [token]);

  return (
    <div className="s2a center-page">
      <div>
        <h1>{error ? "Couldn't join" : 'Joining…'}</h1>
        {error && (
          <>
            <p>{error}</p>
            <a className="btn btn-secondary btn-sm" href="#/">Go to my apps</a>
          </>
        )}
      </div>
    </div>
  );
}
