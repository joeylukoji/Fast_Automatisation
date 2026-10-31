// Champ libellé + formulaire simple, réutilisables dans toutes les apps.
export function Field({ label, ...input }) {
  return (
    <label className="os-field">
      <span>{label}</span>
      <input {...input} />
    </label>
  );
}

export function Form({ onSubmit, children, error, className = '' }) {
  return (
    <form className={`os-form ${className}`} onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      {children}
      {error && <p className="os-error">{error}</p>}
    </form>
  );
}
