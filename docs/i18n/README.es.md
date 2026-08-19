# agent-guardrails

¿Le pediste a un agente de IA «solo arregla el espaciado» y terminaste con 12 archivos modificados?

Renombró una función, «limpió» código duplicado y simplificó un bucle de reintentos que llevaba meses funcionando. El diff parece razonable. Incluso puede pasar los tests.

Y unos días después se rompe algo que no tenía nada que ver.

`agent-guardrails` es una pequeña puerta de Git para ese problema: **impedir que los agentes de IA cambien código que ya estaba terminado y fuera del alcance de la tarea.**

En vez de confiar en otra frase dentro del prompt, convierte la regla en código ejecutable. Si se modifica una ruta protegida, el commit se rechaza.

Sin dependencias. Sin API de modelos. Solo Python y Git.

[English](../../README.md) | [한국어](README.ko.md) | [Português](README.pt-BR.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Prueba de 30 segundos

Dale al agente una tarea pequeña:

```text
Corrige el espaciado de la página de configuración.
```

Al terminar:

```sh
git diff --stat
```

Si esperabas dos archivos y aparecen nueve, abre los otros siete.

Suelen aparecer cambios como:

```text
"Renombrado para mayor claridad."
"Extraje lógica duplicada."
"Eliminé código que parecía no usarse."
"Actualicé código cercano por consistencia."
```

Todos suenan razonables. Ninguno fue pedido.

Si tus diffs ya contienen solo lo solicitado, quizá todavía no necesites esta herramienta.

## El problema que resuelve

Supón que este archivo lleva tres meses funcionando correctamente en producción:

```text
src/billing/charge.py
```

La tarea de hoy solo es:

```text
Ajustar el espaciado de la página de facturas.
```

El agente no sabe por qué `charge.py` tiene una rama rara. No sabe si existe por una caída real de hace seis meses. Ve el código actual, no la historia que lo convirtió en ese código.

Por eso solemos escribir:

```text
No toques este archivo.
```

en `AGENTS.md`, `CLAUDE.md`, prompts y comentarios.

El problema es que la documentación explica una regla; no la hace cumplir.

`agent-guardrails` convierte:

```text
por favor, no toques esto
```

en:

```text
commit rejected
```

## Cómo funciona

Añade las rutas terminadas a `frozen.json`:

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "Terminado, en producción y fuera del roadmap.",
      "what_breaks": "Un cálculo incorrecto sigue mostrando una pantalla normal; solo cambia el importe.",
      "before_you_touch": [
        "Los reembolsos parciales viven en refund.py.",
        "Los fallos revierten toda la transacción.",
        "El redondeo de moneda se decide una sola vez en el límite."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Si el agente modifica esa ruta y trata de hacer commit, se detiene justo cuando importa el contexto:

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
      verify -> pytest tests/test_billing.py -q
```

La puerta es Python local. No llama a un LLM.

El trabajo normal pasa. El contexto extra aparece solo cuando el agente cruza el límite.

## Si realmente hay que cambiar el archivo

Congelado no significa inmutable para siempre.

Un cambio legítimo exige tres líneas en el mensaje de commit:

```text
UNFREEZE: src/billing/charge.py - el nuevo método de pago necesita una rama aquí
UNFREEZE-IMPACT: una lógica incorrecta puede cambiar los importes cobrados
UNFREEZE-ROLLBACK: git revert <sha> y volver a ejecutar pytest tests/test_billing.py
```

Si falta una, el commit se rechaza.

Porque «por qué ahora» no basta. Antes de tocar código probado también deberías saber **qué se rompe si te equivocas** y **cómo volver atrás**.

## Qué cambia en la práctica

### Las tareas pequeñas dejan de convertirse en diffs gigantes

```text
Pedido:
arreglar el espaciado

Extras inesperados:
renombrar componente
refactorizar helper de API
simplificar reintentos
fusionar tipos
```

El desvío de alcance se hace visible antes de entrar.

### El código raro conserva su historia

Todo código maduro tiene líneas que parecen incorrectas pero sostienen algo importante. `before_you_touch` muestra la razón justo cuando un agente intenta cruzar ese límite.

### La revisión gana prioridad

Si un agente nocturno produce 34 commits y dos contienen `UNFREEZE`, revisa esos dos primero.

### Cambia el modelo; la regla permanece

Claude hoy, Codex mañana, Gemini la semana que viene. La regla vive en Git, no en la memoria del modelo.

## ¿Ahorra tokens?

Las puertas consumen **cero tokens de LLM**. Son scripts locales:

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

Lo que pueden reducir es el trabajo caro que sigue a un mal cambio:

- exploración innecesaria de archivos
- refactors fuera de alcance
- generación de código para esos refactors
- tests adicionales
- diagnóstico de regresiones
- rollback
- repetir la tarea

No hay una cifra tipo «ahorra 37%» porque dependería de cuánto se desvíen tus agentes.

No es un optimizador de tokens. Evita trabajo que nunca debió existir.

## Alcance opcional por tarea

`check_scope.py` puede limitar una tarea a rutas permitidas.

```text
Tarea: espaciado de configuración

Permitido:
frontend/settings/**
frontend/styles/settings.css

Prohibido:
backend/**
database/**
billing/**
```

El scope es opcional. Sin archivo de scope, la comprobación queda inactiva.

## También encuentra trabajo Git abandonado

`check_git_policy.py` no se limita a contar ramas. Usa equivalencia de parches (`git cherry`) para separar trabajo realmente ausente de `main` de trabajo que ya entró mediante squash o rebase.

En el proyecto original, «11 ramas sin fusionar» se redujo a «1 rama con trabajo que realmente importa».

## De dónde salió

No nació de una teoría limpia sobre seguridad de agentes.

Nació de meses de agentes de IA trabajando sobre un código de producción real. Producción se rompió 60 veces. Cada incidente se registró así:

```text
Symptom   qué parecía pasar
Cause     por qué pasó
Fix       qué se cambió
Rule      qué hacer la próxima vez
```

Las reglas que podían hacerse cumplir mecánicamente se convirtieron en estas puertas.

El repositorio incluye 28 casos en `FAILURE_MODES.md`.

## Instalación

Linux / macOS:

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /ruta/a/tu-repo
```

Windows:

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\ruta\a\tu-repo
```

Diagnóstico:

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

El hook local puede saltarse con `--no-verify`; CI no. Se recomienda usar ambos.

## Empieza vacío

No congeles todo el repositorio.

```json
{
  "frozen": []
}
```

La primera vez que un agente «mejore» código ya terminado, añade esa ruta.

Una puerta que se dispara todo el tiempo se convierte en ruido. Protege solo lo que está realmente terminado y es caro de alterar.

## Disciplina al hacer staging

Evita:

```sh
git add -A
git add .
git add -u
```

Mejor nombra los archivos:

```sh
git add src/thing.py tests/test_thing.py
```

Un agente no puede asumir que todo cambio en un working tree compartido le pertenece.

## Verificar significa ejecutar

`skill/SKILL.md` cubre reglas que no pueden deducirse solo del diff.

Leer código y decir «debería funcionar» no es verificar. Si no se ejecutó algo, informa `NOT_RUN`. Si falló, informa el fallo. Para cambios visuales, mira el resultado renderizado antes de dar la tarea por terminada.

## Tests

```sh
python tests/test_gates.py
```

Hay 16 tests. Crean repositorios Git temporales reales, hacen commits reales y ejecutan las puertas como procesos separados.

Los bugs encontrados en las propias puertas también quedan como tests de regresión.

## Incluye

- `FAILURE_MODES.md` - 28 fallos reales que produjeron estas reglas
- `skill/SKILL.md` - reglas operativas para agentes
- `check_frozen.py` - protege rutas terminadas
- `check_scope.py` - límites opcionales por tarea
- `check_git_policy.py` - encuentra trabajo Git realmente pendiente
- `check_guardrail_integrity.py` - protege las propias guardrails
- `doctor.py` - diagnóstico de instalación

## Lo que no hace

No busca secretos; para eso existen herramientas como gitleaks.

No detecta patrones peligrosos generales; semgrep lo hace mejor.

No sustituye la revisión de código.

No hace que el agente escriba mejor código.

Hace una cosa más estrecha:

> Evita que cambios plausibles, fuera de alcance, sobre código ya correcto se conviertan silenciosamente en commits normales.

## En una línea

No es otro prompt que dice:

```text
Por favor, no modifiques código existente sin necesidad.
```

Es lo que ocurre después de que el agente ignore esa frase:

```text
commit rejected
```

## Licencia

MIT. Usa lo que te sirva.