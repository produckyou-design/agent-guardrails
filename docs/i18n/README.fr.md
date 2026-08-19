# agent-guardrails

Vous avez demandé à un agent IA de « juste corriger l'espacement » et vous vous retrouvez avec 12 fichiers modifiés ?

Une fonction a été renommée, du code dupliqué a été « nettoyé », une boucle de retry stable depuis des mois a été simplifiée. Le diff paraît raisonnable. Les tests peuvent même passer.

Puis, quelques jours plus tard, quelque chose sans rapport casse.

`agent-guardrails` est un petit garde-fou Git pour ce problème précis : **empêcher les agents IA de modifier du code déjà terminé et hors du périmètre de la tâche.**

Au lieu d'ajouter une phrase de plus dans le prompt, la règle devient exécutable. Si un chemin protégé est modifié, le commit est refusé.

Aucune dépendance. Aucune API de modèle. Seulement Python et Git.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Test en 30 secondes

Donnez à l'agent une petite tâche :

```text
Corrige uniquement l'espacement de la page des paramètres.
```

Puis :

```sh
git diff --stat
```

Si vous attendiez 2 fichiers et qu'il y en a 9, ouvrez les 7 autres.

Vous trouverez souvent :

```text
« Renommé pour plus de clarté. »
« Logique dupliquée extraite. »
« Code apparemment inutilisé supprimé. »
« Code adjacent harmonisé. »
```

Tout paraît raisonnable. Rien n'était demandé.

Si vos diffs contiennent déjà uniquement ce que vous avez demandé, cet outil ne vous est peut-être pas encore nécessaire.

## Le problème résolu

Supposons que ce fichier fonctionne correctement en production depuis trois mois :

```text
src/billing/charge.py
```

La tâche du jour est simplement :

```text
Ajuster l'espacement de la page de facture.
```

L'agent ne sait pas pourquoi `charge.py` paraît un peu étrange. Il ne sait pas si cette branche existe à cause d'un incident réel survenu six mois plus tôt. Il voit le code, pas son histoire.

On écrit donc souvent :

```text
Ne modifiez pas ce fichier.
```

Dans `AGENTS.md`, `CLAUDE.md`, les prompts ou les commentaires.

Le problème : la documentation décrit une règle, elle ne l'impose pas.

`agent-guardrails` transforme :

```text
merci de ne pas toucher à ceci
```

en :

```text
commit rejected
```

## Fonctionnement

