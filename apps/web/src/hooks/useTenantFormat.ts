import { useCallback } from 'react';
import { formatMoney, formatDate, formatDateTime, type Money } from '@bai/ui';

import { useSession } from '../lib/session';

/**
 * Formatting bound to the TENANT, not the browser.
 *
 * `navigator.language` is the device's preference and is wrong here: a record's
 * money and dates belong to the organisation that owns them.
 */
export function useTenantFormat() {
  const locale = useSession((s) => s.locale);
  const timezone = useSession((s) => s.timezone);

  return {
    money: useCallback((m: Money) => formatMoney(m, locale), [locale]),
    date: useCallback((iso: string) => formatDate(iso, locale, timezone), [locale, timezone]),
    dateTime: useCallback(
      (iso: string) => formatDateTime(iso, locale, timezone),
      [locale, timezone],
    ),
  };
}
