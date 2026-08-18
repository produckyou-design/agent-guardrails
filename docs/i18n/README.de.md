# agent-guardrails

Ein Werkzeug, das einen Commit ablehnt, wenn dein KI-Coding-Agent Code
verändert, der bereits fertig war. Es besteht aus zwei Python-Dateien, ohne
Abhängigkeiten zum Installieren.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Русский](README.ru.md)

---

## Welches Problem das löst

Wenn du Code an einen KI-Agenten gibst, kommt der Ärger meist nicht von dem
neuen Code, den er schreibt. Er kommt von dem Code, den er unterwegs anfasst.

Sagen wir, du bittest ihn, die Abstände auf der Rechnungsseite zu korrigieren.
Häufig räumt er bei der Gelegenheit auch die Steuerberechnung direkt daneben
auf. Das ist keine Nachlässigkeit. Der Agent hat keine Möglichkeit zu wissen,
warum dieser Code so aussieht, wie er aussieht, oder was nötig war, um dorthin zu
kommen. Und so eine Änderung sieht im Review nicht falsch aus. Ein Test deckt sie
auch nicht ab, denn der Code lief, und niemand kam auf die Idee, einen zu
schreiben.

Du kannst "diese Datei nicht anfassen" in die Projektdokumentation schreiben. Das
hält nicht. In dem Projekt, aus dem das hier stammt, stand diese Regel sechs
Monate in der Doku und wurde permanent gebrochen, auch von Agenten, die den Satz
gerade gelesen hatten, weil kein Code sie jemals geprüft hat.

Dieses Werkzeug macht aus dieser Regel **etwas, das tatsächlich ausgeführt wird**.

## Wie es funktioniert

Du listest die fertigen Pfade in `frozen.json` auf.

```json
{
  "frozen": [
    {
      "label": "Abrechnung",
      "paths": ["src/billing/charge.py"],
      "reason": "Fertig und in Produktion. Auf keiner Roadmap.",
      "what_breaks": "Eine falsche Rechnung zeigt trotzdem einen normalen Screen. Nur der Betrag ändert sich.",
      "before_you_touch": [
        "Teilrückerstattungen werden in refund.py behandelt, nicht hier.",
        "Ein Fehler rollt die gesamte Transaktion zurück. Das nicht abschwächen."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Danach installierst du den Pre-commit-Hook, und jeder Commit, der diese Pfade
verändert, wird abgelehnt. In diesem Moment wird alles, was du oben geschrieben
hast, im Terminal ausgegeben: warum es gesperrt ist, was kaputtgeht, wenn du dich
irrst, und was du wissen musst, bevor du es anfasst. Es erscheint **genau dann,
wenn jemand blockiert wird**, und nicht in einer Datei, die niemand öffnet.

### Wenn du es wirklich ändern musst

Schreib drei Zeilen in die Commit-Nachricht.

```
UNFREEZE: src/billing/charge.py - die neue Zahlart braucht hier einen Zweig
UNFREEZE-IMPACT: falsche Rechnung zeigt trotzdem einen normalen Screen, nur der Betrag ändert sich
UNFREEZE-ROLLBACK: git revert <sha>, danach pytest tests/test_billing.py erneut laufen lassen
```

Fehlt eine der drei, wird der Commit abgelehnt.

Warum drei Zeilen statt einer? Weil der Grund nur beantwortet, "warum das jetzt
geändert wird". Er sagt nicht, was passiert, wenn du dich irrst, und auch nicht,
wie jemand dahin zurückkommt, wo er war. Genau diese beiden Dinge zählen
tatsächlich, und genau diese beiden werden weggelassen.

**Wenn du Auswirkung und Rollback nicht schreiben kannst, bist du noch nicht so
weit, diesen Code zu ändern.** Und du erfährst das jetzt, statt es in der
Produktion zu erfahren. Es geht nicht darum, ein Formular auszufüllen, sondern
darum, dass dieses Urteil beim Schreiben der drei Zeilen von selbst entsteht.

## Was besser wird

**Du liest nicht mehr jeden Commit.** Angenommen, dein Agent hat über Nacht 34
Commits gemacht. Zwei davon tragen UNFREEZE-Zeilen. Die liest du zuerst. Der
Agent ist nicht vorsichtiger geworden; er markiert jetzt, wo er den Rahmen
verlassen hat, den du ihm gegeben hast.

**"Korrigier die Abstände" kommt nicht mehr als zwölf geänderte Dateien
zurück.** Du hast um eine Sache gebeten, und im Diff steckt zusätzlich ein
Refactor der Steuerberechnung und ein Aufräumen einer Retry-Schleife, die es nur
gibt, weil eine fremde API unzuverlässig ist. Das passiert seltener.

**Der tragende Workaround wird nicht mehr aufgeräumt.** Jede Codebasis hat eine
Zeile, die falsch aussieht, aber etwas zusammenhält. Alle paar Monate räumt sie
jemand auf, und später geht etwas kaputt, das niemand mit diesem Aufräumen in
Verbindung bringt. `before_you_touch` ist der Warnhinweis, der an dieser Stelle
hängt.

**Die Regel hängt nicht mehr davon ab, dass sich jemand erinnert.** "Fass das
Mobile-Layout nicht an" ist ein Ratschlag. Ein Commit, der nicht durchgeht, ist
eine Information. Das Zweite wirkt um 3 Uhr nachts, bei einem Modell, das dich
nie gesehen hat, in seiner ersten Minute in deinem Repository.

## Das zweite Werkzeug

`check_git_policy.py` findet nicht gemergte Branches und Worktrees, die
ausgecheckt liegen geblieben sind.

Ein herumliegender Branch ist nicht das eigentliche Problem. Das Problem ist,
dass **echte, nicht gemergte Arbeit darin vergraben wird**. Agenten legen
Branches und Worktrees an und gehen zur nächsten Aufgabe über, also sammelt sich
das an.

Es listet nicht einfach Branches auf. Es nutzt Patch-Äquivalenz (`git cherry`),
um Branches, deren Inhalt wirklich nicht auf main ist, von solchen zu trennen,
die bereits per Squash oder Rebase übernommen wurden. Im Ursprungsprojekt machte
diese Unterscheidung aus "11 nicht gemergten Branches" genau "1, der wirklich
zählt".

## Woher das kommt

Es stammt aus einem echten Projekt, in dem KI-Agenten monatelang Produktionscode
geschrieben haben. Dabei ging die Live-Seite 60 Mal kaputt. Jedes Mal wurde
festgehalten, was passiert war und was man anders machen sollte, und die Regeln,
die sich in Code verwandeln ließen, wurden zu diesen Gates.

Dieses Repository liefert die beiden, die auch außerhalb jenes Projekts gelten,
zusammen mit den 28 Vorfällen dahinter. Die stehen in `FAILURE_MODES.md`.

## Installation

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /pfad/zu/deinem-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\pfad\zu\deinem-repo
```

