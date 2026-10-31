import { createContext, useContext, useMemo } from 'react';

// Specs déployées par le générateur (docs/app-builder-contract.md), partagées via contexte.
export const SpecContext = createContext({});
export const useSpecs = () => useContext(SpecContext);
export const useSpec = (app) => useContext(SpecContext)[app] ?? {};

// Libellé de la spec, sinon texte actuel en repli.
export function useLabels(app) {
  const labels = useSpec(app).labels ?? {};
  return (key, fallback) => (typeof labels[key] === 'string' && labels[key].trim() ? labels[key] : fallback);
}

// Filtre défensif + isolation : « .app-root » → « .app-root.app-<app> ».
export function scopeCss(app, lines) {
  if (!Array.isArray(lines)) return '';
  return lines
    .filter((l) => typeof l === 'string' && l.trimStart().startsWith('.app-root') && !/<|@import|url\(/i.test(l))
    .map((l) => l.trimStart().replace(/^\.app-root/, `.app-root.app-${app}`))
    .join('\n');
}

const HEX = /^#[0-9a-f]{6}$/i;

// Racine d'une app : classe d'isolation, variables de thème et CSS de la spec.
export function AppRoot({ app, className = '', children }) {
  const spec = useSpec(app);
  const css = useMemo(() => scopeCss(app, spec.css), [app, spec.css]);
  const { accent, background } = spec.theme ?? {};
  const style = {};
  if (HEX.test(accent ?? '')) style['--app-accent'] = accent;
  if (HEX.test(background ?? '')) style['--app-bg'] = background;
  return (
    <div className={`app-root app-${app} ${className}`} style={style}>
      {css && <style>{css}</style>}
      {children}
    </div>
  );
}
