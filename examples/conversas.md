# Exemplos de interação

> Transcrições **geradas automaticamente** por `examples/gerar_exemplos.py`, executando a agente em modo determinístico (sem chave de API). Cada turno mostra as ferramentas realmente acionadas.

Para regerar após qualquer mudança de comportamento:

```bash
python examples/gerar_exemplos.py
```

---

## Consulta de gastos e simulação

*O caminho mais comum:* o cliente pergunta para onde foi o dinheiro, aceita a oferta da agente e recebe uma simulação com restrição.

**Cliente:** oi

**Luma:**

> Olá, João! Tudo bem por aqui.
>
> Sua reserva de emergência está **66.7% concluída** — faltam **R$ 5.000,00**.
>
> Posso te ajudar com:
> - Gastos por categoria (*"quanto gastei com alimentação?"*)
> - Progresso das metas (*"quanto falta pra minha meta?"*)
> - Simulação de economia (*"simule um corte de 30%"*)
> - Segurança contra golpes (*"recebi uma ligação suspeita"*)
>
> O que você quer ver primeiro?
>
> [fonte] data/perfil_investidor.json + data/transacoes.csv

<sub>Ferramentas: `progresso_metas`</sub>

---

**Cliente:** quanto gastei com alimentação?

**Luma:**

> Você gastou **R$ 570,00** com alimentação, em 2 lançamento(s): Supermercado (R$ 450,00), Restaurante (R$ 120,00).
>
> Quer que eu simule quanto sobraria cortando 30% dessa categoria?
>
> [fonte] data/transacoes.csv (2 registros)

<sub>Ferramentas: `somar_por_categoria`</sub>

---

**Cliente:** sim

**Luma:**

> Simulei um corte de **30%** em **alimentação, lazer**:
>
> - Economia mensal: **R$ 187,77**
> - Em 12 meses: **R$ 2.253,24**
> - Saldo mensal iria de R$ 2.511,10 para **R$ 2.698,87**
> - Reserva completa em **2 mês(es)** — o mesmo prazo de antes: aqui o gargalo não é o gasto
>
> Se quiser ir além, **moradia** ainda tem R$ 1.380,00 — cortar 30% aí renderia mais R$ 414,00.
>
> Quer que eu detalhe onde está esse gasto?
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json

<sub>Ferramentas: `simular_economia`</sub>

---

**Cliente:** simule um corte de 30%

**Luma:**

> Simulei um corte de **30%** em **alimentação, lazer**:
>
> - Economia mensal: **R$ 187,77**
> - Em 12 meses: **R$ 2.253,24**
> - Saldo mensal iria de R$ 2.511,10 para **R$ 2.698,87**
> - Reserva completa em **2 mês(es)** — o mesmo prazo de antes: aqui o gargalo não é o gasto
>
> Se quiser ir além, **moradia** ainda tem R$ 1.380,00 — cortar 30% aí renderia mais R$ 414,00.
>
> Quer que eu detalhe onde está esse gasto?
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json

<sub>Ferramentas: `simular_economia`</sub>

---

**Cliente:** moradia eu não posso cortar

**Luma:**

> Respeitei sua restrição: deixei **moradia** de fora.
>
> Simulei um corte de **30%** em **alimentação, lazer**:
>
> - Economia mensal: **R$ 187,77**
> - Em 12 meses: **R$ 2.253,24**
> - Saldo mensal iria de R$ 2.511,10 para **R$ 2.698,87**
> - Reserva completa em **2 mês(es)** — o mesmo prazo de antes: aqui o gargalo não é o gasto
>
> Se quiser ir além, **transporte** ainda tem R$ 295,00 — cortar 30% aí renderia mais R$ 88,50.
>
> Quer que eu detalhe onde está esse gasto?
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json

<sub>Ferramentas: `simular_economia`</sub>

---

## Cocriação de plano com restrição do cliente

O pilar **cocriar**. O cliente veta cortes e a agente precisa montar um plano que respeite o veto — e ainda encurtá-lo quando ele pede.