Ajoutez les chemins terminés à `frozen.json` :

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "Terminé, en production et hors roadmap.",
      "what_breaks": "Un mauvais calcul affiche toujours un écran normal ; seul le montant change.",
      "before_you_touch": [
        "Les remboursements partiels sont dans refund.py.",
        "Un échec annule toute la transaction.",
        "L'arrondi monétaire est décidé une seule fois à la frontière."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Si l'agent modifie ce chemin et tente un commit, il est arrêté au moment où le contexte compte le plus :

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
      verify -> pytest tests/test_billing.py -q
```

Le gate est du Python local. Aucun appel à un LLM.

Le travail normal passe. Le contexte supplémentaire n'apparaît que lorsque l'agent franchit une limite.

## Si le fichier doit vraiment changer

Frozen ne signifie pas immuable pour toujours.

Une modification légitime nécessite trois lignes dans le message de commit :

```text
UNFREEZE: src/billing/charge.py - un nouveau moyen de paiement exige une branche ici
UNFREEZE-IMPACT: une logique incorrecte peut modifier les montants facturés
UNFREEZE-ROLLBACK: git revert <sha> puis relancer pytest tests/test_billing.py
```

S'il en manque une, le commit est refusé.

Parce que « pourquoi maintenant » ne suffit pas. Avant de toucher du code éprouvé, il faut aussi savoir **ce qui casse si l'on se trompe** et **comment revenir en arrière**.

## Ce qui change en pratique

### Les petites tâches cessent de devenir des diffs géants

```text
Demande :
corriger l'espacement

Extras inattendus :
renommer un composant
refactoriser un helper API
simplifier les retries
fusionner des types
```

La dérive de périmètre devient visible avant d'entrer dans la branche principale.

### Le code bizarre conserve son histoire

Toute base de code mature contient des lignes qui semblent mauvaises mais soutiennent quelque chose d'important. `before_you_touch` montre la raison au moment exact où un agent tente d'y toucher.

### La revue est priorisée

Si un agent nocturne produit 34 commits et que 2 seulement contiennent `UNFREEZE`, commencez par ces 2.

### Le modèle change, la règle reste

Claude aujourd'hui, Codex demain, Gemini la semaine prochaine. L'application de la règle vit dans Git, pas dans la mémoire du modèle.

## Est-ce que cela économise des tokens ?

Les gates consomment **0 token LLM**. Ce sont des scripts locaux :

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

Ce qu'ils peuvent réduire, c'est le travail coûteux qui suit une mauvaise modification :

- exploration de fichiers inutile
- refactors hors périmètre
- génération de code pour ces refactors
- tests supplémentaires
- diagnostic de régression
- rollback
- refaire la tâche

Il n'y a volontairement pas de chiffre du type « 37 % d'économie ». Cela dépend de la fréquence à laquelle vos agents sortent du périmètre.

Ce n'est pas un optimiseur de tokens. Il évite du travail qui n'aurait jamais dû exister.

## Périmètre optionnel par tâche

`check_scope.py` peut limiter une tâche à des chemins autorisés :

```text
Tâche : espacement des paramètres

Autorisé :
frontend/settings/**
frontend/styles/settings.css

Interdit :
backend/**
database/**
billing/**
```

Sans fichier de scope, ce contrôle reste inactif.

## Il retrouve aussi le vrai travail Git abandonné

`check_git_policy.py` ne compte pas simplement les branches. Il utilise l'équivalence de patch (`git cherry`) pour distinguer le travail réellement absent de `main` de ce qui a déjà été intégré par squash ou rebase.

Dans le projet d'origine, « 11 branches non fusionnées » est devenu « 1 branche avec du travail réellement pertinent ».

## D'où vient cet outil

Il n'est pas né d'une théorie propre sur la sécurité des agents.

Il vient de plusieurs mois d'agents IA travaillant sur une vraie base de code en production. La production a cassé 60 fois. Chaque incident a été noté ainsi :

```text
Symptom   à quoi cela ressemblait
Cause     pourquoi c'est arrivé
Fix       ce qui a changé
Rule      quoi faire la prochaine fois
```

Les règles pouvant être appliquées mécaniquement sont devenues ces gates.

Le dépôt contient 28 de ces incidents dans `FAILURE_MODES.md`.

## Installation

Linux / macOS :

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /chemin/vers/votre-repo
```

Windows :

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\chemin\vers\votre-repo
```

Diagnostic :

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

Le hook local peut être contourné avec `--no-verify`; la CI ne le peut pas. Utiliser les deux est recommandé.

## Commencez vide

Ne gelez pas tout le dépôt.

```json
{
  "frozen": []
}
```

La première fois qu'un agent « améliore » du code déjà terminé, ajoutez ce chemin.

Un gate qui sonne en permanence devient du bruit. Protégez uniquement le code réellement terminé et coûteux à perturber.

## Discipline de staging

Évitez :

```sh
git add -A
git add .
git add -u
```

Préférez nommer les fichiers :

```sh
git add src/thing.py tests/test_thing.py
```

Un agent ne peut pas supposer que toutes les modifications d'un working tree partagé lui appartiennent.

## Vérifier signifie exécuter

`skill/SKILL.md` couvre les règles qui ne peuvent pas être imposées à partir du seul diff.

Lire le code et dire « ça devrait marcher » n'est pas une vérification. Si rien n'a été exécuté, indiquez `NOT_RUN`. Si cela échoue, indiquez l'échec. Pour les changements visuels, regardez le rendu réel avant de déclarer la tâche terminée.

## Tests

```sh
python tests/test_gates.py
```

Il y a 16 tests. Ils créent de vrais dépôts Git temporaires, de vrais commits et exécutent les gates comme processus séparés.

Les bugs trouvés dans les gates eux-mêmes deviennent aussi des tests de régression.

## Inclus

- `FAILURE_MODES.md` - 28 incidents réels à l'origine de ces règles
- `skill/SKILL.md` - règles de fonctionnement pour les agents
- `check_frozen.py` - protège les chemins terminés
- `check_scope.py` - limites optionnelles par tâche
- `check_git_policy.py` - retrouve le vrai travail Git restant
- `check_guardrail_integrity.py` - protège les guardrails eux-mêmes
- `doctor.py` - diagnostic d'installation

## Ce que l'outil ne fait pas

Il ne cherche pas les secrets ; utilisez par exemple gitleaks.

Il ne détecte pas les motifs dangereux généraux ; semgrep le fait mieux.

Il ne remplace pas la revue de code.

Il ne rend pas l'agent meilleur pour écrire du code.

Il fait une chose plus étroite :

> Empêcher des modifications plausibles mais hors périmètre sur du code déjà correct de devenir silencieusement des commits ordinaires.

## En une ligne

Ce n'est pas un autre prompt qui dit :

```text
Merci de ne pas modifier inutilement le code existant.
```

C'est ce qui se passe après que l'agent ignore cette phrase :

```text
commit rejected
```

## Licence

MIT. Prenez ce qui vous est utile.