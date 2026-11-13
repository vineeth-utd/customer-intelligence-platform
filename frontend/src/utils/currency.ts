/**
 * Formats a monetary amount in its authoritative currency without conversion.
 */
export function formatCurrency(
  amount: number | null | undefined,
  currency: string = 'USD'
): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '—';
  }

  const validCurrency = currency && currency.trim() ? currency.toUpperCase() : 'USD';

  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: validCurrency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    // Fallback if currency string is not recognized by Intl
    return `${validCurrency} ${amount.toFixed(2)}`;
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
 */
export function formatGrowthRate(growthPct: number | null | undefined): string {
  if (growthPct === null || growthPct === undefined || isNaN(growthPct)) {
    return '—';
  }
  const prefix = growthPct >= 0 ? '+' : '';
  return `${prefix}${growthPct.toFixed(1)}%`;
}

