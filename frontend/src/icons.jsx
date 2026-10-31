// Icônes SVG au trait (24×24), sans dépendance.
const P = {
  trigger_manual: ['M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z', 'M13 13l6 6'],
  http_request: ['M2 12h20', 'M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z', 'C12 12 10'],
  llm: ['M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z', 'M19 3v4', 'M21 5h-4'],
  condition: ['M16 3h5v5', 'M8 3H3v5', 'M12 22v-8.3a4 4 0 0 0-1.17-2.87L3 3', 'm15 9 6-6'],
  telegram_send: ['m22 2-7 20-4-9-9-4Z', 'M22 2 11 13'],
  gmail_send: ['R2 4 20 16 2', 'm22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'],
  plus: ['M12 5v14', 'M5 12h14'],
  trash: ['M3 6h18', 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6', 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'],
  play: ['m6 3 14 9-14 9V3z'],
  flask: ['M9 3h6', 'M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3', 'M7 15h10'],
  save: ['M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z', 'M17 21v-8H7v8', 'M7 3v5h8'],
  x: ['M18 6 6 18', 'm6 6 12 12'],
  check: ['M20 6 9 17l-5-5'],
  alert: ['M12 9v4', 'M12 17h.01', 'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z'],
  arrow: ['M5 12h14', 'm12 5 7 7-7 7'],
  search: ['C11 11 8', 'm21 21-4.3-4.3'],
  folder: ['M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z'],
  bolt: ['M13 2 3 14h9l-1 8 10-12h-9l1-8z'],
  chevron: ['m6 9 6 6 6-6'],
};

export default function Icon({ name, size = 18, stroke = 1.5, className }) {
  const parts = P[name] ?? P.bolt;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}
      strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {parts.map((d, i) => {
        if (d.startsWith('C')) { const [cx, cy, r] = d.slice(1).trim().split(' ').map(Number); return <circle key={i} cx={cx} cy={cy} r={r} />; }
        if (d.startsWith('R')) { const [x, y, w, h, rx] = d.slice(1).trim().split(' ').map(Number); return <rect key={i} x={x} y={y} width={w} height={h} rx={rx} />; }
        return <path key={i} d={d} />;
      })}
    </svg>
  );
}