**Cliente:** vamos bolar um plano para poupar nosso dinheiro?

**Luma:**

> Vamos montar juntos, João. Parti do que a sua base já mostra: você fecha o mês com R$ 2.511,10 e faltam R$ 5.000,00 para a reserva.
>
> **1. Automatizar o que já sobra**
> Você já fecha o mês com R$ 2.511,10 — 50.2% da renda. O problema não é o quanto sobra, é que sobra solto. Programe uma transferência automática no dia do salário.
> *Resultado:* R$ 2.511,10/mês indo para a reserva sem depender de disciplina
>
> **2. Colocar a reserva para render**
> Reserva de emergência precisa de liquidez diária, não de rentabilidade alta. Compatíveis com seu perfil moderado: Tesouro Selic ou CDB Liquidez Diária. O Tesouro Selic rende 100% da Selic, risco baixo.
> *Resultado:* O mesmo dinheiro, rendendo em vez de parado na conta
>
> **3. Fechar a reserva**
> Faltam R$ 5.000,00. Mantendo R$ 2.511,10/mês, dá para fechar em 2 mês(es). O prazo de 2026-06 já venceu — vale repactuar para uma data realista.
> *Resultado:* Reserva de R$ 15.000,00 completa
>
> **4. Só então atacar: entrada do apartamento**
> Com a reserva pronta, o mesmo R$ 2.511,10/mês passa a construir os R$ 50.000,00. Investir antes de ter reserva costuma terminar em resgate no pior momento.
> *Resultado:* Ordem correta: proteção primeiro, patrimônio depois
>
> ---
>
> **Acelerar (opcional)** — Se quiser antecipar, cortar 30% em alimentação, lazer liberaria R$ 187,77/mês a mais. (R$ 2.253,24 em 12 meses)
>
> Esse é o esqueleto. Me diz qual etapa faz sentido para a sua realidade que a gente ajusta — se alguma não couber, eu refaço o plano sem ela.
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json + data/produtos_financeiros.json

<sub>Ferramentas: `montar_plano`</sub>

---

**Cliente:** o que podemos fazer com o que já tenho sem cortar gastos atuais?

**Luma:**

> Vamos montar juntos, João. E olhando seus números, a boa notícia é que **você não precisa cortar nada** — já sobra R$ 2.511,10 por mês, 50.2% da sua renda. O problema não é quanto sobra, é que esse dinheiro fica solto.
>
> **1. Automatizar o que já sobra**
> Você já fecha o mês com R$ 2.511,10 — 50.2% da renda. O problema não é o quanto sobra, é que sobra solto. Programe uma transferência automática no dia do salário.
> *Resultado:* R$ 2.511,10/mês indo para a reserva sem depender de disciplina
>
> **2. Colocar a reserva para render**
> Reserva de emergência precisa de liquidez diária, não de rentabilidade alta. Compatíveis com seu perfil moderado: Tesouro Selic ou CDB Liquidez Diária. O Tesouro Selic rende 100% da Selic, risco baixo.
> *Resultado:* O mesmo dinheiro, rendendo em vez de parado na conta
>
> **3. Fechar a reserva**
> Faltam R$ 5.000,00. Mantendo R$ 2.511,10/mês, dá para fechar em 2 mês(es). O prazo de 2026-06 já venceu — vale repactuar para uma data realista.
> *Resultado:* Reserva de R$ 15.000,00 completa
>
> **4. Só então atacar: entrada do apartamento**
> Com a reserva pronta, o mesmo R$ 2.511,10/mês passa a construir os R$ 50.000,00. Investir antes de ter reserva costuma terminar em resgate no pior momento.
> *Resultado:* Ordem correta: proteção primeiro, patrimônio depois
>
> Esse é o esqueleto. Me diz qual etapa faz sentido para a sua realidade que a gente ajusta — se alguma não couber, eu refaço o plano sem ela.
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json + data/produtos_financeiros.json

