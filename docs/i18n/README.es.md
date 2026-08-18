# agent-guardrails

Una herramienta que rechaza un commit cuando tu agente de IA edita código que ya
estaba terminado. Son dos archivos de Python, sin dependencias que instalar.

[English](../../README.md) | [한국어](README.ko.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Qué problema resuelve

Cuando le pasas código a un agente de IA, el problema no suele venir del código
nuevo que escribe. Viene del código que toca de camino.

Supongamos que le pides que corrija el espaciado de la página de facturas. Muy a
menudo aprovechará para ordenar también el cálculo de impuestos que está justo
al lado. No es descuido. El agente no tiene forma de saber por qué ese código es
como es, ni lo que costó llegar hasta ahí. Y un cambio así no parece incorrecto
en la revisión. Tampoco hay un test que lo cubra, porque el código funcionaba y
a nadie se le ocurrió escribirle uno.

Puedes poner "no toques este archivo" en la documentación del proyecto. No se
sostiene. En el proyecto del que salió esta herramienta, esa regla estuvo seis
meses en la documentación y se incumplió constantemente, incluso por agentes que
acababan de leer la frase, porque ningún código la comprobaba.

Esta herramienta convierte esa regla en **algo que se ejecuta de verdad**.

## Cómo funciona

Enumeras las rutas terminadas en `frozen.json`.

```json
{
  "frozen": [
    {
      "label": "Facturación",
      "paths": ["src/billing/charge.py"],
      "reason": "Terminado y en producción. No está en ninguna hoja de ruta.",
      "what_breaks": "Un cálculo mal sigue pintando una pantalla normal. Solo cambia el importe.",
      "before_you_touch": [
        "Los reembolsos parciales se manejan en refund.py, no aquí.",
        "Un fallo revierte la transacción entera. No debilites eso."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Después instalas el hook de pre-commit y cualquier commit que edite esas rutas
queda rechazado. Cuando eso ocurre, todo lo que escribiste arriba se imprime en
la terminal: por qué está bloqueado, qué se rompe si te equivocas y qué necesitas
saber antes de tocarlo. Aparece **en el momento en que alguien queda bloqueado**,
en vez de estar en un archivo que nadie abre.

### Si realmente necesitas cambiarlo

Pon tres líneas en el mensaje del commit.

```
UNFREEZE: src/billing/charge.py - el nuevo medio de pago necesita una rama aquí
UNFREEZE-IMPACT: un cálculo mal sigue pintando una pantalla normal, solo cambia el importe
UNFREEZE-ROLLBACK: git revert <sha> y volver a ejecutar pytest tests/test_billing.py
```

Si falta cualquiera de las tres, el commit se rechaza.

¿Por qué tres líneas y no una? Porque el motivo solo responde a "por qué cambiar
esto ahora". No dice qué pasa si te equivocas, ni cómo vuelve alguien al punto de
partida. Esas dos cosas son las que importan de verdad, y son exactamente las que
se omiten.

**Si no puedes escribir el impacto y la reversión, todavía no estás listo para
cambiar ese código.** Y te enteras ahora, en vez de enterarte en producción. La
idea no es que rellenes un formulario, sino que ese juicio salga de escribir las
tres líneas.

## Qué mejora

**Dejas de leer todos los commits.** Supongamos que tu agente hizo 34 commits
durante la noche. Dos llevan líneas UNFREEZE. Esos dos los lees primero. El
agente no se volvió más cuidadoso: ahora marca dónde se salió del alcance que le
diste.

**"Arregla el espaciado" deja de volver como doce archivos cambiados.** Pediste
una cosa, y el diff trae además una refactorización del cálculo de impuestos y
una limpieza de un bucle de reintentos que solo existe porque una API externa no
es fiable. Eso pasa menos.

**El apaño que sostiene algo deja de ser ordenado.** Toda base de código tiene
una línea que parece incorrecta pero está sujetando algo. Cada pocos meses
alguien la limpia, y más tarde algo se rompe de una forma que nadie conecta con
aquella limpieza. `before_you_touch` es el cartel de aviso puesto en ese punto.

**La regla deja de depender de que alguien la recuerde.** "No toques el layout
móvil" es un consejo. Un commit que no pasa es información. El segundo funciona a
las 3 de la mañana, con un modelo que nunca te ha visto, en su primer minuto en
tu repositorio.

## La segunda herramienta

`check_git_policy.py` encuentra ramas sin fusionar y worktrees que quedaron
abiertos.

Una rama que se queda ahí no es el problema en sí. El problema es que **se
entierra en ella trabajo real sin fusionar**. Los agentes crean ramas y worktrees
y pasan a la siguiente tarea, así que se acumulan.

No se limita a listar ramas. Usa equivalencia de parches (`git cherry`) para
distinguir las ramas cuyo contenido realmente no está en main de las que ya se
fusionaron mediante un squash o un rebase. En el proyecto de origen, esa
distinción convirtió "11 ramas sin fusionar" en "1 que de verdad importa".

## De dónde salió

Salió de un proyecto real donde agentes de IA escribieron código de producción
durante meses. Por el camino, el sitio en producción se rompió 60 veces. Cada
vez se anotó qué pasó y qué hacer distinto, y las reglas que podían convertirse
en código se convirtieron en estos gates.

Este repositorio trae los dos que sirven fuera de aquel proyecto, junto con los
28 incidentes que hay detrás. Están en `FAILURE_MODES.md`.

## Instalación

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /ruta/a/tu-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\ruta\a\tu-repo
```

Para hacerlo a mano, copia `gates/*.py` al `scripts/` de tu proyecto, pon
`hooks/pre-commit` en `.git/hooks/` y copia `examples/workflow.yml` en
`.github/workflows/`.

Un hook local se puede saltar con `--no-verify`, pero el job de CI no. Merece la
pena tener los dos.

**Empieza con la lista de congelados vacía.** Añade la primera ruta el día en que
un agente edite un archivo que creías terminado.

## No congeles todo

Si la congelación cubre todo el repositorio, el gate salta constantemente, y
entonces las violaciones reales se ignoran junto con el ruido. Deja abiertas las
rutas en las que estás a punto de trabajar.

El proyecto de origen mantiene 19 rutas congeladas de varios cientos.

## Lo que esta herramienta no hace

**No mide cuánto mejora nada.** En este README no hay tabla de benchmarks porque
no hay forma honesta de producir una.

**No busca secretos ni patrones de código inseguros.** gitleaks y semgrep hacen
eso mucho mejor. Esta herramienta cubre un problema que ellos no cubren.

**No hace que el agente escriba mejor código.** Solo hace visible un cambio
equivocado antes de que llegue a producción.

**No sustituye la revisión de código.** Filtra lo único que la revisión detecta
peor: una edición pequeña y plausible sobre código que ya era correcto.

## Tests

```sh
python tests/test_gates.py
```

Hay 16. Crean un repositorio git real en un directorio temporal, hacen commits
reales y ejecutan los gates como procesos aparte. No se simula nada, porque lo
que se prueba es cómo los gates leen git.

También están los errores que costaron caro. Por ejemplo, declarar
`src/db/sync-notices.py` desbloqueaba en silencio `src/db/sync_orders.py`,
porque una expresión regular se comía el guion.

Un repositorio que sostiene que la verificación debe ser ejecutable debería poder
demostrarlo consigo mismo. Relaja la regla de tres líneas y fallan 3 tests. Rompe
el manejo del guion y falla el test de rutas. Compruébalo tú mismo.

## Qué más hay aquí

**`FAILURE_MODES.md`** contiene los 28 incidentes de los que salieron estos
gates. Cada uno son cuatro líneas.

```
Síntoma  cómo se veía
Causa    por qué pasó
Arreglo  qué cambió
Regla    qué hacer a partir de ahora
```

Hay una sola prueba para saber si algo entra en ese archivo: **si no lo escribo,
¿lo volveré a hacer?** Si la respuesta es sí, entra, aunque no se haya roto nada.
Lo que se repite rara vez es una caída dramática. Es la misma cosa pequeña con la
que tropiezas siempre.

**`skill/SKILL.md`** contiene las reglas de operación que lee un agente. Los
gates solo atrapan lo que se puede comprobar mecánicamente. Esto cubre el resto,
como informar únicamente de la verificación que realmente ejecutaste.

## Licencia

MIT. Llévate lo que te sirva.
