# agent-guardrails

Des règles que votre agent de code IA ne peut pas contourner, parce que ce sont
du code et non de la documentation.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Ce que personne ne vous dit sur les agents de code IA

En général, ils ne cassent pas la production en écrivant du mauvais code.

Ils la cassent en touchant à quelque chose qui était déjà terminé, d'une manière
qui paraît parfaitement normale en revue, et qu'aucun test ne couvre parce que
ce code fonctionnait et que personne n'a pensé à lui en écrire un.

Voilà à quoi ça ressemble. Tout ce qui suit est parti en production.

**Le déploiement a réussi. L'écran n'a pas changé.**
Le CSS a été modifié. Le nouveau HTML est sorti. Les navigateurs ont continué à
utiliser l'ancien CSS en cache. Pipeline au vert, logs propres, site faux. C'est
la pire catégorie de panne, parce que le signal de succès se déclenche quand même.

**Le push a réussi. Le déploiement n'a jamais tourné.**
Le commit existe. Il est sur GitHub. Le workflow de déploiement était manuel,
donc rien ne s'est passé. Pendant deux jours, « poussé » et « en ligne » ont été
comptés comme le même événement.

**Une fonctionnalité était en ligne et son code n'était sur aucune branche.**
Le consommateur avait été déployé, le producteur non. L'écran continuait à lire
un fichier que plus rien n'écrivait et servait la dernière copie valide jusqu'à
son expiration.

**La règle de sécurité était dans la doc depuis six mois.**
« Ne pas toucher à la mise en page mobile. » Écrite, validée, dans le fichier de
règles que tous les agents lisent. Rien ne l'appliquait. Elle était violée en
permanence, par tous les agents, y compris ceux qui venaient de lire la phrase.

Cette dernière est la raison d'être entière de ce dépôt.

> Une règle que rien ne lit n'est pas une protection. C'est une note qui y
> ressemble.

## De quoi il s'agit

Deux fichiers Python. Uniquement la bibliothèque standard. Pas de modèle, pas
d'API, pas de service, aucune dépendance à installer.

```
check_frozen.py       353 lignes   verrouille le code terminé
check_git_policy.py   223 lignes   retrouve le travail enterré
```

Ils viennent d'un projet réel où des agents IA ont livré du code de production
pendant des mois et l'ont cassé 60 fois. Chaque casse a été notée, et celles qui
pouvaient devenir du code sont devenues ces garde-fous. Ce dépôt livre les deux
qui se généralisent, plus les 27 incidents qui les ont produits.

## La partie à voler même si vous n'utilisez rien d'autre

Geler du code, c'est facile. La vraie question est comment on dégèle, parce que
la réponse « demande à un humain » ne survit pas au contact d'un agent qui
travaille à 3 heures du matin.

Voici ce qui fonctionne. Pour toucher à un chemin gelé, le message de commit doit
porter trois lignes :

```
UNFREEZE: src/billing/charge.py - le nouveau moyen de paiement exige une branche ici
UNFREEZE-IMPACT: un calcul faux affiche quand même un écran normal, seul le montant change
UNFREEZE-ROLLBACK: git revert <sha>, puis relancer pytest tests/test_billing.py
```

Il en manque une, le commit est refusé.

Pourquoi trois et pas une ? Parce que la raison ne répond qu'à « pourquoi
maintenant ». Elle ne dit pas ce qui se passe si vous vous trompez, ni comment on
revient en arrière. Ce sont les deux questions qui comptent à 3 heures du matin,
et ce sont exactement les deux qu'on saute.

L'important n'est pas la paperasse. **Si vous ne pouvez pas écrire l'impact et le
retour arrière, vous n'êtes pas prêt à dégeler, et vous venez de le découvrir
vous-même plutôt que de le découvrir en production.** Ce jugement sort tout seul
des trois lignes, et c'est pour cela que ça marche sur les agents aussi bien que
sur les humains.

## Ce qui s'améliore vraiment

**Vous arrêtez de tout relire.**
Votre agent a fait 34 commits pendant la nuit. Deux portent des lignes UNFREEZE.
Ce sont ces deux-là que vous lisez en premier. Le garde-fou n'a pas rendu
l'agent prudent. Il a fait en sorte que l'agent vous dise où il a quitté le
chemin.

**« Corrige l'espacement » ne revient plus avec 12 fichiers modifiés.**
Vous avez demandé une chose. Le diff contient cette chose, plus une
refactorisation du calcul de TVA, plus un nettoyage d'une boucle de retry qui
n'existe que parce qu'une API externe est instable. L'agent n'est pas
négligent. Il ne peut pas distinguer quel code bizarre est bizarre pour une
raison. Maintenant le code bizarre le dit, au moment où on y touche.

**Le bricolage porteur cesse d'être amélioré.**
Toute base de code a une ligne qui semble fausse et qui soutient quelque chose.
Quelqu'un la range à peu près une fois par trimestre, et ça casse d'une manière
que personne ne relie au rangement. `before_you_touch` est le panneau cloué sur
cette barrière, et il apparaît dans le terminal, pas dans un fichier que
personne n'ouvre.

