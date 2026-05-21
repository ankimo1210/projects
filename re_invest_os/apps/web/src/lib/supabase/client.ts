/**
 * Supabase クライアント (ブラウザ側)
 * NEXT_PUBLIC_SUPABASE_URL と NEXT_PUBLIC_SUPABASE_ANON_KEY が設定されていない場合は null を返す。
 */
import { createBrowserClient } from "@supabase/ssr";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export function getSupabase() {
  if (!url || !key) return null;
  return createBrowserClient(url, key);
}

export const supabase = url && key ? createBrowserClient(url, key) : null;
