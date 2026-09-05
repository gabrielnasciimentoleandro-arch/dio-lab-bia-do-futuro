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

1. Faça o **fork** do repositório oficial `digitalinnovationone/dio-lab-bia-do-futuro`.
2. Copie o conteúdo deste projeto para o fork.
3. Abra o `README.md` e troque, na linha 11, `SEU-USUARIO/SEU-REPO` pelo seu
   caminho real — é o badge de CI. Sem isso ele aparece quebrado.
4. Commit e push.
5. Confira a aba **Actions**: a suíte deve rodar sozinha e ficar verde.

```bash
git add -A
git commit -m "Luma: agente financeira com function calling determinístico"
git push
```

**Não suba a sua chave de API.** O `.gitignore` já cobre `.env`, mas confira
com `git status` antes do push.

---

## 3. Gravar o pitch (3 minutos)

O roteiro cronometrado está em [`docs/05-pitch.md`](docs/05-pitch.md) — 407
palavras, medidas em 2min54s — e o passo a passo de tela em
[`docs/05b-roteiro-gravacao.md`](docs/05b-roteiro-gravacao.md). Dividido
em problema -> como funciona -> por que é inovador, com as frases-âncora
destacadas e uma tabela de perguntas prováveis da banca.

Para ensaiar, há narração sintetizada de todo o roteiro em `audio/`
(`00-pitch-completo.mp3`, 2min56s). É material de ensaio: o pitch enviado
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
