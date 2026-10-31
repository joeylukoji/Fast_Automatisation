// Table générique : columns = [{ key, label, render?, align? }].
export default function DataTable({ columns, rows, onRowClick, empty = 'Aucune donnée.', rowKey = (r) => r.id }) {
  if (!rows) return <p className="os-empty muted">Chargement…</p>;
  if (!rows.length) return <p className="os-empty muted">{empty}</p>;
  return (
    <div className="os-table-wrap">
      <table className="os-table">
        <thead><tr>{columns.map((c) => <th key={c.key} style={{ textAlign: c.align }}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)} onClick={onRowClick && (() => onRowClick(r))} className={onRowClick ? 'clickable' : ''}>
              {columns.map((c) => <td key={c.key} style={{ textAlign: c.align }}>{c.render ? c.render(r) : r[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
