import { useEffect, useRef, useState } from 'react';
import Icon from '../icons.jsx';
import { api } from '../api';

const go = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
const SOURCE = { gemma: 'Gemma 4', local: 'Modèle local', mock: 'Démo (mock)' };

// Sphère de particules en Canvas 2D (points répartis sur une sphère de Fibonacci + orbites).
function ParticleSphere() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas.getContext('2d');
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const N = 900;
    const pts = Array.from({ length: N }, (_, i) => {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const t = i * Math.PI * (3 - Math.sqrt(5));
      return [Math.cos(t) * r, y, Math.sin(t) * r, Math.random() * Math.PI * 2];
    });
    let w, h, dpr, raf, time = 0, mx = 0, my = 0;
    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const onMove = (e) => { mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5; };
    const draw = () => {
      time += 0.004;
      ctx.clearRect(0, 0, w, h);
      const wide = w >= 1024;
      const cx = wide ? w * 0.7 : w * 0.5, cy = wide ? h * 0.5 : h * 0.24;
      const R = Math.min(w, h) * (wide ? 0.3 : 0.3);
      const ay = time + mx * 0.6, ax = 0.35 + my * 0.4;
      const [sy, cy2, sx, cx2] = [Math.sin(ay), Math.cos(ay), Math.sin(ax), Math.cos(ax)];
      for (const [x0, y0, z0, ph] of pts) {
        const n = 1 + Math.sin(ph + time * 6 + y0 * 3) * 0.06; // « respiration »
        const x = x0 * cy2 + z0 * sy, z1 = -x0 * sy + z0 * cy2;
        const y = y0 * cx2 - z1 * sx, z = y0 * sx + z1 * cx2;
        const depth = (z + 1) / 2;
        ctx.fillStyle = `rgba(28,25,23,${0.12 + depth * 0.55})`;
        ctx.beginPath();
        ctx.arc(cx + x * R * n, cy + y * R * n, 0.5 + depth * 1.3, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.strokeStyle = 'rgba(120,53,15,0.16)';
      ctx.lineWidth = 1;
      [[1.2, 0.28, 0], [1.16, 0.5, 0.6], [1.3, 0.18, -0.5]].forEach(([k, flat, rot], i) => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, R * k, R * k * flat, rot + time * (i + 1) * 0.3, 0, Math.PI * 2);
        ctx.stroke();
      });
      if (!reduce) raf = requestAnimationFrame(draw);
    };
    resize(); draw();
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', onMove);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); window.removeEventListener('mousemove', onMove); };
  }, []);
  return <canvas ref={ref} className="sphere" aria-hidden="true" />;
}

function EnginePanel() {
  const [health, setHealth] = useState(null);
  const [nodes, setNodes] = useState(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(false));
    api.nodes().then(setNodes).catch(() => setNodes([]));
  }, []);
  const live = health && health.status === 'ok';
  return (
    <aside className="glass engine fade" style={{ animationDelay: '.5s' }}>
      <header><span className="serif-i">Moteur Kernel</span></header>
      <div className="engine-body">
        <div className="engine-row"><span>GÉNÉRATEUR</span><span>{live ? SOURCE[health.generator] ?? 'non configuré' : '—'}</span></div>
        <div className="engine-row"><span>SECOURS</span><span>{live && health.fallback ? 'modèle local' : '—'}</span></div>
        <div className="engine-row"><span>BLOCS</span><span>{nodes ? nodes.length : '—'}</span></div>
        <div className="engine-chain">
          {['trigger_manual', 'http_request', 'condition', 'telegram_send'].map((k, i) => (
            <span key={k} className="engine-step">{i > 0 && <span className="engine-link" />}<span className="engine-node"><Icon name={k} size={15} /></span></span>
          ))}
        </div>
        <div className="engine-row foot">
          <span>API</span>
          <span className={`live ${live ? 'on' : 'off'}`}>{health === null ? '…' : live ? 'EN LIGNE' : 'HORS LIGNE'}<i /></span>
        </div>
      </div>
    </aside>
  );
}

const BLOCKS = [
  ['trigger_manual', 'Déclencheur manuel', 'Point de départ du workflow, lancé à la main.'],
  ['http_request', 'Requête HTTP', 'Appelle une URL et renvoie statut, JSON et texte.'],
  ['llm', 'LLM (Gemma)', 'Résume, reformule ou analyse un texte.'],
  ['condition', 'Condition', 'Compare deux valeurs et choisit la branche vrai / faux.'],
  ['telegram_send', 'Telegram', 'Envoie un message via un bot.'],
  ['gmail_send', 'Gmail', 'Envoie un e-mail depuis le compte configuré.'],
];

