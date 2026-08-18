# agent-guardrails

Uma ferramenta que recusa um commit quando seu agente de IA edita código que já
estava pronto. São dois arquivos Python, sem dependências para instalar.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## Isto se aplica a você? Dois minutos para descobrir

Peça ao seu agente uma mudança pequena e bem delimitada. Algo como "ajusta o
espaçamento da página de configurações". Depois, antes de ler o código:

```sh
git diff --stat
```

Conte os arquivos. Se o número for maior do que você pediu, abra os extras.
Normalmente você vai encontrar um rename, uma refatoração ou uma limpeza de algo
que já funcionava.

É esse o problema que esta ferramenta resolve. Não é que o agente escreva código
ruim. É que ele melhorou algo que você não pediu, e você teria que perceber isso
no review, toda vez, para sempre.

Se o diff tiver só o que você pediu, talvez você ainda não precise disto. Volte
na primeira vez em que não for assim.

## Que problema isto resolve

Quando você entrega código a um agente de IA, o problema geralmente não vem do
código novo que ele escreve. Vem do código que ele encosta no caminho.

Digamos que você peça para ajustar o espaçamento da página de faturas. Muitas
vezes ele vai aproveitar e reorganizar também o cálculo de impostos que está
logo ao lado. Não é descuido. O agente não tem como saber por que aquele código
é do jeito que é, nem o que foi preciso para chegar até ali. E uma mudança dessas
não parece errada no code review. Também não existe teste cobrindo, porque o
código funcionava e ninguém pensou em escrever um.

Você pode escrever "não mexa neste arquivo" na documentação do projeto. Isso não
se sustenta. No projeto de onde isto saiu, essa regra ficou seis meses na
documentação e foi quebrada o tempo todo, inclusive por agentes que tinham
acabado de ler a frase, porque nenhum código a verificava.

Esta ferramenta transforma essa regra em **algo que de fato executa**.

## Como funciona

Você lista os caminhos prontos no `frozen.json`.

```json
{
  "frozen": [
    {
      "label": "Faturamento",
      "paths": ["src/billing/charge.py"],
      "reason": "Pronto e rodando em produção. Não está em nenhum roadmap.",
      "what_breaks": "Conta errada ainda renderiza uma tela normal. Só o valor muda.",
      "before_you_touch": [
        "Reembolso parcial é tratado em refund.py, não aqui.",
        "Uma falha reverte a transação inteira. Não enfraqueça isso."
      ],
      "how_to_verify": "pytest tests/test_billing.py -q"
    }
  ]
}
```

Depois você instala o hook de pre-commit, e qualquer commit que edite esses
caminhos é recusado. Quando isso acontece, tudo o que você escreveu acima aparece
no terminal: por que está travado, o que quebra se você errar e o que precisa
saber antes de mexer. Aparece **no momento em que alguém é bloqueado**, e não
dentro de um arquivo que ninguém abre.

É assim que fica quando um agente tenta.

```
$ git commit -m "invoice: tidy up rounding"

frozen: FAIL - a frozen path was changed
  src/billing/charge.py
      [Billing] Finished and in production. Not on any roadmap.
      breaks -> Wrong math still renders a normal screen. Only the amount changes.
        - Partial refunds live in refund.py, not here.
        - Failure rolls the whole transaction back. Do not weaken that.
        - Currency rounding is decided once, at the boundary. Not per call site.
      verify -> pytest tests/test_billing.py -q
```

### Se você realmente precisar mudar

Coloque três linhas na mensagem do commit.

```
UNFREEZE: src/billing/charge.py - o novo meio de pagamento precisa de um ramo aqui
UNFREEZE-IMPACT: conta errada ainda renderiza uma tela normal, só o valor muda
UNFREEZE-ROLLBACK: git revert <sha> e rodar de novo pytest tests/test_billing.py
```

Se faltar qualquer uma das três, o commit é recusado.

Por que três linhas em vez de uma? Porque o motivo só responde "por que mudar
isso agora". Ele não diz o que acontece se você estiver errado, nem como alguém
volta ao ponto anterior. Essas duas coisas são as que realmente importam, e são
exatamente as que ficam de fora.

**Se você não consegue escrever o impacto e a reversão, ainda não está pronto
para mexer naquele código.** E você descobre isso agora, em vez de descobrir em
produção. A ideia não é te fazer preencher formulário. É que esse julgamento
apareça no ato de escrever as três linhas.

## O que melhora

**Você para de ler todos os commits.** Digamos que seu agente fez 34 commits
durante a noite. Dois carregam linhas UNFREEZE. São esses dois que você lê
primeiro. O agente não ficou mais cuidadoso: agora ele marca onde saiu do escopo
que você deu.

