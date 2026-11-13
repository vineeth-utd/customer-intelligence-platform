import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseNumericValue,
  formatCurrency,
  formatGrowthRate,
  formatScore,
  formatPercent,
  getCurrencySymbol,
} from './currency.ts';

describe('parseNumericValue', () => {
  it('parses numbers directly', () => {
    assert.equal(parseNumericValue(42), 42);
    assert.equal(parseNumericValue(-78.48), -78.48);
    assert.equal(parseNumericValue(0), 0);
  });

  it('parses numeric string representations from JSON Decimals', () => {
    assert.equal(parseNumericValue('-78.48'), -78.48);
    assert.equal(parseNumericValue('25.0'), 25.0);
    assert.equal(parseNumericValue('12495.54'), 12495.54);
    assert.equal(parseNumericValue(' 100.5 '), 100.5);
  });

  it('returns null for null, undefined, empty, or whitespace', () => {
    assert.equal(parseNumericValue(null), null);
    assert.equal(parseNumericValue(undefined), null);
    assert.equal(parseNumericValue(''), null);
    assert.equal(parseNumericValue('   '), null);
  });

  it('returns null for NaN and invalid strings without crashing', () => {
    assert.equal(parseNumericValue(NaN), null);
    assert.equal(parseNumericValue('not-a-number'), null);
    assert.equal(parseNumericValue({}), null);
    assert.equal(parseNumericValue([]), null);
  });
});

describe('formatCurrency', () => {
  it('formats numeric amounts safely in USD and EUR', () => {
    const usd = formatCurrency(12495.54, 'USD');
    assert.ok(usd.includes('12,495.54'));
    assert.ok(usd.includes('$'));

    const eur = formatCurrency(12495.54, 'EUR');
    assert.ok(eur.includes('12,495.54') || eur.includes('12.495,54'));
    assert.ok(eur.includes('€'));
  });

  it('safely handles JSON Decimal strings', () => {
    const usd = formatCurrency('12495.54', 'USD');
    assert.ok(usd.includes('12,495.54'));
    assert.ok(usd.includes('$'));

    const eur = formatCurrency('249.99', 'EUR');
    assert.ok(eur.includes('249.99') || eur.includes('249,99'));
    assert.ok(eur.includes('€'));
  });

  it('returns em-dash for null, undefined, empty, or invalid values', () => {
    assert.equal(formatCurrency(null), '—');
    assert.equal(formatCurrency(undefined), '—');
    assert.equal(formatCurrency(''), '—');
    assert.equal(formatCurrency('invalid'), '—');
  });
});

describe('formatGrowthRate', () => {
  it('formats positive and negative numbers with sign and percent', () => {
    assert.equal(formatGrowthRate(25.0), '+25.0%');
    assert.equal(formatGrowthRate(-78.48), '-78.5%');
    assert.equal(formatGrowthRate(0), '+0.0%');
  });

  it('safely formats string Decimals without calling string.toFixed', () => {
    assert.equal(formatGrowthRate('-78.48'), '-78.5%');
    assert.equal(formatGrowthRate('25.0'), '+25.0%');
    assert.equal(formatGrowthRate('0.0'), '+0.0%');
    assert.equal(formatGrowthRate('-100.0'), '-100.0%');
  });

  it('returns em-dash for null, undefined, empty, or invalid', () => {
    assert.equal(formatGrowthRate(null), '—');
    assert.equal(formatGrowthRate(undefined), '—');
    assert.equal(formatGrowthRate(''), '—');
    assert.equal(formatGrowthRate('abc'), '—');
  });
});

describe('formatScore', () => {
  it('formats numeric scores with requested precision', () => {
    assert.equal(formatScore(63.333, 1), '63.3');
    assert.equal(formatScore(100, 0), '100');
  });

  it('safely formats string Decimals', () => {
    assert.equal(formatScore('63.333', 1), '63.3');
    assert.equal(formatScore('100.0', 1), '100.0');
  });

  it('returns em-dash for null, undefined, or invalid', () => {
    assert.equal(formatScore(null), '—');
    assert.equal(formatScore(undefined), '—');
    assert.equal(formatScore('invalid'), '—');
  });
});

describe('formatPercent', () => {
  it('formats decimal fractions with multiplyBy100=true', () => {
    assert.equal(formatPercent(0.2814, 2), '28.14%');
    assert.equal(formatPercent(0.05, 1), '5.0%');
  });

  it('safely formats string Decimals', () => {
    assert.equal(formatPercent('0.2814', 2), '28.14%');
    assert.equal(formatPercent('0.05', 1), '5.0%');
  });

  it('formats whole percentages with multiplyBy100=false', () => {
    assert.equal(formatPercent(28.14, 1, false), '28.1%');
    assert.equal(formatPercent('28.14', 1, false), '28.1%');
  });

  it('returns em-dash for null, undefined, or invalid', () => {
    assert.equal(formatPercent(null), '—');
    assert.equal(formatPercent(undefined), '—');
    assert.equal(formatPercent('invalid'), '—');
  });
});

describe('getCurrencySymbol', () => {
  it('returns appropriate symbols', () => {
    assert.equal(getCurrencySymbol('USD'), '$');
    assert.equal(getCurrencySymbol('EUR'), '€');
    assert.equal(getCurrencySymbol('GBP'), '£');
  });
});

