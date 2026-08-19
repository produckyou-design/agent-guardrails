# agent-guardrails

Você pediu para um agente de IA "só ajustar o espaçamento" e terminou com 12 arquivos alterados?

Uma função foi renomeada, código duplicado foi "limpo" e um loop de retry que funcionava há meses foi simplificado. O diff parece razoável. Os testes podem até passar.

Dias depois, quebra algo que não tinha relação com a tarefa.

`agent-guardrails` é um pequeno gate de Git para esse problema: **impedir que agentes de IA alterem código já concluído e fora do escopo da tarefa.**

Em vez de confiar em mais uma frase no prompt, a regra vira código executável. Se um caminho protegido for alterado, o commit é recusado.

Sem dependências. Sem API de modelo. Só Python e Git.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Teste de 30 segundos

Dê ao agente uma tarefa pequena:

```text
Ajuste o espaçamento da página de configurações.
```

Quando terminar:

```sh
git diff --stat
```

Se você esperava dois arquivos e recebeu nove, abra os outros sete.

Você provavelmente verá coisas como:

```text
"Renomeado para ficar mais claro."
"Extraí lógica duplicada."
"Removi código que parecia não ser usado."
"Atualizei código adjacente por consistência."
```

Tudo parece razoável. Nada disso foi pedido.

Se seus diffs já contêm apenas o que foi solicitado, talvez você ainda não precise desta ferramenta.

## O problema que ela resolve

Suponha que este arquivo esteja funcionando corretamente em produção há três meses:

```text
src/billing/charge.py
```

A tarefa de hoje é apenas:

```text
Ajustar o espaçamento da tela de fatura.
```

O agente não sabe por que `charge.py` parece estranho. Não sabe se aquela condição existe por causa de um incidente real de seis meses atrás. Ele vê o código atual, não a história que produziu esse código.

Por isso escrevemos regras como:

```text
Não mexa neste arquivo.
```

em `AGENTS.md`, `CLAUDE.md`, prompts e comentários.

O problema é que documentação explica uma regra; não a aplica.

`agent-guardrails` transforma:

```text
por favor, não mexa nisso
```

em:

```text
commit rejected
```

## Como funciona

Adicione caminhos concluídos ao `frozen.json`:

```json
{
  "frozen": [
    {
      "label": "Billing",
      "paths": ["src/billing/charge.py"],
      "reason": "Concluído, em produção e fora do roadmap.",
      "what_breaks": "Uma conta errada ainda renderiza uma tela normal; só o valor muda.",
      "before_you_touch": [
        "Reembolsos parciais ficam em refund.py.",
        "Falhas revertem a transação inteira.",
        "O arredondamento de moeda é decidido uma vez na fronteira."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Se o agente alterar esse caminho e tentar commitar, ele é parado exatamente quando o contexto importa:

```text
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production.
      breaks -> Wrong math still renders a normal screen.
      verify -> pytest tests/test_billing.py -q
```

O gate é Python local. Não chama um LLM.

Trabalho normal passa. O contexto extra aparece apenas quando o agente cruza a fronteira.

## E se o arquivo realmente precisar mudar?

Frozen não significa imutável para sempre.

Uma mudança legítima exige três linhas na mensagem do commit:

```text
UNFREEZE: src/billing/charge.py - novo método de pagamento exige um branch aqui
UNFREEZE-IMPACT: lógica incorreta pode alterar os valores cobrados
UNFREEZE-ROLLBACK: git revert <sha> e depois pytest tests/test_billing.py
```

Se faltar uma, o commit é recusado.

Porque "por que agora" não basta. Antes de mexer em código provado, você também deveria saber **o que quebra se estiver errado** e **como voltar atrás**.

## O que muda na prática

### Tarefas pequenas deixam de virar diffs gigantes

```text
Pedido:
ajustar espaçamento

