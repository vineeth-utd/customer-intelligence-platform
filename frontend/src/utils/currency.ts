/**
 * Safely parses a value that may arrive from JSON as a number, numeric string (e.g. Decimal),
 * or null/undefined.
 *
 * Returns null if the value is null, undefined, empty/whitespace string, or not a valid number.
 */
export function parseNumericValue(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (typeof value === 'number') {
    return isNaN(value) ? null : value;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed === '') return null;
    const parsed = Number(trimmed);
    return isNaN(parsed) ? null : parsed;
  }
  return null;
}

/**
 * Formats a monetary amount in its authoritative currency without conversion.
 * Safely accepts number or string representation from JSON Decimals.
 */
export function formatCurrency(
  amount: number | string | null | undefined,
  currency: string = 'USD'
): string {
  const num = parseNumericValue(amount);
  if (num === null) {
    return '—';
  }

  const validCurrency = currency && currency.trim() ? currency.toUpperCase() : 'USD';

  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: validCurrency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    // Fallback if currency string is not recognized by Intl
    return `${validCurrency} ${num.toFixed(2)}`;
  }
}

/**
 * Returns the display symbol for a given currency code (e.g. '$' for USD, '€' for EUR).
 */
export function getCurrencySymbol(currency: string = 'USD'): string {
  const validCurrency = currency && currency.trim() ? currency.toUpperCase() : 'USD';

  try {
    const parts = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: validCurrency,
    }).formatToParts(0);
    const symbolPart = parts.find((p) => p.type === 'currency');
    return symbolPart ? symbolPart.value : validCurrency;
  } catch {
    return validCurrency;
  }
}

/**
 * Formats a period-over-period growth percentage.
 * Backend returns values already multiplied by 100 (e.g. 25.0 for +25%, -78.5 for -78.5%, -100.0 for -100%).
 * Safely normalizes both numeric strings from Decimal serialization and numbers.
 */
export function formatGrowthRate(growthPct: number | string | null | undefined): string {
  const num = parseNumericValue(growthPct);
  if (num === null) {
    return '—';
  }
  const prefix = num >= 0 ? '+' : '';
  return `${prefix}${num.toFixed(1)}%`;
}

/**
 * Formats health or index scores with explicit precision.
 * Safely handles strings from API serialization, numbers, and nulls.
 */
export function formatScore(
  score: number | string | null | undefined,
  precision: number = 1
): string {
  const num = parseNumericValue(score);
  if (num === null) {
    return '—';
  }
  return num.toFixed(precision);
}

/**
 * Formats percentage metrics (e.g. conversion rate, adoption rate).
 * If multiplyBy100 is true (default), converts 0.2814 -> 28.1%.
 */
export function formatPercent(
  rate: number | string | null | undefined,
  precision: number = 1,
  multiplyBy100: boolean = true
): string {
  const num = parseNumericValue(rate);
  if (num === null) {
    return '—';
  }
  const val = multiplyBy100 ? num * 100 : num;
  return `${val.toFixed(precision)}%`;
}
