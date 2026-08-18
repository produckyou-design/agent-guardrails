# agent-guardrails

Un outil qui refuse un commit lorsque votre agent de code IA modifie du code déjà
terminé. Ce sont deux fichiers Python, sans aucune dépendance à installer.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Quel problème cela résout

Quand vous confiez du code à un agent IA, l'ennui ne vient généralement pas du
code qu'il écrit. Il vient du code qu'il touche en passant.

Disons que vous lui demandez de corriger les espacements de la page de
facturation. Il en profitera souvent pour ranger aussi le calcul de TVA juste à
côté. Ce n'est pas de la négligence. L'agent n'a aucun moyen de savoir pourquoi
ce code est écrit ainsi, ni ce qu'il a fallu pour en arriver là. Et une telle
modification ne paraît pas anormale en revue. Aucun test ne la couvre non plus,
parce que ce code fonctionnait et que personne n'a pensé à en écrire un.

Vous pouvez écrire « ne touchez pas à ce fichier » dans la documentation du
projet. Cela ne tient pas. Dans le projet d'où vient cet outil, cette règle est
restée six mois dans la documentation et a été enfreinte en permanence, y compris
par des agents qui venaient de lire la phrase, parce qu'aucun code ne la
vérifiait.

Cet outil transforme cette règle en **quelque chose qui s'exécute réellement**.

## Comment cela fonctionne

Vous listez les chemins terminés dans `frozen.json`.

```json
{
  "frozen": [
    {
      "label": "Facturation",
      "paths": ["src/billing/charge.py"],
      "reason": "Terminé et en production. Sur aucune feuille de route.",
      "what_breaks": "Un calcul faux affiche quand même un écran normal. Seul le montant change.",
      "before_you_touch": [
        "Les remboursements partiels sont gérés dans refund.py, pas ici.",
        "Un échec annule toute la transaction. Ne pas affaiblir cela."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Vous installez ensuite le hook de pre-commit, et tout commit qui modifie ces
chemins est refusé. À ce moment-là, tout ce que vous avez écrit ci-dessus
s'affiche dans le terminal : pourquoi c'est verrouillé, ce qui casse si vous vous
trompez, et ce qu'il faut savoir avant d'y toucher. Cela apparaît **au moment où
quelqu'un est bloqué**, et non dans un fichier que personne n'ouvre.

### Si vous devez vraiment le modifier

Mettez trois lignes dans le message de commit.

```
UNFREEZE: src/billing/charge.py - le nouveau moyen de paiement exige une branche ici
UNFREEZE-IMPACT: un calcul faux affiche quand même un écran normal, seul le montant change
UNFREEZE-ROLLBACK: git revert <sha>, puis relancer pytest tests/test_billing.py
```

S'il en manque une seule, le commit est refusé.

Pourquoi trois lignes plutôt qu'une ? Parce que la raison ne répond qu'à
« pourquoi changer cela maintenant ». Elle ne dit pas ce qui se passe si vous vous
trompez, ni comment revenir en arrière. Or ce sont ces deux points qui comptent
vraiment, et ce sont exactement ceux qu'on omet.

**Si vous ne pouvez pas écrire l'impact et le retour arrière, vous n'êtes pas
encore prêt à modifier ce code.** Et vous l'apprenez maintenant plutôt qu'en
production. Le but n'est pas de vous faire remplir un formulaire, mais que ce
jugement émerge de l'écriture des trois lignes.

## Ce qui s'améliore

**Vous cessez de lire tous les commits.** Supposons que votre agent ait fait 34
commits pendant la nuit. Deux portent des lignes UNFREEZE. Ce sont ces deux-là
que vous lisez en premier. L'agent n'est pas devenu plus prudent : il signale
désormais où il est sorti du périmètre que vous lui aviez donné.

**« Corrige les espacements » ne revient plus sous forme de douze fichiers
modifiés.** Vous avez demandé une chose, et le diff contient en plus une
refactorisation du calcul de TVA et un nettoyage d'une boucle de retry qui
n'existe que parce qu'une API externe est instable. Cela arrive moins.

**Le bricolage porteur cesse d'être rangé.** Toute base de code contient une
ligne qui semble fausse mais qui soutient quelque chose. Tous les quelques mois,
quelqu'un la nettoie, et plus tard quelque chose casse d'une manière que personne
ne relie à ce nettoyage. `before_you_touch` est l'avertissement posé à cet
endroit.

**La règle ne dépend plus de la mémoire de quelqu'un.** « Ne touche pas au layout
mobile » est un conseil. Un commit qui ne passe pas est une information. Le second
fonctionne à 3 heures du matin, avec un modèle qui ne vous a jamais vu, dès sa
première minute dans votre dépôt.

## Le second outil

`check_git_policy.py` repère les branches non fusionnées et les worktrees laissés
ouverts.

Une branche qui traîne n'est pas le problème en soi. Le problème est que **du
vrai travail non fusionné s'y retrouve enterré**. Les agents créent des branches
et des worktrees puis passent à la tâche suivante, si bien que cela s'accumule.

Il ne se contente pas de lister des branches. Il utilise l'équivalence de patchs
(`git cherry`) pour distinguer les branches dont le contenu n'est réellement pas
sur main de celles déjà intégrées par un squash ou un rebase. Dans le projet
d'origine, cette distinction a transformé « 11 branches non fusionnées » en « 1
qui compte vraiment ».

## D'où cela vient

Cela vient d'un projet réel où des agents IA ont écrit du code de production
pendant des mois. En chemin, le site en production a cassé 60 fois. À chaque
fois, ce qui s'était passé et ce qu'il fallait faire autrement a été noté, et les
règles qui pouvaient devenir du code sont devenues ces garde-fous.

Ce dépôt livre les deux qui s'appliquent en dehors de ce projet, avec les 28
incidents qui les ont produits. Ils sont dans `FAILURE_MODES.md`.

## Installation

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /chemin/vers/votre-depot
```

