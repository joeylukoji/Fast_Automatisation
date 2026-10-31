import { useRef } from 'react';
import Icon from '../icons.jsx';

// Fenêtre déplaçable par sa barre de titre ; le focus remonte son z-index.
export default function Window({ win, onFocus, onClose, onMinimize, onMove, children }) {
  const drag = useRef(null);
  const down = (e) => {
    if (e.button !== 0 || e.target.closest('button')) return;
    onFocus();
    drag.current = { dx: e.clientX - win.x, dy: e.clientY - win.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const move = (e) => {
    if (!drag.current) return;
    onMove(Math.max(0, e.clientX - drag.current.dx), Math.max(0, e.clientY - drag.current.dy));
  };
  const up = () => { drag.current = null; };
  return (
    <section className={`os-win ${win.focused ? 'focused' : ''}`} hidden={win.minimized}
      style={{ left: win.x, top: win.y, width: win.w, height: win.h, zIndex: win.z }}
      onPointerDown={onFocus} role="dialog" aria-label={win.title}>
      <header className="os-titlebar" onPointerDown={down} onPointerMove={move} onPointerUp={up}>
        <Icon name={win.icon} size={14} />
        <span className="os-title">{win.title}</span>
        <button className="os-tb-btn" onClick={onMinimize} aria-label="Réduire"><Icon name="minus" size={13} /></button>
        <button className="os-tb-btn close" onClick={onClose} aria-label="Fermer"><Icon name="x" size={13} /></button>
      </header>
      <div className="os-body">{children}</div>
    </section>
  );
}
