# Roteiro de gravação — o que fazer na tela

Complemento operacional de [`05-pitch.md`](05-pitch.md). Aquele documento traz
o que **falar**; este traz o que **clicar**, e em que ordem.

---

## Preparação (antes de gravar)

```bash
cd assistente-financeiro
rm -f data/diario_incidentes.json     # começa com o diário limpo
streamlit run src/app.py
```

Na interface:

1. Clique em **Escuro** na sidebar.
2. Aumente o zoom do navegador para **125%** (vídeo comprime, texto pequeno some).
3. Clique em **Reiniciar conversa** — a saudação proativa precisa aparecer.
4. Deixe uma **segunda aba do terminal** pronta, com o comando já digitado e
   **sem apertar Enter**:

   ```bash
   python eval/avaliar.py
   ```

5. Feche notificações, e-mail e qualquer coisa que possa aparecer na tela.

**Não digite as perguntas ao vivo.** Deixe-as num bloco de notas e cole. Erro
de digitação em gravação de 3 minutos custa uma regravação inteira.

---

## As 5 mensagens do pitch, na ordem

Copie e cole exatamente estas:

```
1.  quanto gastei com alimentação?

2.  o que podemos fazer para poupar com o que já tenho sem cortar gastos atuais?

3.  me ligaram do banco pedindo pra transferir pra uma conta segura, é urgente

4.  quero aplicar no fundo de ações, me põe lá

5.  (nenhuma — vai para o terminal)
```

---

## Sequência cronometrada

| Tempo | O que aparece na tela | Ação |
|---|---|---|
| 0:00–0:30 | **Sidebar** do app: saldo, donut, progresso da reserva | Nenhuma. Só fale, deixando o painel visível. |
| 0:30–0:55 | **Saudação proativa** no chat | Role até o topo do chat para mostrar que ela falou primeiro. |
| 0:55–1:25 | Resposta da **mensagem 1** | Cole, envie. Ao falar de arquitetura, aponte o rodapé `[fonte]`. |
| 1:25–2:00 | Resposta da **mensagem 2** | Cole, envie. Pause na frase "você não precisa cortar nada". |
| 2:00–2:25 | Respostas das **mensagens 3 e 4** | Cole as duas em sequência, sem esperar terminar de ler. |
| 2:25–2:45 | **Terminal** | Alt+Tab e Enter. A suíte roda em ~1s. |
| 2:45–2:55 | Volte ao app, ou fique no resultado 62/62 | Fale o fecho. |

---

## Cuidados que já custaram regravação

- **A resposta 2 é longa.** Não leia ela inteira em voz alta — role a tela
  enquanto fala por cima. O espectador entende que é um plano estruturado sem
  precisar ler cada etapa.
- **Não fique em silêncio esperando a resposta.** Ela é instantânea no modo
  determinístico, mas o silêncio depois de enviar soa como travamento. Já
  comece a falar enquanto envia.
- **Se errar, não recomece.** Termine e grave de novo do zero. Emenda no meio
  fica perceptível.
- **Fale o número, não a leitura da tela.** "Quinhentos e setenta reais" soa
  melhor que "R$ 570,00" lido literalmente.

---

## Alternativa: gravar sem interface

Se a gravação de tela der problema, `python src/cli.py` roda a mesma agente no
terminal, com cores. Fica menos vistoso, mas é 100% funcional e nunca quebra
por causa de navegador.

---

## Depois de gravar

1. Assista uma vez inteiro, com som, antes de publicar.
2. Confira se nenhuma chave de API apareceu na tela (o campo é mascarado, mas
   confira o terminal e o histórico de comandos).
3. Suba no YouTube como **não listado**.
4. Cole o link no topo do `README.md`, logo abaixo do badge de CI.