Windows :

```powershell
.\agent-guardrails\install.ps1 C:\chemin\vers\votre-depot
```

Pour le faire à la main, copiez `gates/*.py` dans le `scripts/` de votre projet,
placez `hooks/pre-commit` dans `.git/hooks/`, et copiez `examples/workflow.yml`
dans `.github/workflows/`.

Un hook local se contourne avec `--no-verify`, mais pas le job de CI. Les deux
valent la peine.

**Commencez avec une liste de gel vide.** Ajoutez le premier chemin le jour où un
agent modifie un fichier que vous croyiez terminé.

## Ne gelez pas tout

Si le gel couvre tout le dépôt, le garde-fou se déclenche en permanence, et les
vraies violations sont ignorées avec le bruit. Laissez ouverts les chemins sur
lesquels vous allez travailler.

Le projet d'origine garde 19 chemins gelés sur plusieurs centaines.

## Ce que cet outil ne fait pas

**Il ne mesure aucune amélioration.** Il n'y a pas de tableau de benchmark dans ce
README parce qu'il n'existe aucun moyen honnête d'en produire un.

**Il ne cherche ni secrets ni motifs de code dangereux.** gitleaks et semgrep font
cela bien mieux. Cet outil couvre un problème qu'ils ne couvrent pas.

**Il ne fait pas écrire un meilleur code à l'agent.** Il rend seulement une
modification erronée visible avant qu'elle ne parte.

**Il ne remplace pas la revue de code.** Il filtre la seule chose que la revue
détecte le plus mal : une petite modification plausible sur du code qui était
déjà correct.

## Tests

```sh
python tests/test_gates.py
```

Il y en a 16. Ils créent un vrai dépôt git dans un répertoire temporaire, font de
vrais commits, et lancent les garde-fous comme processus séparés. Rien n'est
simulé, car ce qui est testé, c'est la façon dont ils lisent git.

Les bugs appris à la dure y figurent aussi. Par exemple, déclarer
`src/db/sync-notices.py` déverrouillait silencieusement `src/db/sync_orders.py`,
parce qu'une expression régulière avalait le trait d'union.

Un dépôt qui soutient que la vérification doit être exécutable devrait pouvoir le
démontrer sur lui-même. Assouplissez la règle des trois lignes et 3 tests
échouent. Cassez la gestion du trait d'union et le test de chemin échoue. Essayez
vous-même.

## Ce qu'il y a d'autre ici

**`FAILURE_MODES.md`** contient les 28 incidents dont ces garde-fous sont issus.
Chacun tient en quatre lignes.

```
Symptôme  à quoi cela ressemblait
Cause     pourquoi c'est arrivé
Correctif ce qui a changé
Règle     quoi faire désormais
```

Il n'y a qu'un test pour savoir si quelque chose a sa place dans ce fichier :
**si je ne l'écris pas, est-ce que je le referai ?** Si la réponse est oui, cela
entre, même si rien n'a cassé. Ce qui se répète est rarement une panne
spectaculaire. C'est la même petite chose sur laquelle vous butez à chaque fois.

**`skill/SKILL.md`** contient les règles d'exploitation que lit un agent. Les
garde-fous n'attrapent que ce qui se vérifie mécaniquement. Ceci couvre le reste,
par exemple ne rendre compte que de la vérification réellement exécutée.

## Licence

MIT. Prenez ce qui vous sert.
