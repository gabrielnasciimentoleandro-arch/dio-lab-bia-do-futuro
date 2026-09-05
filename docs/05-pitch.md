# 5. Pitch — 3 minutos

## Roteiro para gravação

> Tempo alvo: **2min55s**. Tudo em `>` é para falar; o resto é indicação de
> tela.
>
> **Medição:** 407 palavras de fala = **2min54s** a 140 palavras por minuto,
> que é ritmo de apresentação calmo. A margem é curta de propósito — se você
> fala rápido, sobra tempo para as pausas de demonstração; se fala devagar,
> use a lista "Se o tempo apertar" mais abaixo.
>
> Todos os valores citados foram conferidos contra as ferramentas: alimentação
> R$ 570,00 em 2 lançamentos, saldo R$ 2.511,10 (50,2% da renda), faltam
> R$ 5.000,00 para a reserva, prazo de junho de 2026 vencido.

---

### Problema (0:00 – 0:30)

> "Esse é o João. Ganha cinco mil por mês e poupa metade disso — cinquenta por
> cento da renda.
>
> Mesmo assim, a reserva dele está travada em dez mil, de uma meta de quinze. E
> o prazo que ele mesmo marcou já venceu.
>
> O problema do João não é falta de dinheiro. É falta de direção.
>
> O banco mostra o extrato. Extrato é passado — ninguém diz o que fazer amanhã."

**Tela:** painel lateral — saldo R$ 2.511,10, reserva em 66,7%.

---

### Solução (0:30 – 0:55)

> "Essa é a Luma.
>
> Repare que eu ainda não perguntei nada, e ela já abre assim: *faltam cinco
> mil para a sua reserva; no seu ritmo dá para fechar em dois meses, mas o
> prazo de junho já passou.*
>
> Ela não esperou a pergunta. Antecipou."

**Tela:** abrir o app, saudação proativa.

---

### Demo 1 — Precisão e arquitetura (0:55 – 1:25)

> "*Quanto gastei com alimentação?*
>
> Quinhentos e setenta reais, em dois lançamentos — e embaixo, a fonte:
> transacoes.csv.
>
> Por que eu confio nesse número? Porque **a Luma não faz essa conta**. A IA só
> interpreta a pergunta e escolhe qual ferramenta chamar. Quem soma é o Python.
>
> Minha agente é matematicamente incapaz de errar um valor, porque ela não é
> quem calcula. Isso não é um prompt pedindo 'não invente'. É arquitetura."

**Tela:** resposta com o rodapé de fonte; depois `assets/arquitetura.svg`.

---

### Demo 2 — Cocriação com restrição (1:25 – 2:00)

> "Agora o teste que eu mais gosto. O João pede: *como poupar sem cortar meus
> gastos atuais?*
>
> Um assistente comum sugere cortar alimentação e lazer — ignora a única regra
> que o cliente deu.
>
> A Luma responde: **você não precisa cortar nada.** Já sobram dois mil e
> quinhentos por mês. O problema não é quanto sobra, é que fica solto na conta.
>
> E entrega um plano em quatro etapas que termina perguntando o que ajustar.
>
> Cocriar é obedecer à restrição do cliente."

**Tela:** o plano com a abertura "você não precisa cortar nada".

---

### Demo 3 — Proteção (2:00 – 2:25)

> "*Me ligaram do banco pedindo para transferir para uma conta segura.*
>
> Risco alto, cara de golpe, não avance. E de novo: é o Python contando
> marcadores objetivos, não o modelo achando.
>
> E quando o João pede o Fundo de Ações, ela **recusa** — risco alto, e a
> reserva dele ainda não está pronta.
>
> Um chatbot vendedor teria aceitado."

**Tela:** alerta de risco ALTO; depois a recusa do fundo.

---

### Prova (2:25 – 2:45)

> "Um comando: `python eval/avaliar.py`. Sessenta e dois casos, cem por cento.
> Dezesseis são ataques — injection, pedido de senha, produto inexistente,
> promessa de rentabilidade.
>
> Mas o número que eu levo é outro: **dezessete falhas documentadas, onze delas
> achadas conversando com ela** enquanto a suíte marcava cem por cento."

**Tela:** terminal com a suíte verde, 62/62.

---

### Fecho (2:45 – 2:55)

> "Agente financeiro confiável não nasce de um prompt melhor. Nasce de
> arquitetura: separar quem calcula de quem conversa.
>
> E num banco, saber dizer 'não sei' vale mais do que parecer inteligente.
>
> Obrigado."

---

## Estrutura resumida

| Tempo | Bloco | Mensagem central |
|---|---|---|
| 0:00–0:30 | Problema | Poupa 50% e não bate a meta. Falta direção, não dinheiro. |
| 0:30–0:55 | Solução | Agente proativo: fala antes de ser perguntado |
| 0:55–1:25 | Demo 1 | Número com fonte · o LLM não calcula |
| 1:25–2:00 | Demo 2 | Cocriação que obedece ao veto do cliente |
| 2:00–2:25 | Demo 3 | Antifraude e recusa de produto incompatível |
| 2:25–2:45 | Prova | 62 casos, 100% · 17 falhas documentadas |
| 2:45–2:55 | Fecho | Arquitetura > prompt · saber dizer "não sei" |

