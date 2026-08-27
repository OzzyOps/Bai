/**
 * Formatting shared by every product.
 *
 * Money is integer minor units plus an ISO 4217 code. Nothing here accepts a
 * float, and nothing assumes two decimal places — JPY has none, KWD has three.
 */

/** ISO 4217 minor-unit exponents that are NOT 2. Mirrors bai_platform.money. */
const EXPONENTS: Record<string, number> = {
  JPY: 0, KRW: 0, VND: 0, CLP: 0, ISK: 0, PYG: 0, RWF: 0, UGX: 0,
  VUV: 0, XAF: 0, XOF: 0, XPF: 0, DJF: 0, GNF: 0, KMF: 0,
  BHD: 3, IQD: 3, JOD: 3, KWD: 3, LYD: 3, OMR: 3, TND: 3,
};

export function exponentFor(currency: string): number {
  return EXPONENTS[currency.toUpperCase()] ?? 2;
}

export interface Money {
  readonly minor: number;
  readonly currency: string;
}

/**
 * Render money in the tenant's locale.
 *
 * The tenant's locale and currency are independent: a Brazilian tenant may hold
 * a USD contract. Never derive one from the other.
 */
export function formatMoney(money: Money, locale: string): string {
  const exponent = exponentFor(money.currency);
  const major = money.minor / 10 ** exponent;
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: money.currency,
      minimumFractionDigits: exponent,
      maximumFractionDigits: exponent,
    }).format(major);
  } catch {
    // An unknown currency code must still render something truthful.
    return `${major.toFixed(exponent)} ${money.currency}`;
  }
}

export function formatDate(iso: string, locale: string, timeZone: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium', timeZone,
  }).format(new Date(iso));
}

export function formatDateTime(iso: string, locale: string, timeZone: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium', timeStyle: 'short', timeZone,
  }).format(new Date(iso));
}
