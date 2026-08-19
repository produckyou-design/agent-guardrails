# agent-guardrails

Du bittest einen KI-Coding-Agenten: „Ändere nur den Abstand“ – und am Ende sind 12 Dateien verändert?

Eine Funktion wurde umbenannt, doppelter Code „aufgeräumt“ und eine seit Monaten stabile Retry-Schleife vereinfacht. Der Diff sieht vernünftig aus. Die Tests können sogar grün sein.

Ein paar Tage später bricht etwas völlig anderes.

`agent-guardrails` ist ein kleines Git-Gate für genau dieses Problem: **KI-Agenten daran hindern, bereits fertigen Code außerhalb des aktuellen Auftrags zu verändern.**

Statt noch einen Satz in den Prompt zu schreiben, wird die Regel ausführbar. Wird ein geschützter Pfad verändert, wird der Commit abgelehnt.

Keine Abhängigkeiten. Keine Modell-API. Nur Python und Git.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Русский](README.ru.md)

---

## 30-Sekunden-Test

Gib dem Agenten eine kleine Aufgabe:

```text
Ändere nur den Abstand auf der Einstellungsseite.
```

Danach:

```sh
git diff --stat
```

Wenn du zwei Dateien erwartet hast und neun bekommst, öffne die anderen sieben.

Oft findest du Dinge wie:

```text
„Zur besseren Lesbarkeit umbenannt.“
„Doppelte Logik ausgelagert.“
„Scheinbar unbenutzten Code entfernt.“
„Benachbarten Code für Konsistenz angepasst.“
```

Alles klingt vernünftig. Nichts davon war beauftragt.

Wenn deine Diffs ohnehin nur die angeforderten Änderungen enthalten, brauchst du dieses Tool vielleicht noch nicht.

## Welches Problem es löst

Angenommen, diese Datei läuft seit drei Monaten stabil in Produktion:

```text
src/billing/charge.py
```

Die heutige Aufgabe lautet nur:

```text
Abstand auf der Rechnungsseite anpassen.
```

Der Agent weiß nicht, warum `charge.py` etwas seltsam aussieht. Er weiß nicht, ob dieser merkwürdige Zweig wegen eines echten Vorfalls vor sechs Monaten existiert. Er sieht Code, nicht seine Geschichte.

Deshalb schreiben wir Regeln wie:

```text
Diese Datei nicht anfassen.
```

in `AGENTS.md`, `CLAUDE.md`, Prompts oder Kommentare.

Das Problem: Dokumentation beschreibt eine Regel. Sie erzwingt sie nicht.

`agent-guardrails` macht aus:

```text
bitte nicht anfassen
```

folgendes:

```text
commit rejected
```

## So funktioniert es

