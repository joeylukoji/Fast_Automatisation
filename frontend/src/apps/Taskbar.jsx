import { useEffect, useState } from 'react';
import Icon from '../icons.jsx';

// Barre des tâches : accueil, fenêtres ouvertes, lien Studio, horloge.
// `extra` : actions supplémentaires (ex. Régénérer / Réinitialiser la démo).
export default function Taskbar({ wins, apps, activeKey, onClick, extra }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 15000); return () => clearInterval(t); }, []);
  return (
    <footer className="os-taskbar">
      <a href="#/" className="os-start" title="Accueil Fast Automatisation"><span className="logo-mark" /></a>
      <div className="os-tasks">
        {wins.map((w) => (
          <button key={w.key} className={`os-task ${activeKey === w.key ? 'active' : ''} ${w.minimized ? 'min' : ''}`} onClick={() => onClick(w)}>
            <Icon name={apps[w.app].icon} size={14} /> <span>{w.title ?? apps[w.app].title}</span>
          </button>
        ))}
      </div>
      {extra}
      <a href="#/studio" className="os-task link"><Icon name="grid" size={14} /> <span>Studio</span></a>
      <time className="os-clock mono">
        {now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
        <small>{now.toLocaleDateString('fr-FR')}</small>
      </time>
    </footer>
  );
}
