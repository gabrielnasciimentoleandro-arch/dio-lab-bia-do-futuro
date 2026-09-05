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
*Fork*, no canto superior direito do GitHub. Anote o nome do repositório criado
(normalmente `dio-lab-bia-do-futuro`) e o seu usuário.

**2. Rode o script de publicação**, passando usuário e repositório:

```bash
./publicar.sh SEU-USUARIO dio-lab-bia-do-futuro
```

Ele faz tudo o que é chato e fácil de esquecer:

- troca o `SEU-USUARIO/SEU-REPO` do badge de CI pelo caminho real;
- apaga o diário de incidentes e os `__pycache__`;
- roda as duas suítes e regenera os exemplos (o CI roda as mesmas — se falhar
  aqui, falharia lá);
- confere se alguma chave de API vazou no histórico e **aborta** se achar;
- cria o commit do ajuste.

Ao final, ele imprime os dois comandos do passo seguinte, já preenchidos.

**3. Conecte e envie:**

```bash
git remote add origin https://github.com/SEU-USUARIO/dio-lab-bia-do-futuro.git
git push --force origin main
```

O `--force` é necessário porque o seu histórico e o do template são
independentes. Como o fork acabou de ser criado, não há nada a perder.

**4. Se preferir fazer à mão**, o único passo obrigatório é editar a linha 11
do `README.md`, trocando `SEU-USUARIO/SEU-REPO`. O resto do script é
conferência.

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

### Com o que gravar

Você precisa de algo que capture **tela + microfone ao mesmo tempo**. Em ordem
de facilidade:

| Ferramenta | Como |
|---|---|
| **Gravador do Windows** | `Win + Alt + R`. Já vem instalado, grava a janela ativa. |
| **OBS Studio** | Gratuito, todos os sistemas. Mais controle, um pouco mais de configuração. |
| **Google Meet** | Abra uma reunião sozinho, compartilhe a tela e grave. Salva direto no Drive. |
| **Celular apontado para a tela** | Último recurso. Funciona, mas o texto fica ilegível. |

Grave em **1080p** se puder. O avaliador precisa ler os números na tela.

### Preparação

Tudo está em [`docs/05b-roteiro-gravacao.md`](docs/05b-roteiro-gravacao.md),
com as mensagens prontas para colar. O resumo:

```bash
rm -f data/diario_incidentes.json
streamlit run src/app.py
```

Depois, na interface: modo **Escuro**, zoom do navegador em **125%**, e clique
em **Reiniciar conversa** para a saudação proativa aparecer. Deixe o terminal
com `python eval/avaliar.py` já digitado, sem apertar Enter.

Feche e-mail, notificações e qualquer coisa que possa aparecer na tela.

### A sequência

Cinco momentos, na ordem do roteiro:

1. Painel lateral (fale o problema do João)
2. Saudação proativa (ela fala primeiro)
3. `quanto gastei com alimentação?`
4. `o que podemos fazer para poupar com o que já tenho sem cortar gastos atuais?`
5. Terminal com a suíte -> fecho

### O que mais atrapalha

- **Digitar ao vivo.** Deixe as perguntas num bloco de notas e cole.
- **Silêncio esperando a resposta.** Comece a falar enquanto envia.
- **Ler a tela em voz alta.** Fale "quinhentos e setenta reais", não "erre
  cifrão quinhentos e setenta".
- **Tentar consertar no meio.** Se errar, termine e regrave do zero.

Ensaie com o áudio de `audio/00-pitch-completo-com-trilha.mp3` tocando, falando
por cima. É o jeito mais rápido de pegar o ritmo.

### Publicar

Suba no **YouTube como "não listado"** (aparece só para quem tem o link) e cole
o link no topo do `README.md`, logo abaixo dos badges:

```markdown
**[Assista ao pitch de 3 minutos](https://youtu.be/SEU-VIDEO)**
```

Alternativas: Google Drive com link público, ou Loom.

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
