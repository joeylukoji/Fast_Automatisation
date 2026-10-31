"""Construit le jeu synthétique annoté (prompt → intention).

Anti-fuite : chaque composant de phrase a 6 formulations ; les formulations 0–3 servent
uniquement à l'entraînement, la 4 à la validation, la 5 au test. Une phrase de test n'utilise donc
aucune formulation vue à l'entraînement. Graine fixe → sortie déterministe.
Usage : python build_dataset.py
"""
import json, random
from pathlib import Path

SEED = 42
P = {  # composant → 6 formulations (index = partition : 0-3 train, 4 val, 5 test)
 "tg": ["envoie un message Telegram", "préviens-moi sur Telegram", "poste sur le canal Telegram {chat}",
        "notifie le groupe telegram {chat}", "écris dans mon chat Telegram", "balance une alerte via mon bot telegram"],
 "gm": ["envoie un e-mail à {mail}", "préviens {mail} par mail", "écris un courriel à {mail}",
        "notifie {mail} par Gmail", "expédie un mail à {mail}", "fais partir un message électronique vers {mail}"],
 "both": ["envoie-le sur Telegram et par e-mail à {mail}", "préviens-moi sur Telegram et aussi par mail à {mail}",
          "notifie à la fois Telegram et {mail}", "poste sur Telegram puis envoie un courriel à {mail}",
          "diffuse sur telegram ainsi qu'à {mail} par gmail", "double alerte : bot telegram et message électronique à {mail}"],
 "llm": ["résume", "fais un résumé de", "synthétise", "demande à Gemma de résumer", "condense", "rédige une synthèse courte de"],
 "http": ["récupère la page {url}", "appelle l'API {url}", "télécharge le contenu de {url}",
          "fais une requête GET sur {url}", "interroge {url}", "va chercher les données de {url}"],
 "cond": ["si le statut vaut {code}", "seulement si la réponse est {code}", "quand le code HTTP est {code}",
          "uniquement si le serveur répond {code}", "à condition que le code retour soit {code}", "dans le cas où on obtient un {code}"],
 "else": ["sinon", "autrement", "dans le cas contraire", "sinon alors", "si ce n'est pas le cas", "en cas d'échec"],
 "txt": ["ce texte", "le message reçu", "le contenu saisi", "mon texte", "cette note", "le paragraphe fourni"],
 "go": ["", "Quand je clique, ", "Au lancement, ", "Déclenche manuellement et ", "Dès que je lance, ", "À chaque démarrage manuel, "],
}

def sentence(intent, v, r):
    g = lambda k: P[k][v]
    send = {"telegram": g("tg"), "gmail": g("gm"), "telegram_gmail": g("both")}
    if intent in send: s = send[intent] + " avec " + g("txt")
    elif intent == "llm": s = f"{g('llm')} {g('txt')}"
    elif intent.startswith("llm_"): s = f"{g('llm')} {g('txt')} puis {send[intent[4:]]}"
    elif intent == "http": s = g("http")
    elif intent.startswith("http_llm_"): s = f"{g('http')}, {g('llm')} le résultat et {send[intent[9:]]}"
    elif intent == "http_cond_telegram_gmail": s = f"{g('http')} ; {g('cond')}, {g('tg')}, {g('else')} {g('gm')}"
    elif intent.startswith("http_cond_"): s = f"{g('http')} et {g('cond')}, {send[intent[10:]]}"
    else: s = f"{g('http')} puis {send[intent[5:]]}"
    s = g("go") + s
    return s.format(url=r.choice(["https://api.meteo.fr/paris", "https://status.monsite.com", "https://example.org/rss", "http://localhost:3000/health"]),
                    mail=r.choice(["alice@exemple.fr", "equipe@startup.io", "moi@gmail.com"]),
                    chat=r.choice(["123456", "-100987654", "424242"]), code=r.choice(["200", "404", "500", "503"]))

def main():
    import sys; sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
    from app.ai.local_model import INTENTS
    r = random.Random(SEED); rows = []
    for split, variants, n in (("train", [0, 1, 2, 3], 10), ("val", [4], 6), ("test", [5], 6)):
        for intent in INTENTS:
            for v in variants:
                seen = set()
                for _ in range(n * 3):
                    # mélange des formulations : chaque composant tire sa propre variante dans la partition
                    vs = {k: r.choice(variants) for k in P}
                    s = sentence_mixed(intent, vs, r)
                    if s not in seen: seen.add(s); rows.append({"prompt": s, "intent": intent, "split": split})
                    if len(seen) >= n: break
    out = Path(__file__).parent / "data" / "synthetic.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n")
    print(out, len(rows))

def sentence_mixed(intent, vs, r):
    saved = {k: P[k][:] for k in P}
    try:
        for k in P: P[k] = [saved[k][vs[k]]] * 6
        return sentence(intent, 0, r)
    finally:
        P.update(saved)

if __name__ == "__main__": main()
