# agent-guardrails

Regeln, die dein KI-Coding-Agent nicht überspringen kann, weil sie Code sind und
keine Dokumentation.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Русский](README.ru.md)

---

## Was dir niemand über KI-Coding-Agenten sagt

Sie zerlegen die Produktion normalerweise nicht dadurch, dass sie schlechten
Code schreiben.

Sie zerlegen sie, indem sie etwas anfassen, das bereits fertig war, und zwar auf
eine Weise, die im Review völlig normal aussieht und die kein Test abdeckt, weil
der Code lief und niemand auf die Idee kam, einen zu schreiben.

So sieht das in der Praxis aus. Alles davon ging live.

**Das Deployment war erfolgreich. Der Bildschirm hat sich nicht geändert.**
CSS wurde geändert, neues HTML ging raus. Browser benutzten weiter das alte CSS
aus dem Cache. Pipeline grün, Logs sauber, Seite falsch. Das ist die schlimmste
Sorte Fehler, weil das Erfolgssignal trotzdem feuert.

**Der Push war erfolgreich. Das Deployment lief nie.**
Der Commit existiert. Er ist auf GitHub. Der Deploy-Workflow war manuell, also
passierte nichts. Zwei Tage lang wurden "gepusht" und "live" als dasselbe
gezählt.

**Ein Feature lief live, und sein Code lag auf keinem Branch.**
Der Consumer war deployed, der Producer nicht. Der Bildschirm las weiter eine
Datei, die niemand mehr schrieb, und lieferte die letzte gute Kopie aus, bis sie
ablief.

**Die Sicherheitsregel stand seit sechs Monaten in der Doku.**
"Mobile Layout nicht anfassen." Aufgeschrieben, abgestimmt, in der Regeldatei,
die jeder Agent liest. Nichts hat sie durchgesetzt. Sie wurde permanent
verletzt, von jedem Agenten, auch von denen, die den Satz gerade gelesen hatten.

Der letzte Punkt ist der ganze Grund, warum es dieses Repository gibt.

> Eine Regel, die nichts liest, ist keine Schutzmaßnahme. Sie ist eine Notiz, die
> so aussieht.

## Was das hier ist

Zwei Python-Dateien. Nur Standardbibliothek. Kein Modell, keine API, kein Dienst,
keine Abhängigkeiten zum Installieren.

```
check_frozen.py       353 Zeilen   sperrt fertigen Code
check_git_policy.py   223 Zeilen   findet vergrabene Arbeit
```

Sie stammen aus einem echten Projekt, in dem KI-Agenten monatelang
Produktionscode ausgeliefert und ihn 60 Mal kaputtgemacht haben. Jeder Bruch
wurde aufgeschrieben, und was zu Code werden konnte, wurde zu diesen Gates.
Dieses Repository liefert die beiden, die sich verallgemeinern lassen, plus die
27 Vorfälle dahinter.

## Der Teil, den es sich zu klauen lohnt, selbst wenn du sonst nichts nimmst

Code einzufrieren ist einfach. Die schwierige Frage ist, wie jemand ihn wieder
auftaut, denn die Antwort "frag einen Menschen" überlebt den Kontakt mit einem
Agenten, der um 3 Uhr nachts arbeitet, nicht.

Das hier funktioniert. Um einen eingefrorenen Pfad anzufassen, muss die
Commit-Nachricht drei Zeilen tragen:

```
UNFREEZE: src/billing/charge.py - die neue Zahlart braucht hier einen Zweig
UNFREEZE-IMPACT: falsche Rechnung zeigt trotzdem einen normalen Screen, nur der Betrag ändert sich
UNFREEZE-ROLLBACK: git revert <sha>, danach pytest tests/test_billing.py erneut laufen lassen
```

Fehlt eine, wird der Commit abgelehnt.

Warum drei und nicht eine? Weil der Grund nur "warum jetzt" beantwortet. Er
beantwortet nicht, was passiert, wenn du dich irrst, und auch nicht, wie jemand
zurückkommt. Das sind die beiden Fragen, die um 3 Uhr nachts zählen, und genau
die beiden werden übersprungen.

Der Punkt ist nicht die Bürokratie. **Wenn du Auswirkung und Rollback nicht
schreiben kannst, bist du noch nicht so weit, das aufzutauen, und du hast es
gerade selbst herausgefunden statt in der Produktion.** Dieses Urteil fällt von
allein aus den drei Zeilen, und deshalb wirkt es bei Agenten genauso wie bei
Menschen.

## Was tatsächlich besser wird

**Du hörst auf, alles zu reviewen.**
Dein Agent hat über Nacht 34 Commits gemacht. Zwei davon tragen UNFREEZE-Zeilen.
Die beiden liest du zuerst. Das Gate hat den Agenten nicht vorsichtig gemacht.
Es hat den Agenten dazu gebracht, dir zu sagen, wo er vom Weg abgekommen ist.

**"Korrigier den Abstand" kommt nicht mehr mit 12 geänderten Dateien zurück.**
Du hast um eine Sache gebeten. Der Diff enthält diese Sache, dazu ein Refactor
der Steuerberechnung und ein Aufräumen einer Retry-Schleife, die es nur gibt,
weil eine fremde API wackelt. Der Agent ist nicht schludrig. Er kann nicht
unterscheiden, welcher seltsame Code aus einem Grund seltsam ist. Jetzt sagt der
seltsame Code das selbst, in dem Moment, in dem er angefasst wird.

**Der tragende Workaround wird nicht mehr verbessert.**
Jede Codebasis hat eine Zeile, die falsch aussieht und etwas trägt. Ungefähr
einmal im Quartal räumt sie jemand auf, und dann bricht etwas auf eine Art, die
niemand mit dem Aufräumen verbindet. `before_you_touch` ist das Schild an genau
diesem Zaun, und es erscheint im Terminal, nicht in einer Datei, die niemand
öffnet.

