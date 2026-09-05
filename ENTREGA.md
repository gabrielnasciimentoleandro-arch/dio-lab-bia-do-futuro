# Guia de entrega

Checklist para publicar o projeto. Este arquivo é para você, não para o
avaliador — pode apagar antes do envio final se preferir.

---

## 1. Antes de publicar

```bash
# na pasta do projeto
rm -f data/diario_incidentes.json     # arquivo de runtime, não vai para o repo
python eval/testar_calculos.py        # 19 testes unitários
python eval/avaliar.py                # 62 casos — precisa dar 100%
python examples/gerar_exemplos.py     # regenera as transcrições
```

Os três precisam terminar sem erro. `avaliar.py` sai com código 1 se qualquer
caso falhar, então a CI reprova sozinha se algo quebrar.

---

## 2. Publicar no GitHub

### Fork ou repositório novo?

**Faça o fork.** É o caminho recomendado, por três motivos:

1. O fork cria um vínculo visível com o repositório oficial da DIO. Quem abrir
   o seu vê "forked from digitalinnovationone/dio-lab-bia-do-futuro".
2. Você aparece na lista de forks do repo oficial — que é justamente onde os
   avaliadores procuram os projetos entregues.
3. Se a DIO pedir Pull Request, só é possível a partir de um fork.

Repositório novo do zero funcionaria tecnicamente, mas você perde a
rastreabilidade e corre o risco de o projeto não ser encontrado.

> O seu histórico de commits **não se perde** no processo abaixo. Ele é
> preservado inteiro, com os 18 commits que contam a evolução do projeto — e
> esse histórico é argumento a seu favor: mostra as decisões e correções, não
> um despejo de código pronto.

### Passo a passo

**1. Faça o fork** de `digitalinnovationone/dio-lab-bia-do-futuro` pelo botão
*Fork* no GitHub.

**2. Conecte o seu repositório local ao fork.** Na pasta do projeto:

```bash
git remote add origin https://github.com/SEU-USUARIO/dio-lab-bia-do-futuro.git
```

**3. Troque o badge de CI** no `README.md`, linha 11: substitua
`SEU-USUARIO/SEU-REPO` pelo caminho real. Sem isso o badge aparece quebrado.

```bash
git add README.md
git commit -m "Ajusta badge de CI para o repositorio publicado"
```

**4. Envie.** O seu projeto substitui o conteúdo do template — é isso mesmo que
se espera, já que os arquivos oficiais são modelos a preencher:

```bash
git push --force origin main
```

O `--force` é necessário porque o seu histórico e o do template são
independentes. Como o fork é seu e acabou de ser criado, não há o que perder.

> Se preferir preservar os commits originais do template, use
> `git pull origin main --allow-unrelated-histories` antes do push e resolva os
> conflitos. Dá mais trabalho e não agrega à avaliação.

**5. Confira a aba Actions.** A suíte roda sozinha e deve ficar verde. Se o
GitHub pedir para habilitar Actions no fork, autorize.

**6. Confira que nenhuma chave vazou:**

```bash
git log -p | grep -oE "AIza[A-Za-z0-9_-]{30,}" | head
```

Sem resultado = seguro. Chaves do Google AI Studio começam com `AIza`. As
ocorrências de `GOOGLE_API_KEY=sua_chave` na documentação são exemplos, não
credenciais.

Já verificado neste projeto: nenhuma chave real no histórico, e o `.gitignore`
cobre `.env`, `__pycache__` e o diário de incidentes.

---

## 3. Gravar o pitch (3 minutos)

O roteiro cronometrado está em [`docs/05-pitch.md`](docs/05-pitch.md) — 407
palavras, medidas em 2min54s — e o passo a passo de tela em
[`docs/05b-roteiro-gravacao.md`](docs/05b-roteiro-gravacao.md). Dividido
em problema -> como funciona -> por que é inovador, com as frases-âncora
destacadas e uma tabela de perguntas prováveis da banca.

Para ensaiar, há narração sintetizada de todo o roteiro em `audio/`
(`00-pitch-completo.mp3`, 2min25s). É material de ensaio: o pitch enviado
deve ser gravado com a sua voz.

Sugestão de gravação:

- Deixe o app rodando em modo escuro antes de começar.
- Mostre **uma** interação ao vivo — a melhor é o plano com veto
  (*"sem cortar gastos atuais"*), porque exibe os quatro pilares de uma vez.
- Termine no relatório `eval/resultado.md` com os 62 casos.
- Suba o vídeo no YouTube como *não listado* e cole o link no README.

---

## 4. O que ainda depende de você

### Obrigatório antes de enviar

| Pendência | Onde |
|---|---|
| Trocar `SEU-USUARIO/SEU-REPO` no badge | `README.md`, linha 11 |
| Gravar e linkar o pitch | `docs/05-pitch.md` |

### Opcional (o projeto está entregável sem isso)

| Item | Onde |
|---|---|
| Testar com chave Gemini real | Cole no campo da sidebar ou use `.env` |
| Coletar a avaliação humana | Aplique `eval/formulario-avaliacao.md` e transcreva em `docs/04-metricas.md`, seção 4.9 |

Sobre a avaliação humana: o enunciado a apresenta como **dica opcional**
(`[!TIP]`), não como requisito. A avaliação exigida é a estruturada, e ela está
completa — 62 casos, 19 testes unitários, 17 falhas documentadas. A seção 4.9
fica honestamente em branco, com o formulário pronto ao lado.

Se sobrar tempo antes do envio, aplicar em 3 pessoas já agrega: o valor não está
na nota, está no que alguém de fora tenta e você não imaginou. Se não sobrar,
entregue como está — uma seção declarada em branco é melhor que uma tabela
inventada.

---

## 5. Se pedirem para rodar na hora

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

Funciona **sem chave de API**. Sem chave, a Luma responde pelo motor
determinístico sobre as mesmas 16 ferramentas; com chave, o Gemini passa a
redigir via function calling. Em ambos os modos, nenhum número é gerado pelo
modelo.

Alternativa sem interface gráfica:

```bash
python src/cli.py
```
