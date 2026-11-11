import { useEffect, useState } from 'react';
import Landing from './landing/Landing';
import DemoFlow from './demo/DemoFlow';
import AppPage from './pages/AppPage';
import Dashboard from './pages/Dashboard';
import JoinPage from './pages/JoinPage';
import { savePendingUpload, takePendingUpload } from './lib/pendingUpload';
import { signInWithGoogle, supabaseConfigured } from './lib/supabase';
import { useSession } from './lib/useSession';

/**
 * Routes (hash-based, no router library):
 *   #/              signed out: homepage. Signed in: My apps.
 *   #/apps/<id>     a saved app
 *   #/join/<token>  accept an invite link
 * VITE_DEMO_MODE=true in frontend/.env.local switches to the no-sign-in demo (backend/demo_server.py).
 */
const DEMO = import.meta.env.VITE_DEMO_MODE === 'true';
const RETURN_KEY = 's2a:return-to';

export default function App() {
  return DEMO ? <DemoFlow /> : <MainFlow />;
}

type Route = { kind: 'home' } | { kind: 'app'; id: string } | { kind: 'join'; token: string };

function parse(hash: string): Route {
  const app = hash.match(/^#\/apps\/([\w-]+)/);
  if (app) return { kind: 'app', id: app[1] };
  const join = hash.match(/^#\/join\/([\w-]+)/);
  if (join) return { kind: 'join', token: join[1] };
  return { kind: 'home' };
}

function useHash() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const on = () => setHash(window.location.hash);
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return hash;
}

/** Google sign-in leaves the page; remember where to come back to. */
function signIn(returnTo: string) {
  sessionStorage.setItem(RETURN_KEY, returnTo);
  void signInWithGoogle();
}

function MainFlow() {
  const session = useSession();
  const route = parse(useHash());
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  // Just signed in: go back to the page that asked for sign-in, and pick up a file chosen before it.
  useEffect(() => {
    if (!session) return;
    const back = sessionStorage.getItem(RETURN_KEY);
    if (back) {
      sessionStorage.removeItem(RETURN_KEY);
      window.location.hash = back;
    }
    takePendingUpload()
      .then((f) => f && setPendingFile(f))
      .catch(() => {});
  }, [session]);

  if (!supabaseConfigured) {
    return (
      <div className="s2a center-page">
        <div>
          <h1>Supabase isn't set up yet</h1>
          <p>Copy frontend/.env.example to frontend/.env.local and fill in the Supabase URL and publishable key, or set VITE_DEMO_MODE=true for the demo.</p>
        </div>
      </div>
    );
  }
  if (session === undefined) return <div className="s2a center-page"><p>Loading…</p></div>;

  if (!session) {
    if (route.kind !== 'home') {
      return (
        <div className="s2a center-page">
          <div>
            <h1>{route.kind === 'join' ? "You've been invited" : 'Sign in to open this app'}</h1>
            <p>{route.kind === 'join' ? 'Sign in with Google to join the app.' : 'This app is private to its members.'}</p>
            <button type="button" className="btn btn-primary" onClick={() => signIn(window.location.hash)}>
              Continue with Google
            </button>
          </div>
        </div>
      );
    }
    return (
      <Landing
        onSignIn={() => signIn('#/')}
        onUpload={async (file) => {
          await savePendingUpload(file);
          signIn('#/');
        }}
      />
    );
  }

  if (route.kind === 'join') return <JoinPage token={route.token} />;
  if (route.kind === 'app') return <AppPage key={route.id} appId={route.id} myId={session.user.id} />;
  return <Dashboard pendingFile={pendingFile} onPendingUsed={() => setPendingFile(null)} />;
}