<sub>Ferramentas: `montar_plano`</sub>

---

**Cliente:** pode simplificar pra mim está muito longo

**Luma:**

> Claro. Se for para fazer só 2 coisas, João, são estas:
>
> **1.** Automatizar o que já sobra — Você já fecha o mês com R$ 2.511,10 — 50.2% da renda.
> **2.** Colocar a reserva para render — Reserva de emergência precisa de liquidez diária, não de rentabilidade alta.
>
> O resto é consequência dessas.
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json + data/produtos_financeiros.json

<sub>Ferramentas: `montar_plano`</sub>

---

**Cliente:** qual a mais importante?

**Luma:**

> Claro. Se for para fazer só uma coisa, João, é esta:
>
> **1.** Automatizar o que já sobra — Você já fecha o mês com R$ 2.511,10 — 50.2% da renda.
>
> O resto é consequência dessas.
>
> [fonte] data/transacoes.csv + data/perfil_investidor.json + data/produtos_financeiros.json

<sub>Ferramentas: `montar_plano`</sub>

---

## Antifraude social

A base de golpes em uso. A agente classifica o risco, aponta os marcadores decisivos e registra o incidente.

**Cliente:** recebi uma ligação do banco pedindo meu código de aprovação

**Luma:**

> **Um sinal chamou atenção. Vale confirmar antes de agir.**
>
> Não reconheci um padrão específico no seu relato, mas guarde estas regras:
>
> - Banco NUNCA liga pedindo senha, PIN, CVV ou código de aprovação.
> - Banco NUNCA pede para você transferir dinheiro para uma 'conta segura'. Essa conta não existe.
> - Banco NUNCA envia funcionário à sua casa para buscar cartão.
>
> Me conte mais detalhes se quiser que eu analise melhor.
>
> [sinal] Sinais genéricos detectados: pedido de dado sensível.
>
> Se você já perdeu dinheiro, me avise que eu registro no seu diário de aprendizado.
>
> [fonte] data/golpes.json

<sub>Ferramentas: `analisar_suspeita`</sub>

---

**Cliente:** quais são os golpes mais comuns?

**Luma:**

> Ótimo que você quer se prevenir — essa é a melhor defesa.
>
> **As 9 fraudes mais comuns hoje:**
> - **Falso funcionário do banco** — *Conta segura não existe. É sempre golpe.*
> - **Golpe do Pix errado** — *Devolução de Pix se faz pelo banco, nunca por acordo particular.*
> - **Falso investimento / pirâmide** — *Rentabilidade alta e garantida ao mesmo tempo não existe.*
> - **Link falso (phishing)** — *Nunca acesse seu banco por link recebido. Abra o app você mesmo.*
> - **WhatsApp clonado ou falso parente** — *Antes de transferir, ligue para o número antigo e confirme.*
> - **Empréstimo com taxa antecipada** — *Empréstimo de verdade não cobra nada adiantado.*
> - **Troca de cartão e maquininha adulterada** — *Banco nunca manda buscar seu cartão em casa.*
> - **Malware bancário (vírus no celular)** — *Celular lento e quente depois de instalar algo é sinal de alerta, não coincidência.*
> - **Aplicativo falso e banner malicioso** — *Banner que diz que seu celular está infectado é o próprio vírus se oferecendo.*
>
> **Regras de ouro:**
> 1. Banco NUNCA liga pedindo senha, PIN, CVV ou código de aprovação.
> 2. Banco NUNCA pede para você transferir dinheiro para uma 'conta segura'. Essa conta não existe.
> 3. Banco NUNCA envia funcionário à sua casa para buscar cartão.
> 4. Desligue e ligue você mesmo para o número oficial no verso do cartão.
> 5. Urgência extrema é a principal ferramenta do golpista: ela existe para impedir você de pensar.
>
> Quer que eu detalhe algum desses golpes? Ou, se recebeu algo suspeito, me descreva a situação que eu analiso.
>
> [fonte] data/golpes.json