**Vous pouvez aller dormir.**
Pas parce que l'agent est devenu prudent. Parce que le pire qu'il puisse faire
en votre absence est désormais borné par une liste que vous avez écrite éveillé.

**La règle cesse de dépendre de quelqu'un qui s'en souvient.**
« Ne touche pas au layout mobile » est un conseil. Un commit qui ne passe pas
est une information. La différence n'est pas la politesse. L'un des deux
fonctionne à 3 heures du matin, sur un modèle qui ne vous a jamais vu, dès sa
première minute dans votre dépôt.

## Ce que cela ne fait pas

Cela ne mesure pas l'amélioration. Il n'y a pas de tableau de benchmark dans ce
README parce qu'il n'existe pas de façon honnête d'en construire un, et un
tableau inventé vaudrait moins que les deux scripts.

Il ne cherche ni secrets ni motifs dangereux. gitleaks et semgrep font cela mieux
que tout ce qui serait livré ici. Ceci fait ce qu'ils ne font pas.

Cela ne fait pas écrire du meilleur code à un agent. Cela rend un mauvais
changement visible avant qu'il ne parte. Ce sont deux problèmes distincts et
ceci ne traite que le second.

Cela ne remplace pas la revue. Cela supprime la catégorie d'erreur que la revue
détecte le plus mal : la petite modification plausible et adjacente à quelque
chose qui était déjà correct.

## Installation

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /chemin/vers/votre-depot
```

Windows :

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

Ou copiez `gates/*.py` dans votre `scripts/`, posez le hook pre-commit et
ajoutez `.github/workflows/gates.yml`. Les hooks locaux se contournent avec
`--no-verify`, le job CI non, donc utilisez les deux.

Commencez avec une liste de gel vide. Ajoutez le premier chemin le jour où un
agent modifie quelque chose que vous croyiez terminé. Vous n'attendrez pas
longtemps.

## Écrire une entrée de gel qui tient

Un chemin sans raison sera dégelé par le suivant qui en a besoin. Ce qui fait
tenir un gel, c'est `what_breaks`, parce que celui qui dégèle doit savoir ce
qu'il risque.

```json
{
  "label": "Facturation",
  "paths": ["src/billing/charge.py"],
  "reason": "Terminé et en production. Sur aucune feuille de route.",
  "what_breaks": "Un calcul faux affiche quand même un écran normal. Seul le montant change.",
  "before_you_touch": [
    "Les remboursements partiels vivent dans refund.py, pas ici.",
    "Un échec annule toute la transaction. Ne pas affaiblir cela."
  ],
  "how_to_verify": "pytest tests/test_billing.py -q"
}
```

`before_you_touch` est l'endroit où atterrissent les incidents. Chaque ligne
devrait être quelque chose appris à la dure.

## Ne gelez pas tout

Si le gel couvre tout le dépôt, le garde-fou devient le garçon qui criait au
loup, et les vraies violations sont ignorées avec le bruit. Laissez grand
ouverts les chemins que votre feuille de route va toucher.

Le projet d'origine gèle 19 chemins sur plusieurs centaines.

## Tests

```sh
python tests/test_gates.py
```

16 tests. Ils construisent un vrai dépôt git dans un répertoire temporaire, font
de vrais commits et lancent les garde-fous comme sous-processus. Rien n'est
simulé, car ce qui est testé c'est la façon dont ils lisent git.

Ils couvrent aussi les bugs appris à la dure, dont celui où déclarer
`src/db/sync-notices.py` déverrouillait silencieusement `src/db/sync_orders.py`
parce qu'une expression régulière avalait le trait d'union.

Un dépôt qui soutient que la vérification doit être exécutable devrait pouvoir
le prouver sur lui-même. Affaiblissez la règle des trois lignes et 3 tests
échouent. Cassez la gestion du trait d'union et le test de chemin échoue.
Essayez.

## Également inclus

`FAILURE_MODES.md` contient les incidents dont ces garde-fous sont issus, dans le
format qui les a rendus utiles :

```
Symptôme  à quoi cela ressemblait
Cause     pourquoi c'est arrivé
Correctif ce qui a changé
Règle     quoi faire désormais
```

Un test pour savoir si un incident a sa place dans ce fichier : **si je ne
l'écris pas, est-ce que je le referai ?** Si oui, il entre, même si rien n'a
cassé. Ce qui se répète n'est presque jamais la panne spectaculaire. Ce sont les
petites boucles dans lesquelles vous retombez à chaque fois.

`skill/SKILL.md` est la moitié destinée à l'agent : les règles d'exploitation qui
accompagnent les garde-fous. Les garde-fous attrapent ce qui se vérifie
mécaniquement. La skill couvre le reste, comme rendre compte honnêtement des
vérifications réellement exécutées.

## Licence

MIT. Prenez ce qui sert, jetez le reste.
