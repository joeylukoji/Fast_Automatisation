// Formats monétaires et dates partagés par les apps ERP.
export const DEFAULT_RATE = 2300;
export const usd = (n) => `${Number(n ?? 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} $`;
export const cdf = (n) => `${Math.round(Number(n ?? 0)).toLocaleString('fr-FR')} FC`;
export const toCdf = (u, rate = DEFAULT_RATE) => Math.round((u * rate) / 100) * 100;
export const date = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');
export const STATUS = { sent: ['envoyée', 'st-success'], failed: ['échec', 'st-error'], not_sent: ['non envoyée', 'st-idle'] };
