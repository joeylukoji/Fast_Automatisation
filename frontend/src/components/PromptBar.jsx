import { useState } from 'react';
import { useStore } from '../store';

export default function PromptBar() {
  const [prompt, setPrompt] = useState('');
  const generate = useStore((s) => s.generate);
  const run = useStore((s) => s.run);
  const busy = useStore((s) => s.busy);
  const hasNodes = useStore((s) => s.nodes.length > 0);

  const submit = (e) => {
    e.preventDefault();
    if (prompt.trim()) generate(prompt.trim());
  };

  const runForReal = () => {
    const ok = window.confirm(
      'Exécuter ce workflow pour de vrai ?\n\nLes blocs Telegram, Gmail et HTTP vont réellement envoyer des messages ou des requêtes.',
    );
    if (ok) run(false);
  };

  return (
    <form className="promptbar" onSubmit={submit}>
      <input
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Décrivez votre automatisation… ex. « Envoie-moi un message Telegram quand une page répond 200 »"
        disabled={busy !== null}
      />
      <button type="submit" disabled={busy !== null || !prompt.trim()}>
        {busy === 'generate' ? 'Génération…' : 'Générer'}
      </button>
      <button type="button" className="secondary" disabled={busy !== null || !hasNodes} onClick={() => run(true)}>
        Simuler
      </button>
      <button type="button" className="danger" disabled={busy !== null || !hasNodes} onClick={runForReal}>
        Exécuter
      </button>
    </form>
  );
}
