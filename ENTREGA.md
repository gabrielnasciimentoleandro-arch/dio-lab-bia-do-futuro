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

O roteiro cronometrado está em [`docs/05-pitch.md`](docs/05-pitch.md), dividido
em problema -> como funciona -> por que é inovador, com as frases-âncora
destacadas e uma tabela de perguntas prováveis da banca.

Sugestão de gravação:

- Deixe o app rodando em modo escuro antes de começar.
- Mostre **uma** interação ao vivo — a melhor é o plano com veto
  (*"sem cortar gastos atuais"*), porque exibe os quatro pilares de uma vez.
- Termine no relatório `eval/resultado.md` com os 62 casos.
- Suba o vídeo no YouTube como *não listado* e cole o link no README.

---

## 4. O que ainda depende de você

| Pendência | Onde |
|---|---|
| Trocar `SEU-USUARIO/SEU-REPO` no badge | `README.md`, linha 11 |
| Testar com chave Gemini real | Cole no campo da sidebar ou use `.env` |
| Preencher a avaliação humana (3-5 pessoas) | Aplique `eval/formulario-avaliacao.md` e transcreva em `docs/04-metricas.md`, seção 4.9 |
| Gravar e linkar o pitch | `docs/05-pitch.md` |

A avaliação humana é a única seção com espaços em branco propositais: o
desafio pede pessoas reais avaliando de 1 a 5, e isso não dá para simular.
O formulário pronto está em `eval/formulario-avaliacao.md` — mande para 3 a 5
pessoas, de perfis diferentes, e transcreva as notas na seção 4.9.

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