const PIPELINE = [
  ['Prompt', 'Une phrase en français'],
  ['Gemma 4', 'ou modèle local hors-ligne'],
  ['Validation', 'types, paramètres, cycles — réparation auto'],
  ['Éditeur', 'graphe modifiable'],
  ['Simulation', 'aucun effet de bord'],
  ['Exécution', 'après approbation'],
];

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', on);
    return () => window.removeEventListener('scroll', on);
  }, []);

  return (
    <div className="landing">
      <div className="grid-bg" aria-hidden="true" />
      <ParticleSphere />

      <nav className={`glass nav ${scrolled ? 'compact' : ''}`}>
        <div className="wrap nav-in">
          <a href="#/" className="brand"><span className="logo-mark" /><span className="brand-name">Kernel</span></a>
          <div className="nav-links">
            <button onClick={() => go('projet')}>Le projet</button>
            <button onClick={() => go('fonctionnement')}>Fonctionnement</button>
            <button onClick={() => go('blocs')}>Blocs</button>
            <button onClick={() => go('recherche')}>Recherche</button>
          </div>
          <div className="nav-cta">
            <a href="#/apps" className="nav-apps">Applications</a>
            <a href="#/studio" className="pill-btn">Ouvrir le studio</a>
          </div>
        </div>
      </nav>

      <main>
        <section className="wrap hero">
          <div className="hero-text fade" style={{ animationDelay: '.2s' }}>
            <div className="eyebrow-line"><span /><em>AUTOMATISATION — LANGAGE NATUREL</em></div>
            <h1 className="display">Décrivez-le.<br /><span className="serif-i light">Kernel l'automatise.</span></h1>
            <p className="lead">
              Kernel transforme une phrase en workflow visuel : Gemma 4 le génère, le moteur le vérifie et le répare,
              vous l'ajustez dans l'éditeur, le simulez sans risque, puis l'exécutez seulement après votre accord.
            </p>
            <div className="cta-row">
              <a href="#/studio" className="btn-hero">OUVRIR LE STUDIO <Icon name="arrow" size={16} /></a>
              <span className="rule" />
              <button className="serif-i link-muted" onClick={() => go('fonctionnement')}>Comment ça marche</button>
            </div>
            <div className="meta mono">
              <span>PROJET : KERNEL — HACKATHON</span>
              <span>STACK : FASTAPI · REACT FLOW · GEMMA 4</span>
            </div>
          </div>
          <EnginePanel />
        </section>

        <section id="projet" className="band shift">
          <div className="wrap">
            <div className="center"><span className="tag">LE CHANGEMENT</span></div>
            <div className="vs">
              <div className="vs-col old">
                <h3 className="serif-i">« Aujourd'hui »</h3>
                <div className="vs-grid">
                  <span><Icon name="search" size={22} /> APPRENDRE UN OUTIL</span>
                  <span><Icon name="condition" size={22} /> ASSEMBLER À LA MAIN</span>
                  <span><Icon name="alert" size={22} /> SYNTAXE À DEVINER</span>
                  <span><Icon name="bolt" size={22} /> TESTER EN PRODUCTION</span>
                </div>
                <p>Les outils d'automatisation sont puissants mais exigeants. Un LLM peut décrire une automatisation, mais sa sortie brute n'est ni vérifiable ni sûre à exécuter.</p>
              </div>
              <div className="vs-mid"><span>VS</span></div>
              <div className="vs-col new">
                <h3 className="serif-i">« Avec Kernel »</h3>
                <div className="vs-grid rust">
                  <span><Icon name="llm" size={22} /> UNE PHRASE</span>
                  <span><Icon name="check" size={22} /> WORKFLOW VALIDE</span>
                  <span><Icon name="flask" size={22} /> SIMULATION SANS RISQUE</span>
                  <span><Icon name="play" size={22} /> EXÉCUTION APPROUVÉE</span>
                </div>
                <p>Vous décrivez le besoin. Kernel produit un graphe vérifié que vous voyez, modifiez et testez avant qu'il n'agisse sur le monde réel.</p>
              </div>
            </div>
          </div>
        </section>

        <section id="fonctionnement" className="wrap section">
          <span className="kicker">POURQUOI KERNEL</span>
          <div className="two">
            <h2 className="display md">Une phrase.<br /><span className="serif-i muted-ink">Un workflow vérifié.</span></h2>
            <p className="lead lg">
              Le modèle ne produit jamais directement une action : il propose un graphe au format Kernel. Chaque proposition
              passe par le moteur de validation ; en cas d'erreur, les messages sont renvoyés au modèle pour qu'il corrige
              (jusqu'à deux réparations). Ce qui arrive dans l'éditeur est donc toujours exécutable.
            </p>
          </div>
          <div className="glass pipeline">
            {PIPELINE.map(([t, s], i) => (
              <div key={t} className="pipe-step">
                {i > 0 && <Icon name="arrow" size={18} className="pipe-arrow" />}
                <div className={`pipe-box ${t === 'Validation' ? 'dark' : ''}`}>
                  <span className="mono">{String(i + 1).padStart(2, '0')}</span>
                  <span className="serif-i">{t}</span>
                  <small>{s}</small>
                </div>
              </div>
            ))}
          </div>
          <div className="cards3">
            {[
              ['01', 'VALIDE PAR CONSTRUCTION', 'Types de blocs, paramètres obligatoires, branches, déclencheur et absence de cycle sont vérifiés avant tout affichage.'],
              ['02', 'SIMULÉ AVANT D\'AGIR', 'Le test exécute la logique et montre ce que chaque bloc aurait envoyé, sans envoyer de message ni appeler d\'API.'],
              ['03', 'UN BLOC = UN SCHÉMA', 'Le même schéma alimente le prompt du modèle, la validation et le formulaire de l\'éditeur. Ajouter un bloc ne touche à rien d\'autre.'],
            ].map(([n, t, d]) => (
              <div key={n} className="glass card top">
                <div className="card-head"><span className="mono muted">{n}</span><span className="mono">{t}</span></div>
                <p>{d}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="blocs" className="band">
          <div className="wrap">
            <div className="center head">
              <span className="kicker">LA PLATEFORME</span>
              <h2 className="display md">Six blocs.<br /><span className="serif-i muted-ink">Des combinaisons infinies.</span></h2>
            </div>
            <div className="blocks">
              {BLOCKS.map(([k, t, d], i) => (
                <div key={k} className="glass card lift">
                  <div className="block-icon"><Icon name={k} size={22} /></div>
                  <span className="mono num">{String(i + 1).padStart(2, '0')}</span>
                  <h4 className="mono">{t.toUpperCase()}</h4>
                  <p>{d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="recherche" className="wrap section">
          <span className="kicker">MESURÉ, PAS PROMIS</span>
          <div className="two">
            <div className="glass quote">
              <span className="bar" />
              <h3 className="serif-i big">« Un secours hors-ligne, évalué honnêtement »</h3>
              <span className="mono muted">— experiments/evaluation_report.md</span>
              <p>
                Quand Gemma 4 n'est pas joignable, un petit classifieur entraîné pour le projet reconnaît l'une des 14
                structures de workflow et construit le graphe. Les chiffres ci-contre sont mesurés sur des phrases écrites
                à la main, jamais vues pendant l'entraînement. L'évaluation de Gemma 4 reste à faire.
              </p>
            </div>
            <div className="stats">
              <div><span className="stat">93 %</span><span className="mono muted">Bonnes structures sur 42 phrases manuelles (IC 95 % : 83–100 %)</span></div>
              <div><span className="stat">100 %</span><span className="mono muted">Workflows générés valides et simulables</span></div>
              <div><span className="stat">0,2 ms</span><span className="mono muted">Par prédiction, sur CPU, sans dépendance</span></div>
            </div>
          </div>
        </section>

        <section className="final">
          <div className="grid-bg soft" aria-hidden="true" />
          <div className="final-in">
            <span className="logo-mark big" />
            <h2 className="display md">Prêt à automatiser<br /><span className="serif-i muted-ink">en une phrase ?</span></h2>
            <p className="lead">Ouvrez le studio, décrivez votre besoin, puis testez le workflow avant de l'exécuter.</p>
            <div className="cta-row center-row">
              <a href="#/studio" className="btn-hero">OUVRIR LE STUDIO <Icon name="arrow" size={16} /></a>
              <button className="mono underline" onClick={() => go('fonctionnement')}>Revoir le fonctionnement</button>
            </div>
          </div>
          <span className="mono muted footer-note">KERNEL — AUTOMATISATION EN LANGAGE NATUREL</span>
        </section>
      </main>
    </div>
  );
}
