# 5. Pitch — 3 minutos

## Roteiro para gravação

> Tempo alvo: **2min55s**. Cronometre. Três minutos passam rápido.

---

### 🎬 Abertura — O problema (0:00 – 0:35)

> "Esse é o João. 32 anos, analista de sistemas, ganha cinco mil reais por mês.
>
> E o João faz tudo certo: ele poupa **50% da renda**. Cinquenta por cento.
>
> Mesmo assim, a reserva de emergência dele está parada em dez mil, de uma meta de quinze mil. E o prazo que ele mesmo definiu — junho de 2026 — **já passou**.
>
> O problema do João não é falta de dinheiro. É falta de direção.
>
> O aplicativo do banco mostra o extrato dele. Mas extrato é histórico. Ninguém diz pro João o que fazer **amanhã**."

**Tela:** dashboard lateral do app — saldo R$ 2.511,10, barra de progresso em 66,7%.

---

### 🎬 A solução (0:35 – 1:05)

> "Essa é a **Luma**, uma agente financeira consultiva.
>
> Repare: eu ainda não perguntei nada. E ele já abre assim:
>
> *'Olá, João. Dei uma olhada nos seus números antes de você perguntar: faltam cinco mil reais para a sua reserva. No seu ritmo, dá pra fechar em dois meses — mas o prazo de junho já passou.'*
>
> Ele não esperou a pergunta. Ele **antecipou**."

**Tela:** abrir o app, mostrar a saudação proativa.

---

### 🎬 Demonstração (1:05 – 2:20)

**Demo 1 — precisão e fonte** *(15s)*

> "Quanto gastei com alimentação?"
>
> "R$ 570,00, em dois lançamentos. E aqui está o detalhe que muda tudo: **📎 Fonte: transacoes.csv, dois registros**.
>
> Todo número que a Luma fala vem com a origem. Você pode auditar."

**Demo 2 — o diferencial técnico** *(25s)*

> "E por que eu confio nesse número?
>
> Porque **a Luma não faz essa conta**.
>
> A inteligência artificial só interpreta a pergunta e escolhe qual ferramenta chamar. Quem soma é o Python. O modelo recebe o resultado pronto e escreve a frase.
>
> Ou seja: meu agente é **matematicamente incapaz de errar um valor** — porque ele não é quem faz a conta.
>
> Isso não é um prompt pedindo 'por favor não invente'. É arquitetura."

**Tela:** diagrama do fluxo, destacando LLM → ferramenta → Python → LLM.

**Demo 3 — o escudo antifraude** *(25s)*

> "Mas tem uma coisa que me incomodou enquanto eu construía isso.
>
> De que adianta a Luma economizar cento e oitenta e sete reais por mês pro João, se **um único golpe de Pix leva oitocentos numa tarde**?
>
> Então ela ganhou um segundo pilar. Olha só:
>
> *'Me ligaram do banco pedindo pra transferir pra uma conta segura, é urgente.'*
>
> **Risco ALTO. Isso tem cara de golpe. Não avance.**
>
> Ela identificou o padrão — falso funcionário — listou os sinais, disse o que fazer, e fechou com: **'conta segura não existe, é sempre golpe'**.
>
> E de novo: não é o modelo achando que é golpe. É o Python contando marcadores objetivos no relato."

**Tela:** a resposta de risco ALTO com os sinais listados.

**Demo 4 — o diário de aprendizado** *(20s)*

> "E se a pessoa já caiu?
>
> *'Caí no golpe do pix e perdi oitocentos reais.'*
>
> Repare como ela começa:
>
> **'Sinto muito. E quero dizer uma coisa antes de tudo: cair em golpe não é burrice.'**
>
> Isso não é enfeite — está no meu caso de teste, com asserção obrigatória. Porque vergonha faz a vítima calar, e o silêncio é o que permite o **segundo** golpe.
>
> Aí ela registra no diário, guarda a lição e orienta o boletim de ocorrência.
>
> Essa é a única base do projeto **que cresce com o uso**. Cada golpe sofrido vira defesa futura."

**Tela:** a resposta acolhedora + o card do diário na sidebar.

**Demo 5 — compliance** *(20s)*

> "Agora o teste difícil. Vou pedir uma coisa que o João não deveria fazer:
>
> *'Me põe no Fundo de Ações, quero ganhar mais.'*
>
> E a Luma **recusa**:
>
> *'Entendo a vontade de acelerar os ganhos, mas o Fundo de Ações é de risco alto, e você declarou não aceitar risco. Além disso, sua reserva ainda não está completa — ela é o colchão que evita resgatar investimento na pior hora.'*
>
> Um chatbot vendedor teria aceitado. A Luma protege o cliente **do próprio cliente**."