Extras inesperados:
renomear componente
refatorar helper de API
simplificar retries
unificar tipos
```

O desvio de escopo fica visível antes de entrar.

### Código estranho preserva sua história

Todo código maduro tem linhas que parecem erradas, mas sustentam algo importante. `before_you_touch` mostra o motivo no exato momento em que o agente tenta atravessar a fronteira.

### A revisão ganha prioridade

Se um agente noturno produzir 34 commits e dois tiverem `UNFREEZE`, revise esses dois primeiro.

### O modelo muda; a regra fica

Claude hoje, Codex amanhã, Gemini na semana que vem. A regra vive no Git, não na memória do modelo.

## Isso economiza tokens?

Os gates usam **zero tokens de LLM**. São scripts locais:

```sh
python scripts/check_frozen.py
python scripts/check_git_policy.py
python scripts/check_scope.py
```

O que eles podem reduzir é o trabalho caro que vem depois de uma mudança ruim:

- exploração desnecessária de arquivos
- refactors fora do escopo
- geração de código para esses refactors
- testes extras
- diagnóstico de regressão
- rollback
- refazer a tarefa

Não há um número do tipo "economiza 37%" porque isso depende da frequência com que seus agentes saem do escopo.

Não é um otimizador de tokens. Ele evita trabalho que nunca deveria existir.

## Escopo opcional por tarefa

`check_scope.py` pode limitar a tarefa a caminhos permitidos.

```text
Tarefa: espaçamento da tela de configurações

Permitido:
frontend/settings/**
frontend/styles/settings.css

Proibido:
backend/**
database/**
billing/**
```

Sem arquivo de escopo, a checagem fica inativa.

## Também encontra trabalho Git abandonado

`check_git_policy.py` não apenas conta branches. Ele usa equivalência de patches (`git cherry`) para separar trabalho realmente ausente de `main` de trabalho já incorporado por squash ou rebase.

No projeto original, "11 branches não mesclados" viraram "1 branch com trabalho que realmente importa".

## De onde veio

Não nasceu de uma teoria limpa sobre segurança de agentes.

Nasceu de meses de agentes de IA trabalhando em um código real de produção. Produção quebrou 60 vezes. Cada incidente foi registrado assim:

```text
Symptom   como parecia
Cause     por que aconteceu
Fix       o que mudou
Rule      o que fazer da próxima vez
```

As regras que podiam ser aplicadas mecanicamente viraram estes gates.

O repositório inclui 28 desses casos em `FAILURE_MODES.md`.

## Instalação

Linux / macOS:

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /caminho/do/seu-repo
```

Windows:

```powershell
git clone https://github.com/produckyou-design/agent-guardrails
.\agent-guardrails\install.ps1 C:\caminho\do\seu-repo
```

Diagnóstico:

```sh
python scripts/doctor.py
python scripts/doctor.py --json
```

O hook local pode ser ignorado com `--no-verify`; CI não pode. Usar ambos é recomendado.

## Comece vazio

Não congele o repositório inteiro.

```json
{
  "frozen": []
}
```

Na primeira vez que um agente "melhorar" código que já estava pronto, adicione esse caminho.

Um gate que dispara o tempo todo vira ruído. Proteja apenas o que realmente está concluído e é caro de perturbar.

## Disciplina de staging

Evite:

```sh
git add -A
git add .
git add -u
```

Prefira nomear os arquivos:

```sh
git add src/thing.py tests/test_thing.py
```

Um agente não pode assumir que toda alteração em uma working tree compartilhada pertence a ele.

## Verificação significa execução

`skill/SKILL.md` cobre regras que não podem ser inferidas apenas do diff.

Ler o código e dizer "deve funcionar" não é verificação. Se não executou, informe `NOT_RUN`. Se falhou, informe a falha. Para mudanças visuais, veja o resultado renderizado antes de declarar a tarefa concluída.

## Testes

```sh
python tests/test_gates.py
```

São 16 testes. Eles criam repositórios Git temporários reais, fazem commits reais e executam os gates em processos separados.

Bugs encontrados nos próprios gates também ficam como testes de regressão.

## Incluído

- `FAILURE_MODES.md` - 28 falhas reais que produziram estas regras
- `skill/SKILL.md` - regras operacionais para agentes
- `check_frozen.py` - protege caminhos concluídos
- `check_scope.py` - limites opcionais por tarefa
- `check_git_policy.py` - encontra trabalho Git realmente pendente
- `check_guardrail_integrity.py` - protege os próprios guardrails
- `doctor.py` - diagnóstico da instalação

## O que não faz

Não procura secrets; use ferramentas como gitleaks.

Não detecta padrões perigosos gerais; semgrep faz isso melhor.

Não substitui code review.

Não faz o agente escrever código melhor.

Faz uma coisa mais estreita:

> Impede que mudanças plausíveis, fora do escopo, em código já correto virem commits normais silenciosamente.

## Em uma linha

Não é outro prompt dizendo:

```text
Por favor, não altere código existente sem necessidade.
```

É o que acontece depois que o agente ignora essa frase:

```text
commit rejected
```

## Licença

MIT. Pegue o que for útil.