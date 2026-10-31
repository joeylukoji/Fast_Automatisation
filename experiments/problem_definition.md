# Définition du problème

- **Question** : peut-on produire, sans LLM, un workflow Kernel correct à partir d'un prompt français, assez bien pour une démo hors-ligne et comme baseline face à Gemma 4 ?
- **Reformulation** : la génération libre est décomposée en (1) **classification d'intention** parmi 14 structures de workflow (`local_model.INTENTS`), puis (2) **construction déterministe** du workflow + extraction de paramètres (URL, e-mail, chat id, code HTTP) par expressions régulières.
- **Cible** : l'intention (14 classes, une par prompt). **Entrée** : le texte du prompt.
- **Nature** : classification supervisée multi-classe de textes courts.
- **Utilisateurs / contraintes** : utilisateur de Kernel ; CPU uniquement, aucun GPU (vérifié : `nvidia-smi` absent), pas d'accès au modèle Gemma 4 dans cet environnement, inférence sans dépendance lourde, latence < 50 ms.
- **Métriques** : exactitude (+ IC 95 % bootstrap) et F1 macro sur l'intention ; F1 sur l'ensemble des types de blocs (erreur partielle) ; taux de workflows valides (`engine.validate`) et de simulations réussies.
- **Critère de réussite** : exactitude ≥ 80 % sur un test **rédigé à la main** et 100 % de workflows valides.
- **Hypothèses** : H1 un classifieur appris bat une baseline à règles ; H2 combiner n-grammes de caractères et mots-clés améliore la généralisation à des formulations libres ; H3 (non testée ici) Gemma 4 + réparation dépasse ce modèle sur des demandes hors des 14 structures.
- **Hors périmètre** : workflows hors des 14 structures, paramètres riches (texte des messages, opérateurs autres que `equals`).