Fertige Pfade kommen in `frozen.json`:

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "Fertig, produktiv und nicht auf der Roadmap.",
      "what_breaks": "Falsche Berechnung rendert weiterhin normal; nur der Betrag ist falsch.",
      "before_you_touch": [
        "Teilrückerstattungen liegen in refund.py.",
        "Fehler rollen die gesamte Transaktion zurück.",
        "Währungsrundung wird einmal an der Grenze entschieden."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Ändert der Agent diesen Pfad und versucht zu committen, wird er genau dann gestoppt, wenn der Kontext wichtig ist:

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
      verify -> pytest tests/test_billing.py -q
```

Das Gate ist lokales Python. Es ruft kein LLM auf.

Normale Arbeit läuft durch. Zusätzlicher Kontext erscheint nur beim Überschreiten einer Grenze.

## Wenn die eingefrorene Datei wirklich geändert werden muss

Frozen bedeutet nicht für immer unveränderlich.

Eine legitime Änderung braucht drei Zeilen in der Commit-Nachricht:

```text
UNFREEZE: src/billing/charge.py - neue Zahlungsart braucht hier einen Zweig
UNFREEZE-IMPACT: falsche Logik kann berechnete Beträge verändern
UNFREEZE-ROLLBACK: git revert <sha> und danach pytest tests/test_billing.py ausführen
```

Fehlt eine Zeile, wird der Commit abgelehnt.

Denn „warum jetzt“ reicht nicht. Vor einer Änderung an bewährtem Code solltest du auch wissen, **was bei einem Fehler kaputtgeht** und **wie du zurückkommst**.

## Was sich praktisch ändert

### Kleine Aufgaben werden seltener zu riesigen Diffs

```text
Auftrag:
Abstand korrigieren

Unerwartete Extras:
Komponente umbenennen
API-Helper refaktorieren
Retries vereinfachen
Typen zusammenführen
```

Scope Drift wird sichtbar, bevor er landet.

### Seltsam aussehender Code behält seine Geschichte

Jede reife Codebasis hat Zeilen, die falsch aussehen, aber etwas Wichtiges tragen. `before_you_touch` zeigt den Grund genau dann, wenn ein Agent diese Grenze überschreiten will.

### Reviews bekommen Priorität

Wenn ein Nacht-Agent 34 Commits erzeugt und nur zwei `UNFREEZE` enthalten, prüfe diese zwei zuerst.

### Das Modell kann wechseln, die Regel bleibt

Heute Claude, morgen Codex, nächste Woche Gemini. Die Durchsetzung liegt in Git, nicht im Gedächtnis des Modells.

## Spart das Tokens?

Die Gates selbst verbrauchen **0 LLM-Tokens**. Sie sind lokale Skripte:

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

Reduziert werden kann die teure Arbeit nach einer schlechten Änderung:

- unnötige Dateisuche
- Refactors außerhalb des Scopes
- Codegenerierung dafür
- zusätzliche Tests
- Regression-Diagnose
- Rollbacks
- die Aufgabe erneut machen

Eine Zahl wie „37 % weniger Tokens“ gibt es absichtlich nicht. Sie hängt davon ab, wie oft deine Agenten den Scope verlassen.

Das ist kein Token-Optimierer. Es verhindert Arbeit, die nie hätte entstehen müssen.

## Optionaler Task-Scope

`check_scope.py` kann eine Aufgabe auf erlaubte Pfade begrenzen:

```text
Aufgabe: Abstand der Einstellungsseite

Erlaubt:
frontend/settings/**
frontend/styles/settings.css

Verboten:
backend/**
database/**
billing/**
```

Ohne Scope-Datei bleibt dieser Check inaktiv.

## Findet auch liegengebliebene Git-Arbeit

`check_git_policy.py` zählt nicht nur Branches. Mit Patch-Äquivalenz (`git cherry`) unterscheidet es echte Arbeit, die noch nicht in `main` ist, von Arbeit, die bereits per Squash oder Rebase gelandet ist.

Im Ursprungsprojekt wurden aus „11 ungemergten Branches“ genau „1 Branch mit wirklich relevanter offener Arbeit“.

## Woher das kommt

Das Tool entstand nicht aus einer sauberen Theorie über Agentensicherheit.

Es entstand nach Monaten mit KI-Agenten auf einer echten Produktions-Codebasis. Produktion brach 60-mal. Jeder Vorfall wurde so festgehalten:

```text
Symptom   wie es aussah
Cause     warum es passierte
Fix       was geändert wurde
Rule      was beim nächsten Mal zu tun ist
```

Die Regeln, die sich mechanisch erzwingen ließen, wurden zu diesen Gates.

28 dieser realen Fälle liegen in `FAILURE_MODES.md`.

## Installation

Linux / macOS:

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /pfad/zum/repo
```

Windows:

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\pfad\zum\repo
```

Diagnose:

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

Der lokale Hook kann mit `--no-verify` umgangen werden; CI nicht. Beides zusammen wird empfohlen.

## Leer starten

Nicht das ganze Repository einfrieren.

```json
{
  "frozen": []
}
```

Wenn ein Agent zum ersten Mal bereits fertigen Code „hilfreich“ verändert, füge diesen Pfad hinzu.

Ein Gate, das ständig feuert, wird zu Rauschen. Schütze nur wirklich fertigen und teuer zu störenden Code.

## Staging-Disziplin

Vermeide:

```sh
git add -A
git add .
git add -u
```

Besser die eigenen Dateien benennen:

```sh
git add src/thing.py tests/test_thing.py
```

Ein Agent darf nicht annehmen, dass jede Änderung in einem gemeinsamen Working Tree ihm gehört.

## Verifikation bedeutet Ausführung

`skill/SKILL.md` enthält Regeln, die sich nicht allein aus dem Diff erzwingen lassen.

Code lesen und „sollte funktionieren“ sagen ist keine Verifikation. Nicht ausgeführt heißt `NOT_RUN`. Ein Fehler wird als Fehler gemeldet. Bei sichtbaren Änderungen sollte das tatsächliche Rendering geprüft werden.

## Tests

```sh
python tests/test_gates.py
```

Es gibt 16 Tests. Sie erzeugen echte temporäre Git-Repositories, echte Commits und führen die Gates als separate Prozesse aus.

Auch Bugs in den Gates selbst bleiben als Regressionstests erhalten.

## Enthalten

- `FAILURE_MODES.md` - 28 reale Fehlerfälle hinter diesen Regeln
- `skill/SKILL.md` - Betriebsregeln für Agenten
- `check_frozen.py` - schützt fertige Pfade
- `check_scope.py` - optionale Task-Grenzen
- `check_git_policy.py` - findet wirklich offene Git-Arbeit
- `check_guardrail_integrity.py` - schützt die Guardrails selbst
- `doctor.py` - Installationsdiagnose

## Was es nicht tut

Keine Secret-Suche; dafür eignen sich Tools wie gitleaks.

Keine allgemeine Dangerous-Pattern-Erkennung; semgrep ist dafür besser.

Kein Ersatz für Code Review.

Es macht den Agenten nicht besser im Schreiben von Code.

Es tut eine engere Sache:

> Plausible Änderungen außerhalb des Scopes an bereits korrektem Code sollen nicht still zu normalen Commits werden.

## In einem Satz

Das ist kein weiterer Prompt mit:

```text
Bitte bestehenden Code nicht unnötig verändern.
```

Es ist das, was passiert, nachdem der Agent diesen Satz ignoriert:

```text
commit rejected
```

## Lizenz

MIT. Nimm, was nützlich ist.