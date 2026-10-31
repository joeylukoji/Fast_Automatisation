import { useCallback, useState } from 'react';
import Window from './Window.jsx';
import Taskbar from './Taskbar.jsx';
import Icon from '../icons.jsx';

// Gestionnaire de fenêtres générique. `apps` = { id: { title, icon, w, h, render(props, ctx) } }.
// Chaque fenêtre a une clé unique (ex. « invoice:<id> ») pour éviter les doublons.
let zTop = 10;

export function useWindows() {
  const [wins, setWins] = useState([]);
  const open = useCallback((key, app, props = {}, title) => setWins((ws) => {
    const z = ++zTop;
    if (ws.some((w) => w.key === key)) return ws.map((w) => (w.key === key ? { ...w, props, title: title ?? w.title, minimized: false, z } : w));
    const n = ws.length;
    return [...ws, { key, app, props, title, x: 40 + 32 * (n % 8), y: 30 + 28 * (n % 8), z, minimized: false }];
  }), []);
  const patch = useCallback((key, p) => setWins((ws) => ws.map((w) => (w.key === key ? { ...w, ...(typeof p === 'function' ? p(w) : p) } : w))), []);
  const close = useCallback((key) => setWins((ws) => ws.filter((w) => w.key !== key)), []);
  const focus = useCallback((key) => patch(key, (w) => (w.z === zTop && !w.minimized ? {} : { z: ++zTop, minimized: false })), [patch]);
  return { wins, open, patch, close, focus };
}

export default function Desktop({ apps, launchers, wm, taskbarExtra, children }) {
  const top = wm.wins.filter((w) => !w.minimized).reduce((a, w) => (a && a.z > w.z ? a : w), null);
  const ctx = { open: wm.open, close: wm.close };
  return (
    <div className="os-desktop">
      <div className="os-wall" aria-hidden="true" />
      {children}
      <nav className="os-icons" aria-label="Applications">
        {launchers.map((id) => (
          // simple clic (accessible clavier) ou double-clic : ouvre l'app
          <button key={id} className="os-icon" onClick={() => wm.open(id, id)}>
            <span className="os-icon-tile"><Icon name={apps[id].icon} size={26} stroke={1.3} /></span>
            <span>{apps[id].title}</span>
          </button>
        ))}
      </nav>
      {wm.wins.map((w) => {
        const app = apps[w.app];
        const win = { ...w, title: w.title ?? app.title, icon: app.icon, w: app.w, h: app.h, focused: top?.key === w.key };
        return (
          <Window key={w.key} win={win} onFocus={() => wm.focus(w.key)} onClose={() => wm.close(w.key)}
            onMinimize={() => wm.patch(w.key, { minimized: true })} onMove={(x, y) => wm.patch(w.key, { x, y })}>
            {app.render(w.props, ctx)}
          </Window>
        );
      })}
      <Taskbar wins={wm.wins} apps={apps} activeKey={top?.key} extra={taskbarExtra}
        onClick={(w) => (top?.key === w.key ? wm.patch(w.key, { minimized: true }) : wm.focus(w.key))} />
    </div>
  );
}
