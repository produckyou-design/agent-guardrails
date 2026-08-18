# agent-guardrails

Regras que seu agente de IA não consegue pular, porque são código e não documentação.

[English](../../README.md) | [한국어](README.ko.md) | [Español](README.es.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

---

## O que ninguém conta sobre agentes de IA que escrevem código

Em geral eles não quebram produção escrevendo código ruim.

Quebram mexendo em algo que já estava pronto, de um jeito que no code review
parece totalmente normal, e que nenhum teste cobre porque aquele código
funcionava e ninguém pensou em escrever um.

Na prática é assim. Tudo isso foi para produção.

**O deploy deu certo. A tela não mudou.**
O CSS foi editado. O HTML novo subiu. Os navegadores continuaram usando o CSS
antigo em cache. Pipeline verde, logs limpos, site errado. É o pior tipo de
falha, porque o sinal de sucesso dispara do mesmo jeito.

**O push deu certo. O deploy nunca rodou.**
O commit existe. Está no GitHub. O workflow de deploy era manual, então nada
aconteceu. Por dois dias "subiu" e "está no ar" foram contados como a mesma
coisa.

**Uma funcionalidade estava no ar e o código dela não estava em nenhum branch.**
O consumidor foi para produção, o produtor não. A tela continuou lendo um
arquivo que ninguém mais escrevia e serviu a última cópia boa até ela vencer.

**A regra de segurança estava na documentação havia seis meses.**
"Não mexer no layout mobile." Escrita, acordada, dentro do arquivo de regras que
todo agente lê. Nada garantia o cumprimento. Era violada o tempo todo, por todos
os agentes, inclusive os que tinham acabado de ler a frase.

Essa última é a razão inteira deste repositório existir.

> Uma regra que nada lê não é uma proteção. É um bilhete que parece uma.

## O que é isto

Dois arquivos Python. Só biblioteca padrão. Sem modelo, sem API, sem serviço,
sem dependências para instalar.

```
check_frozen.py       353 linhas   tranca o código pronto
check_git_policy.py   223 linhas   encontra trabalho enterrado
```

Saíram de um projeto real onde agentes de IA mandaram código para produção
durante meses e quebraram 60 vezes. Cada quebra foi anotada, e as que podiam
virar código viraram estes gates. Este repositório traz os dois que generalizam,
mais os 27 incidentes por trás deles.

## A parte que vale copiar mesmo que você não use mais nada

Congelar código é fácil. O difícil é como alguém descongela, porque a resposta
"pergunta para uma pessoa" não sobrevive ao contato com um agente trabalhando às
3 da manhã.

O que funciona é isto. Para tocar num caminho congelado, a mensagem de commit
precisa carregar três linhas:

```
UNFREEZE: src/billing/charge.py - o novo meio de pagamento precisa de um ramo aqui
UNFREEZE-IMPACT: se a conta estiver errada a tela continua normal, só muda o valor
UNFREEZE-ROLLBACK: git revert <sha> e rodar de novo pytest tests/test_billing.py
```

Faltou uma, o commit é recusado.

Por que três e não uma? Porque o motivo só responde "por que agora". Não responde
o que acontece se você estiver errado, nem como alguém volta atrás. Essas são as
duas perguntas que importam às 3 da manhã, e são exatamente as duas que são
puladas.

O ponto não é a burocracia. **Se você não consegue escrever o impacto e a
reversão, você não está pronto para descongelar, e acabou de descobrir isso
sozinho em vez de descobrir em produção.** Esse julgamento sai sozinho das três
linhas, e é por isso que funciona com agentes tão bem quanto com pessoas.

## O que melhora de verdade

**Você para de revisar tudo.**
Seu agente fez 34 commits durante a noite. Dois carregam linhas UNFREEZE. São
esses dois que você lê primeiro. O gate não deixou o agente mais cuidadoso. Fez
o agente te dizer onde ele saiu do caminho.

**"Ajusta o espaçamento" para de voltar com 12 arquivos alterados.**
Você pediu uma coisa. O diff tem aquilo, mais uma refatoração do cálculo de
impostos, mais uma limpeza de um laço de retry que só existe porque uma API
externa é instável. O agente não está sendo desleixado. Ele não consegue
distinguir qual código estranho é estranho por um motivo. Agora o código
estranho diz isso, no momento em que é tocado.

**A gambiarra que sustenta algo para de ser melhorada.**
Toda base de código tem uma linha que parece errada e está segurando alguma
coisa. Alguém arruma isso mais ou menos uma vez por trimestre, e quebra de um
jeito que ninguém liga à arrumação. `before_you_touch` é a placa pregada nessa
cerca, e ela aparece no terminal, não num arquivo que ninguém abre.

**Dá para ir dormir.**
Não porque o agente ficou cuidadoso. Porque a pior coisa que ele pode fazer
enquanto você não está agora é limitada por uma lista que você escreveu acordado.

**A regra para de depender de alguém lembrar dela.**
"Não mexa no layout mobile" é conselho. Um commit que não passa é informação. A
diferença não é educação. Um dos dois funciona às 3 da manhã, num modelo que
nunca te viu, no primeiro minuto dele no seu repositório.

## O que isto não faz

Não mede o quanto melhora. Não existe tabela de benchmark neste README porque
não existe jeito honesto de montar uma, e uma tabela inventada valeria menos que
os dois scripts.

Não procura segredos nem padrões inseguros. gitleaks e semgrep fazem isso melhor
do que qualquer coisa que fosse entregue aqui. Isto faz o que eles não fazem.

Não faz o agente escrever código melhor. Faz uma mudança errada ficar visível
antes de ir para produção. São problemas diferentes e isto cobre só o segundo.

Não substitui revisão. Elimina a classe de erro que a revisão pega pior: a
edição pequena, plausível e vizinha de algo que já estava certo.

## Instalação

```sh
git clone https://github.com/produckyou-design/agent-guardrails
./agent-guardrails/install.sh /caminho/do/seu-repo
```

Windows:

```powershell
.\agent-guardrails\install.ps1 C:\path\to\your-repo
```

Ou copie `gates/*.py` para o seu `scripts/`, coloque o hook de pre-commit e
adicione `.github/workflows/gates.yml`. Hooks locais dá para pular com
`--no-verify`, o job de CI não, então use os dois.

Comece com a lista de congelados vazia. Adicione o primeiro caminho no dia em
que um agente editar algo que você achava pronto. Não vai demorar.

## Como escrever uma entrada de congelamento que segura

Um caminho sem motivo é descongelado pelo próximo que precisar dele. O que
segura o congelamento é o `what_breaks`, porque quem descongela precisa saber o
que está arriscando.

```json
{
  "label": "Faturamento",
  "paths": ["src/billing/charge.py"],
  "reason": "Pronto e em produção. Não está em nenhum roadmap.",
  "what_breaks": "Conta errada ainda renderiza uma tela normal. Só o valor muda.",
  "before_you_touch": [
    "Reembolso parcial mora em refund.py, não aqui.",
    "Falha reverte a transação inteira. Não enfraquecer isso."
  ],
  "how_to_verify": "pytest tests/test_billing.py -q"
}
```

`before_you_touch` é onde as quedas vão parar. Cada linha ali deveria ser algo
aprendido do jeito caro.

## Não congele tudo

Se o congelamento cobre o repositório inteiro, o gate vira o menino que gritava
lobo, e as violações reais são ignoradas junto com o ruído. Deixe bem abertos os
caminhos que o seu roadmap está prestes a tocar.

O projeto de origem congela 19 caminhos de várias centenas.

## Testes

```sh
python tests/test_gates.py
```

16 testes. Eles constroem um repositório git real num diretório temporário, fazem
commits reais e rodam os gates como subprocessos. Nada é mockado, porque o que
está sendo testado é como os gates leem o git.

Também cobrem os bugs aprendidos do jeito caro, incluindo aquele em que declarar
`src/db/sync-notices.py` destravava silenciosamente `src/db/sync_orders.py`
porque uma regex comia o hífen.

Um repositório que defende que verificação precisa ser executável deveria
conseguir provar a própria. Enfraqueça a regra das três linhas e 3 testes falham.
Quebre o tratamento do hífen e o teste de caminho falha. Experimente.

## Também incluído

`FAILURE_MODES.md` tem os incidentes que geraram esses gates, no formato que os
tornou úteis:

```
Sintoma  como aparecia
Causa    por que aconteceu
Correção o que mudou
Regra    o que fazer daqui em diante
```

Um teste para saber se um incidente entra nesse arquivo: **se eu não escrever
isto, vou fazer de novo?** Se sim, entra, mesmo que nada tenha quebrado. O que
se repete quase nunca são as quedas dramáticas. São os loops pequenos em que
você cai todas as vezes.

`skill/SKILL.md` é a metade voltada ao agente: as regras de operação que
acompanham os gates. Gates pegam o que dá para checar mecanicamente. A skill
cobre o resto, como relatar com honestidade a verificação que você realmente
rodou.

## Licença

MIT. Pegue o que servir, descarte o resto.