**"Ajusta o espaçamento" para de voltar como doze arquivos alterados.** Você
pediu uma coisa, e o diff traz junto uma refatoração do cálculo de impostos e uma
limpeza de um laço de retry que só existe porque uma API externa é instável. Isso
passa a acontecer menos.

**A gambiarra que sustenta algo para de ser arrumada.** Toda base de código tem
uma linha que parece errada mas está segurando alguma coisa. De tempos em tempos
alguém arruma, e depois algo quebra de um jeito que ninguém liga àquela arrumação.
`before_you_touch` é o aviso pregado naquele ponto.

**A regra deixa de depender de alguém lembrar.** "Não mexa no layout mobile" é
conselho. Um commit que não passa é informação. O segundo funciona às 3 da manhã,
com um modelo que nunca te viu, no primeiro minuto dele no seu repositório.

## A segunda ferramenta

`check_git_policy.py` encontra branches não mesclados e worktrees que ficaram
abertos.

Um branch parado não é o problema em si. O problema é que **trabalho real e não
mesclado fica enterrado nele**. Agentes criam branches e worktrees e seguem para
a próxima tarefa, então isso se acumula.

Ele não apenas lista branches. Usa equivalência de patches (`git cherry`) para
separar os branches cujo conteúdo realmente não está na main daqueles que já
foram mesclados via squash ou rebase. No projeto de origem, essa distinção
transformou "11 branches não mesclados" em "1 que realmente importa".

## De onde isto veio

Veio de um projeto real onde agentes de IA escreveram código de produção durante
meses. No caminho, o site no ar quebrou 60 vezes. A cada vez, o que aconteceu e o
que fazer diferente foi anotado, e as regras que podiam virar código viraram
estes gates.

Este repositório traz os dois que servem fora daquele projeto, junto com os 28
incidentes por trás deles. Estão em `FAILURE_MODES.md`.

## Instalação

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /caminho/do/seu-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\caminho\do\seu-repo
```

Para fazer na mão, copie `gates/*.py` para o `scripts/` do seu projeto, ponha
`hooks/pre-commit` em `.git/hooks/` e copie `examples/workflow.yml` para
`.github/workflows/`.

Um hook local dá para pular com `--no-verify`, mas o job de CI não. Vale ter os
dois.

**Comece com a lista de congelados vazia.** Adicione o primeiro caminho no dia em
que um agente editar um arquivo que você achava pronto.

## Não congele tudo

Se o congelamento cobrir o repositório inteiro, o gate dispara o tempo todo, e aí
as violações reais são ignoradas junto com o ruído. Deixe abertos os caminhos em
que você está prestes a trabalhar.

O projeto de origem mantém 19 caminhos congelados de várias centenas.

## O que esta ferramenta não faz

**Não mede o quanto algo melhora.** Não há tabela de benchmark neste README
porque não existe jeito honesto de produzir uma.

**Não procura segredos nem padrões de código inseguros.** gitleaks e semgrep
fazem isso muito melhor. Esta ferramenta cobre um problema que eles não cobrem.

**Não faz o agente escrever código melhor.** Só torna uma mudança errada visível
antes de ir para produção.

**Não substitui code review.** Filtra a única coisa que a revisão pega pior: uma
edição pequena e plausível em código que já estava certo.

## Testes

```sh
python tests/test_gates.py
```

São 16. Eles criam um repositório git real num diretório temporário, fazem
commits reais e rodam os gates como processos separados. Nada é simulado, porque
o que está sendo testado é como os gates leem o git.

Os bugs aprendidos do jeito caro também estão ali. Por exemplo, declarar
`src/db/sync-notices.py` destravava silenciosamente `src/db/sync_orders.py`,
porque uma expressão regular comia o hífen.

Um repositório que defende que verificação precisa ser executável deveria
conseguir demonstrar a própria. Afrouxe a regra das três linhas e 3 testes
falham. Quebre o tratamento do hífen e o teste de caminho falha. Pode conferir.

## O que mais tem aqui

**`FAILURE_MODES.md`** traz os 28 incidentes de onde estes gates saíram. Cada um
tem quatro linhas.

```
Sintoma   como aparecia
Causa     por que aconteceu
Correção  o que mudou
Regra     o que fazer daqui em diante
```

Existe um único teste para saber se algo entra nesse arquivo: **se eu não
escrever isto, vou fazer de novo?** Se a resposta for sim, entra, mesmo que nada
tenha quebrado. O que se repete raramente é uma queda dramática. É a mesma
coisinha em que você tropeça sempre.

**`skill/SKILL.md`** contém as regras de operação que um agente lê. Os gates só
pegam o que dá para checar mecanicamente. Isto cobre o resto, como relatar apenas
a verificação que você de fato rodou.

## Licença

MIT. Leve o que for útil.