---

### 🎬 Prova (2:20 – 2:40)

> "E eu não estou pedindo pra você acreditar. Um comando:
>
> `python eval/avaliar.py`
>
> Quarenta e sete casos automatizados. **Cem por cento de aprovação.**
>
> E dez desses casos são ataques: prompt injection, pedido de senha, produto que não existe, promessa de rentabilidade. A Luma bloqueou todos.
>
> Inclusive: quando eu pergunto sobre um fundo inventado, ele responde **'não tenho esse dado e não vou arriscar um palpite'**.
>
> Num banco, saber dizer 'não sei' vale mais do que parecer inteligente."

**Tela:** terminal rodando a suíte, linhas verdes, resultado 25/25.

---

### 🎬 Fechamento (2:40 – 2:55)

>
> "A Luma mostra duas coisas.
>
> Primeiro: um agente financeiro confiável não nasce de um prompt melhor. Nasce de **arquitetura** — separar quem calcula de quem conversa. A IA faz o que faz bem, entender gente. O código faz o que faz bem, não errar conta.
>
> Segundo: assistente financeiro de verdade não serve só para otimizar rendimento. Serve para **proteger**. Porque o maior risco do brasileiro hoje não é escolher o CDB errado — é o telefone tocando com uma história urgente do outro lado.
>
> E o João? Sai da conversa sabendo o próximo passo. E um pouco mais difícil de enganar.
>
> Obrigado."

---

## Estrutura resumida

| Tempo | Bloco | Mensagem central |
|---|---|---|
| 0:00–0:35 | Problema | Poupa 50% e mesmo assim não bate a meta. Falta direção, não dinheiro. |
| 0:35–1:05 | Solução | Agente proativo que fala antes de ser perguntado |
| 1:05–2:20 | Demo | Precisão com fonte · LLM não calcula · **antifraude** · **diário** · compliance |
| 2:20–2:40 | Prova | 45 casos, 100%, 12 ataques bloqueados |
| 2:40–2:55 | Fecho | Arquitetura > prompt · proteger vale mais que otimizar |

---

## Frases-âncora

Se esquecer o roteiro, essas três sustentam o pitch:

1. **"O problema do João não é falta de dinheiro. É falta de direção."**
2. **"Meu agente é matematicamente incapaz de errar um valor, porque ele não é quem faz a conta."**
3. **"Num banco, saber dizer 'não sei' vale mais do que parecer inteligente."**
4. **"De que adianta economizar R$ 187 por mês se um golpe de Pix leva R$ 800 numa tarde?"**
5. **"Cair em golpe não é burrice — e isso está no meu caso de teste."**
6. **"Cortei uma funcionalidade que já estava pronta e testada, porque ela falava fora da base. Escopo também é segurança."**

---

## Checklist de gravação

- [ ] App aberto e testado **antes** de gravar
- [ ] Terminal com a suíte já pronta para rodar (não digitar ao vivo)
- [ ] Zoom da fonte aumentado — vídeo comprime
- [ ] Cronometrar: cortar a demo antes do fechamento, nunca o contrário
- [ ] Falar mais devagar do que parece natural
- [ ] Áudio limpo importa mais que imagem bonita

## Perguntas prováveis da banca

| Pergunta | Resposta curta |
|---|---|
| "Por que não usou RAG?" | 20 registros cabem no contexto. E RAG não resolve aritmética — recuperar o CSV certo não impede o modelo de somar errado. |
| "Escala para milhares de transações?" | As ferramentas sim (é filtro e soma). Acima de ~10 mil registros, migraria para SQL e usaria RAG só para busca textual. |
| "E se o modelo ignorar o system prompt?" | Os guardrails críticos estão em código, fora do modelo. Produto incompatível é filtrado na origem — o LLM nunca o vê como opção. |
| "Por que o modo demo?" | Para o avaliador conseguir rodar sem chave de API. Um projeto que não roda não é avaliado. |
| "A detecção de golpe usa IA?" | Não. É contagem determinística de marcadores objetivos no relato. O LLM redige, mas não decide o nível de risco. |
| "E se der falso positivo?" | Testei frases inofensivas com vocabulário próximo: retorna INDETERMINADO. Um detector que grita sempre é ignorado quando importa. |
| "Quem alimenta a base de golpes?" | Hoje é curada, com referência em Febraban, Banco Central e CERT.br. Em produção, entraria um feed oficial. |
| "Por que a Luma não ajuda com celular infectado?" | Porque a base dela não tem nada sobre hardware. Um agente financeiro opinando sobre aparelho está alucinando com boa intenção. Ela recusa e reconduz — e isso é um caso de teste. |
