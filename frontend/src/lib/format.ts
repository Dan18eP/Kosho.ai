/** Formateadores para números pequeños de costos/tokens (evita notación científica). */

export function fmtTokenPrice(price: number): string {
  if (!Number.isFinite(price)) return ''
  return price.toFixed(8).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '')
}

export function perMillion(price: number): string {
  return `$${(price * 1e6).toFixed(2)} / 1M tokens`
}

export function fmtMoney(n: number, currency = 'USD'): string {
  if (!Number.isFinite(n)) return '—'
  if (n === 0) return '$0'
  const abs = Math.abs(n)
  const digits = abs < 1e-4 ? 8 : abs < 1e-2 ? 6 : 4
  return n.toLocaleString('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  })
}