---

## Se o tempo apertar

Corte nesta ordem, sem dó:

1. **Demo 3 inteira** (25s) — o antifraude é ótimo, mas é o pilar mais
   periférico ao enunciado.
2. A segunda metade da **Prova** (10s), ficando só "62 casos, 100%".
3. A frase do extrato na abertura (7s).

**Nunca corte:** a Demo 1 (é a tese técnica) e a Demo 2 (é o pilar cocriar, e
é a parte mais difícil de replicar).

---

## Frases-âncora

Se travar, qualquer uma destas sustenta o pitch sozinha:

1. **"O problema do João não é falta de dinheiro. É falta de direção."**
2. **"Minha agente é matematicamente incapaz de errar um valor, porque ela não é quem faz a conta."**
3. **"Num banco, saber dizer 'não sei' vale mais do que parecer inteligente."**
4. **"Ele pediu um plano para poupar sem cortar nada, e ela respondeu sugerindo cortes. Cocriar é obedecer à restrição do cliente."**
5. **"Minha suíte marcava 100% enquanto onze bugs estavam vivos. Cobertura de teste herda o viés de quem escreve os testes."**
6. **"Cortei uma funcionalidade pronta e testada porque ela falava fora da base. Escopo também é segurança."**
7. **"Zero significava 'inalcançável' e a tela mostrava como boa notícia."**
8. **"De que adianta economizar R$ 187 por mês se um golpe de Pix leva R$ 800 numa tarde?"**
9. **"Eu sei exatamente o que falta neste projeto, e está escrito no README. Protótipo que não declara seus limites está escondendo alguma coisa."**

---

## Áudio de referência

Narração sintetizada do roteiro inteiro em [`audio/`](../audio/) —
`00-pitch-completo.mp3` tem **2min56s**, e cada bloco está separado para
ensaio. Serve para conferir ritmo e cronometragem antes de gravar com a sua
voz. Detalhes em [`audio/LEIA-ME.md`](../audio/LEIA-ME.md).

---

## Checklist de gravação

> Passo a passo do que clicar, com as mensagens prontas para colar, em
> [`05b-roteiro-gravacao.md`](05b-roteiro-gravacao.md).

- [ ] App **já aberto e testado** antes de apertar o rec — nada de digitar comando ao vivo
- [ ] Modo escuro ligado (fica melhor em vídeo comprimido)
- [ ] Conversa reiniciada, para a saudação proativa aparecer
- [ ] Terminal com a suíte pronta em outra aba
- [ ] Zoom da fonte aumentado — vídeo comprime e some texto pequeno
- [ ] Cronômetro visível
- [ ] Falar mais devagar do que parece natural
- [ ] Áudio limpo importa mais que imagem bonita
- [ ] Gravar duas vezes e ficar com a segunda

---

## Perguntas prováveis da banca

| Pergunta | Resposta curta |
|---|---|
| "Por que não usou RAG?" | 20 registros cabem no contexto. E RAG não resolve aritmética — recuperar o CSV certo não impede o modelo de somar errado. |
| "Escala para milhares de transações?" | As ferramentas sim (é filtro e soma). Acima de ~10 mil registros, migraria para SQL e usaria RAG só para busca textual. |
| "E se o modelo ignorar o system prompt?" | Os guardrails críticos estão em código, fora do modelo. Produto incompatível é filtrado na origem — o LLM nunca o vê como opção. |
| "Por que o modo determinístico?" | Para o avaliador conseguir rodar sem chave de API. Um projeto que não roda não é avaliado. |
| "A detecção de golpe usa IA?" | Não. É contagem determinística de marcadores objetivos no relato. O LLM redige, mas não decide o nível de risco. |
| "E se der falso positivo?" | Testei frases inofensivas com vocabulário próximo: retorna INDETERMINADO. Um detector que grita sempre é ignorado quando importa. |
| "Quem alimenta a base de golpes?" | Hoje é curada, com referência em Febraban, Banco Central e CERT.br. Em produção, entraria um feed oficial. |
| "Como você testou além da suíte?" | Conversa exploratória sem roteiro. Das 17 falhas documentadas, 11 vieram daí — a suíte marcava 100% enquanto elas existiam. O método está em `docs/04-metricas.md`, secao 4.8, e todo achado virou caso de teste: o projeto foi de 24 para 62 casos. |
| "Sua suíte tem 100%. Isso não é suspeito?" | É, e por isso mantenho duas. A de 62 casos testa o agente contra a base real; `eval/testar_calculos.py` testa as ferramentas com dados sintéticos, incluindo mês no vermelho. Foi essa segunda que pegou a agente dizendo "dá para fechar em 0 mês(es)" com saldo negativo. |
| "O que falta para ir para produção?" | Persistência e multi-cliente, memória entre sessões, e um juiz-modelo na avaliação — hoje os testes checam substring, o que já me deu falso negativo. Está listado em "Limites conhecidos" no README, com a razão de cada corte. |
| "Por que a Luma não ajuda com celular infectado?" | Porque a base dela não tem nada sobre hardware. Um agente financeiro opinando sobre aparelho está alucinando com boa intenção. Ela recusa e reconduz — e isso é um caso de teste. |
