import { createClient } from '@supabase/supabase-js';

/**
 * supabaseClient.js — Singleton Supabase browser client
 *
 * Reads VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY from the environment.
 * Used for authentication (login/signup/session) on the frontend.
 * This is the anon/public key — safe to expose in the browser.
 */

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    'Missing Supabase environment variables. ' +
    'Ensure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in frontend/.env.local'
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