Von Hand: kopiere `gates/*.py` in das `scripts/` deines Projekts, lege
`hooks/pre-commit` in `.git/hooks/` ab und kopiere `examples/workflow.yml` nach
`.github/workflows/`.

Ein lokaler Hook lässt sich mit `--no-verify` überspringen, der CI-Job nicht.
Beides zu haben lohnt sich.

**Fang mit einer leeren Freeze-Liste an.** Nimm den ersten Pfad an dem Tag auf,
an dem ein Agent eine Datei ändert, die du für fertig gehalten hast.

## Friere nicht alles ein

Wenn der Freeze das ganze Repository abdeckt, schlägt das Gate ständig an, und
dann werden echte Verstöße zusammen mit dem Rauschen ignoriert. Lass die Pfade
offen, an denen du gleich arbeiten wirst.

Das Ursprungsprojekt hält 19 von mehreren Hundert Pfaden eingefroren.

## Was dieses Werkzeug nicht tut

**Es misst nicht, wie viel besser irgendetwas wird.** In diesem README gibt es
keine Benchmark-Tabelle, weil es keinen ehrlichen Weg gibt, eine zu erzeugen.

**Es sucht nicht nach Secrets oder unsicheren Code-Mustern.** gitleaks und
semgrep machen das weit besser. Dieses Werkzeug deckt ein Problem ab, das jene
nicht abdecken.

**Es bringt den Agenten nicht dazu, besseren Code zu schreiben.** Es macht nur
eine falsche Änderung sichtbar, bevor sie ausgeliefert wird.

**Es ersetzt kein Code-Review.** Es filtert genau das eine heraus, was Review am
schlechtesten findet: eine kleine, plausible Änderung an Code, der schon richtig
war.

## Tests

```sh
python tests/test_gates.py
```

Es sind 16. Sie legen ein echtes Git-Repository in einem temporären Verzeichnis
an, machen echte Commits und starten die Gates als eigene Prozesse. Nichts ist
gemockt, denn getestet wird, wie die Gates Git lesen.

Die teuer gelernten Bugs sind ebenfalls dabei. Zum Beispiel entsperrte das
Deklarieren von `src/db/sync-notices.py` früher stillschweigend
`src/db/sync_orders.py`, weil ein regulärer Ausdruck den Bindestrich
verschluckte.

Ein Repository, das behauptet, Verifikation müsse ausführbar sein, sollte das an
sich selbst zeigen können. Lockere die Drei-Zeilen-Regel und 3 Tests fallen um.
Zerbrich die Bindestrich-Behandlung und der Pfad-Test fällt um. Probier es
selbst.

## Was hier sonst noch liegt

**`FAILURE_MODES.md`** enthält die 28 Vorfälle, aus denen diese Gates entstanden
sind. Jeder besteht aus vier Zeilen.

```
Symptom   wie es aussah
Ursache   warum es passiert ist
Behebung  was sich geändert hat
Regel     was ab jetzt gilt
```

Es gibt genau einen Test, ob etwas in diese Datei gehört: **wenn ich das nicht
aufschreibe, mache ich es dann wieder?** Lautet die Antwort ja, kommt es rein,
auch wenn nichts kaputtgegangen ist. Was sich wiederholt, ist selten der
dramatische Ausfall. Es ist dieselbe Kleinigkeit, über die man jedes Mal
stolpert.

**`skill/SKILL.md`** enthält die Betriebsregeln, die ein Agent liest. Die Gates
fangen nur, was sich mechanisch prüfen lässt. Das hier deckt den Rest ab, etwa
nur die Prüfungen zu berichten, die du tatsächlich ausgeführt hast.

## Lizenz

MIT. Nimm mit, was nützt.