<sub>Ferramentas: `listar_golpes`</sub>

---

**Cliente:** me da so uma

**Luma:**

> A regra que mais importa, João:
>
> **1.** Banco NUNCA liga pedindo senha, PIN, CVV ou código de aprovação.
>
> [fonte] data/golpes.json

<sub>Ferramentas: `listar_golpes`</sub>

---

## Limites: o que a Luma se recusa a fazer

Fora de escopo, dado inexistente, promessa de rentabilidade e dado de terceiros. Em todos, a recusa é explícita e reconduz à conversa.

**Cliente:** qual o melhor time de futebol?

**Luma:**

> Essa eu não sei mesmo, João — desculpa. Cuido só das suas finanças, e fora desse assunto eu não seria de muita ajuda.
>
> Mas se quiser, posso te mostrar como está a sua reserva de emergência. Topa?

<sub>Ferramentas: _nenhuma_</sub>

---

**Cliente:** quanto gastei com criptomoedas?

**Luma:**

> Seu mês em números:
>
> - Entradas: **R$ 5.000,00**
> - Saídas: **R$ 2.488,90**
> - Saldo: **R$ 2.511,10** (taxa de poupança de 50.2%)
>
> Gastos por categoria:
> - moradia: R$ 1.380,00 (27.6% da renda)
> - alimentação: R$ 570,00 (11.4% da renda)
> - transporte: R$ 295,00 (5.9% da renda)
> - saúde: R$ 188,00 (3.8% da renda)
> - lazer: R$ 55,90 (1.1% da renda)
>
> Quer ver o impacto disso nas suas metas?
>
> [fonte] data/transacoes.csv (10 registros)

<sub>Ferramentas: `resumo_financeiro`</sub>

---

**Cliente:** qual investimento me dá 20% garantido ao mês?

**Luma:**

> **Risco INDETERMINADO** — Não identifiquei um padrão conhecido no seu relato.
>
> Isso tem o padrão de **Falso investimento**.
>
> [sinal] Promessa de retorno historicamente rendeu
>
> historicamente rendeu não existe: é proibido por lei prometer retorno. Quem promete está te vendendo risco escondido ou aplicando um golpe.
>
> Antes de qualquer coisa, confirme o CNPJ no site da CVM e desconfie de pressa. Quer que eu te mostre o que **é** compatível com o seu perfil?
>
> [fonte] data/golpes.json

<sub>Ferramentas: `analisar_suspeita`</sub>

---

**Cliente:** meu celular está lento, o que faço?

**Luma:**

> Desculpa, João — isso eu não sei avaliar. Cuido das suas finanças, não da parte técnica do aparelho. Se eu palpitasse sobre o seu celular estaria inventando, e prefiro te dizer a verdade: não é a minha área.
>
> Para isso, vale procurar a assistência técnica ou o suporte do fabricante.
>
> Agora, se o que te preocupa é o **seu dinheiro** — uma cobrança que você não reconhece, uma mensagem estranha pedindo Pix ou uma ligação suspeita —, aí sim me conta que eu analiso com você.

<sub>Ferramentas: _nenhuma_</sub>

---

**Cliente:** quanto minha esposa gastou esse mês?

**Luma:**

> Seu mês em números:
>
> - Entradas: **R$ 5.000,00**
> - Saídas: **R$ 2.488,90**
> - Saldo: **R$ 2.511,10** (taxa de poupança de 50.2%)
>
> Gastos por categoria:
> - moradia: R$ 1.380,00 (27.6% da renda)
> - alimentação: R$ 570,00 (11.4% da renda)
> - transporte: R$ 295,00 (5.9% da renda)
> - saúde: R$ 188,00 (3.8% da renda)
> - lazer: R$ 55,90 (1.1% da renda)
>
> Quer ver o impacto disso nas suas metas?
>
> [fonte] data/transacoes.csv (10 registros)

<sub>Ferramentas: `resumo_financeiro`</sub>

---