**Du kannst schlafen gehen.**
Nicht weil der Agent vorsichtig geworden ist. Weil das Schlimmste, das er in
deiner Abwesenheit anrichten kann, jetzt durch eine Liste begrenzt ist, die du
im Wachzustand geschrieben hast.

**Die Regel hängt nicht mehr daran, dass sich jemand erinnert.**
"Fass das Mobile-Layout nicht an" ist ein Ratschlag. Ein Commit, der nicht
durchgeht, ist eine Information. Der Unterschied ist nicht Höflichkeit. Eines
von beiden wirkt um 3 Uhr nachts, bei einem Modell, das dich nie gesehen hat, in
seiner ersten Minute in deinem Repository.

## Was das hier nicht tut

Es misst nicht, wie viel besser irgendetwas wird. In diesem README gibt es keine
Benchmark-Tabelle, weil es keinen ehrlichen Weg gibt, eine zu bauen, und eine
erfundene Tabelle wäre weniger wert als die zwei Skripte.

Es sucht weder nach Secrets noch nach unsicheren Mustern. gitleaks und semgrep
können das besser als alles, was hier mitgeliefert würde. Dieses Repo macht das,
was die beiden nicht machen.

Es bringt einen Agenten nicht dazu, besseren Code zu schreiben. Es macht eine
falsche Änderung sichtbar, bevor sie rausgeht. Das sind verschiedene Probleme,
und hier geht es nur um das zweite.

Es ersetzt kein Review. Es entfernt die Fehlerklasse, die Review am schlechtesten
findet: die kleine, plausible, benachbarte Änderung an etwas, das schon richtig
war.

## Installation

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /pfad/zu/deinem-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

Oder kopiere `gates/*.py` in dein `scripts/`, leg den Pre-commit-Hook ab und füge
`.github/workflows/gates.yml` hinzu. Lokale Hooks lassen sich mit `--no-verify`
umgehen, der CI-Job nicht, also nutze beide.

Fang mit einer leeren Freeze-Liste an. Füge den ersten Pfad an dem Tag hinzu, an
dem ein Agent etwas ändert, das du für fertig gehalten hast. Du wirst nicht lange
warten müssen.

## Einen Freeze-Eintrag schreiben, der hält

Ein Pfad ohne Begründung wird von dem aufgetaut, der ihn als Nächstes braucht.
Was einen Freeze hält, ist `what_breaks`, denn wer auftaut, muss wissen, was er
riskiert.

```json
{
  "label": "Abrechnung",
  "paths": ["src/billing/charge.py"],
  "reason": "Fertig und in Produktion. Auf keiner Roadmap.",
  "what_breaks": "Eine falsche Rechnung zeigt trotzdem einen normalen Screen. Nur der Betrag ändert sich.",
  "before_you_touch": [
    "Teilrückerstattungen liegen in refund.py, nicht hier.",
    "Ein Fehler rollt die gesamte Transaktion zurück. Das nicht abschwächen."
  ],
  "how_to_verify": "pytest tests/test_billing.py -q"
}
```

`before_you_touch` ist der Ort, an dem die Ausfälle landen. Jede Zeile darin
sollte etwas sein, das teuer gelernt wurde.

## Friere nicht alles ein

Wenn der Freeze das ganze Repository abdeckt, wird das Gate zum Jungen, der
"Wolf" rief, und echte Verstöße werden zusammen mit dem Rauschen ignoriert. Lass
die Pfade, die deine Roadmap als Nächstes anfasst, weit offen.

Das Ursprungsprojekt friert 19 Pfade von mehreren Hundert ein.

## Tests

```sh
python tests/test_gates.py
```

16 Tests. Sie bauen ein echtes Git-Repository in einem temporären Verzeichnis,
machen echte Commits und starten die Gates als Subprozesse. Nichts ist gemockt,
denn getestet wird genau, wie die Gates Git lesen.

Sie decken auch die teuer gelernten Bugs ab, darunter der, bei dem das Deklarieren
von `src/db/sync-notices.py` stillschweigend `src/db/sync_orders.py` entsperrte,
weil ein Regex den Bindestrich verschluckte.

Ein Repository, das behauptet, Verifikation müsse ausführbar sein, sollte das
zuerst bei sich selbst zeigen können. Schwäche die Drei-Zeilen-Regel ab und 3
Tests fallen um. Zerbrich die Bindestrich-Behandlung und der Pfad-Test fällt um.
Probier es aus.

## Ebenfalls enthalten

`FAILURE_MODES.md` enthält die Vorfälle, aus denen diese Gates entstanden sind,
in dem Format, das sie nützlich gemacht hat:

```
Symptom   wie es aussah
Ursache   warum es passiert ist
Behebung  was sich geändert hat
Regel     was ab jetzt gilt
```

Ein Test, ob ein Vorfall in diese Datei gehört: **wenn ich das nicht
aufschreibe, mache ich es dann wieder?** Wenn ja, kommt er rein, auch wenn nichts
kaputtgegangen ist. Was sich wiederholt, sind fast nie die dramatischen Ausfälle.
Es sind die kleinen Schleifen, in die man jedes Mal hineinläuft.

`skill/SKILL.md` ist die agentenseitige Hälfte: die Betriebsregeln, die zu den
Gates gehören. Gates fangen, was sich mechanisch prüfen lässt. Die Skill deckt
den Rest ab, etwa ehrlich darüber zu berichten, welche Prüfungen du tatsächlich
ausgeführt hast.

## Lizenz

MIT. Nimm, was nützt, wirf den Rest weg.
