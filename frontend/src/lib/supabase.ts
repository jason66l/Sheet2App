import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

/** False until frontend/.env.local has the Supabase URL and publishable key. */
export const supabaseConfigured = Boolean(url && key);
if (!supabaseConfigured) {
  console.error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_KEY. Copy frontend/.env.example to frontend/.env.local.');
}

/** Browser Supabase client. Used only for sign-in; all data goes through our FastAPI backend. */
export const supabase = createClient(url || 'http://supabase-not-configured.invalid', key || 'missing-key');

export function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin,
      // Always show Google's account picker, so switching accounts (or signing in on camera) is visible.
      queryParams: { prompt: 'select_account' },
    },
  });
}

export function signOut() {
  return supabase.auth.signOut();
}