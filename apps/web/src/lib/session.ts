import { create } from 'zustand';
import type { Role, Region } from '@bai/types';

/**
 * Tenant context for the UI.
 *
 * Locale, currency and timezone come from the ORG record, never from the
 * browser. A German user working for a Japanese tenant sees JPY in ja-JP
 * formatting, because that is the tenant's data — not their device's guess.
 */
export interface Session {
  orgId: string | null;
  userId: string | null;
  role: Role | null;
  region: Region | null;
  locale: string;
  currency: string;
  timezone: string;
  permissions: readonly string[];
}

export interface SessionStore extends Session {
  set: (s: Partial<Session>) => void;
  clear: () => void;
}

const EMPTY: Session = {
  orgId: null, userId: null, role: null, region: null,
  locale: 'en-GB', currency: 'GBP', timezone: 'UTC', permissions: [],
};

export const useSession = create<SessionStore>((set) => ({
  ...EMPTY,
  set: (s) => { set(s); },
  clear: () => { set(EMPTY); },
}));
