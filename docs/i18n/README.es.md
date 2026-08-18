# agent-guardrails

Reglas que tu agente de IA no puede saltarse, porque son código y no documentación.

[English](../../README.md) | [한국어](README.ko.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Lo que nadie te cuenta sobre los agentes de IA que escriben código

Normalmente no rompen producción escribiendo código malo.

La rompen tocando algo que ya estaba terminado, de una forma que en la revisión
parece completamente normal, y que ningún test cubre porque ese código
funcionaba y a nadie se le ocurrió escribirle uno.

Así se ve en la práctica. Todo esto llegó a producción.

**El despliegue salió bien. La pantalla no cambió.**
Se editó el CSS. Salió el HTML nuevo. Los navegadores siguieron usando el CSS
viejo en caché. El pipeline en verde, los logs limpios, el sitio mal. Es la peor
clase de fallo, porque la señal de éxito se dispara igual.

**El push salió bien. El despliegue nunca corrió.**
El commit existe. Está en GitHub. El workflow de despliegue era manual, así que
no pasó nada. Durante dos días "subido" y "en vivo" se contaron como lo mismo.

**Una función estaba en vivo y su código no estaba en ninguna rama.**
El consumidor se desplegó, el productor no. La pantalla seguía leyendo un
archivo que ya nadie escribía y servía la última copia buena hasta que caducó.

**La regla de seguridad llevaba seis meses en la documentación.**
"No tocar el layout móvil." Escrita, acordada, en el archivo de reglas que todos
los agentes leen. Nada la hacía cumplir. Se violaba constantemente, por todos
los agentes, incluidos los que acababan de leer esa frase.

Esa última es la razón entera de que exista este repositorio.

> Una regla que nada lee no es una salvaguarda. Es una nota que lo parece.

## Qué es esto

Dos archivos de Python. Solo librería estándar. Sin modelo, sin API, sin
servicio, sin dependencias que instalar.

```
check_frozen.py       353 líneas   bloquea el código terminado
check_git_policy.py   223 líneas   encuentra el trabajo enterrado
```

Salieron de un proyecto real donde agentes de IA enviaron código a producción
durante meses y lo rompieron 60 veces. Cada rotura se anotó, y las que podían
volverse código se volvieron estos gates. Este repositorio trae los dos que
generalizan, más los 27 incidentes que hay detrás.

## La parte que vale la pena copiar aunque no uses nada más

Congelar código es fácil. Lo difícil es cómo se descongela, porque la respuesta
"pregúntale a una persona" no sobrevive al contacto con un agente trabajando a
las 3 de la mañana.

Esto es lo que funciona. Para tocar una ruta congelada, el mensaje de commit
tiene que llevar tres líneas:

```
UNFREEZE: src/billing/charge.py - el nuevo medio de pago necesita una rama aquí
UNFREEZE-IMPACT: si el cálculo falla la pantalla sigue normal, solo cambia el importe
UNFREEZE-ROLLBACK: git revert <sha> y volver a correr pytest tests/test_billing.py
```

Si falta una, el commit se rechaza.

¿Por qué tres y no una? Porque el motivo solo responde "por qué ahora". No
responde qué pasa si te equivocas ni cómo vuelve alguien atrás. Esas son las dos
preguntas que importan a las 3 de la mañana, y son exactamente las dos que se
saltan.

Lo importante no es el papeleo. **Si no puedes escribir el impacto y la
reversión, no estás listo para descongelarlo, y acabas de descubrirlo tú mismo
en vez de descubrirlo en producción.** Ese juicio sale solo de las tres líneas,
y por eso funciona igual con agentes que con personas.

## Qué mejora de verdad

**Dejas de revisarlo todo.**
Tu agente hizo 34 commits durante la noche. Dos llevan líneas UNFREEZE. Esos dos
los lees primero. El gate no volvió cuidadoso al agente. Hizo que el agente te
dijera dónde se salió del camino.

**"Arregla el espaciado" deja de volver con 12 archivos cambiados.**
Pediste una cosa. El diff trae esa cosa, más una refactorización del cálculo de
impuestos, más una limpieza de un bucle de reintentos que existe solo porque una
API externa es inestable. El agente no es descuidado. No puede distinguir qué
código raro es raro por una razón. Ahora el código raro lo dice, en el momento
en que alguien lo toca.

**El apaño que sostiene algo deja de ser mejorado.**
Toda base de código tiene una línea que parece mal y está sujetando algo.
Alguien la ordena más o menos cada trimestre, y se rompe de una forma que nadie
conecta con el ordenado. `before_you_touch` es el cartel clavado en esa valla, y
aparece en la terminal, no en un archivo que nadie abre.

**Puedes irte a dormir.**
No porque el agente se haya vuelto prudente. Porque lo peor que puede hacer
mientras no estás ya está acotado por una lista que escribiste despierto.

**La regla deja de depender de que alguien la recuerde.**
"No toques el layout móvil" es un consejo. Un commit que no pasa es información.
La diferencia no es la cortesía. Uno de los dos funciona a las 3 de la mañana,
en un modelo que no te conoce, en su primer minuto en tu repositorio.

## Qué no hace esto

No mide cuánto mejora nada. En este README no hay tabla de benchmarks porque no
hay forma honesta de construirla, y una tabla inventada valdría menos que los
dos scripts.

No busca secretos ni patrones inseguros. gitleaks y semgrep hacen eso mejor que
cualquier cosa que se enviara aquí. Esto hace lo que ellos no hacen.

No hace que un agente escriba mejor código. Hace que un cambio equivocado sea
visible antes de salir. Son problemas distintos y esto solo cubre el segundo.

No sustituye la revisión. Elimina la clase de error que peor detecta la
revisión: la edición pequeña, plausible y adyacente a algo que ya estaba bien.

## Instalación

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /ruta/a/tu-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

O copia `gates/*.py` a tu `scripts/`, pon el hook de pre-commit y añade
`.github/workflows/gates.yml`. Los hooks locales se pueden saltar con
`--no-verify`, el job de CI no, así que usa los dos.

Empieza con la lista de congelados vacía. Añade la primera ruta el día en que un
agente edite algo que creías terminado. No vas a esperar mucho.

## Cómo escribir una entrada de congelación que aguante

Una ruta sin motivo la descongela el siguiente que la necesite. Lo que hace que
aguante es `what_breaks`, porque quien descongela tiene que saber qué se está
jugando.

```json
{
  "label": "Facturación",
  "paths": ["src/billing/charge.py"],
  "reason": "Terminado y en producción. No está en ninguna hoja de ruta.",
  "what_breaks": "Un cálculo mal sigue pintando una pantalla normal. Solo cambia el importe.",
  "before_you_touch": [
    "Los reembolsos parciales viven en refund.py, no aquí.",
    "Un fallo revierte la transacción entera. No debilitar eso."
  ],
  "how_to_verify": "pytest tests/test_billing.py -q"
}
```

`before_you_touch` es donde van las caídas. Cada línea debería ser algo que se
aprendió por las malas.

## No congeles todo

Si la congelación cubre el repositorio entero, el gate se convierte en el pastor
que gritaba "lobo", y las violaciones reales se ignoran junto con el ruido. Deja
abiertas de par en par las rutas que tu hoja de ruta va a tocar.

El proyecto de origen congela 19 rutas de varios cientos.

## Tests

```sh
python tests/test_gates.py
```

16 tests. Construyen un repositorio git real en un directorio temporal, hacen
commits reales y ejecutan los gates como subprocesos. Nada está mockeado, porque
lo que se prueba es cómo los gates leen git.

También cubren los errores que costaron caro, incluido aquel en que declarar
`src/db/sync-notices.py` desbloqueaba en silencio `src/db/sync_orders.py` porque
una expresión regular se comía el guion.

Un repositorio que sostiene que la verificación tiene que ser ejecutable debería
poder demostrarlo consigo mismo. Debilita la regla de tres líneas y fallan 3
tests. Rompe el manejo del guion y falla el test de rutas. Pruébalo.

## También incluido

`FAILURE_MODES.md` tiene los incidentes de los que salieron estos gates, en el
formato que los hizo útiles:

```
Síntoma  cómo se veía
Causa    por qué pasó
Arreglo  qué cambió
Regla    qué hacer a partir de ahora
```

Una prueba para saber si un incidente va en ese archivo: **si no lo escribo,
¿lo volveré a hacer?** Si sí, entra, aunque no se haya roto nada. Lo que se
repite casi nunca son las caídas dramáticas. Son los bucles pequeños en los que
caes todas las veces.

`skill/SKILL.md` es la mitad que lee el agente: las reglas de operación que
acompañan a los gates. Los gates atrapan lo que se puede comprobar
mecánicamente. La skill cubre el resto, como informar con honestidad sobre la
verificación que realmente ejecutaste.

## Licencia

MIT. Llévate lo que sirva, tira el resto.
