# 2. Base de Conhecimento

## 2.1 Fontes de dados

Os quatro arquivos mockados do repositório base, mantidos sem alteração para garantir comparabilidade com outros projetos do Lab.

| Arquivo | Formato | Registros | Papel no agente |
|---|---|---|---|
| `data/transacoes.csv` | CSV | 10 | Extrato do mês — base de todo cálculo de gastos |
| `data/perfil_investidor.json` | JSON | 1 cliente | Renda, perfil de risco, metas e prazos |
| `data/produtos_financeiros.json` | JSON | 5 produtos | Catálogo com risco e aporte mínimo |
| `data/historico_atendimento.csv` | CSV | 5 | Memória de longo prazo, temas recorrentes |
| `data/golpes.json` | JSON | 9 golpes + 7 vetores | **Base antifraude**: engenharia social e infecção técnica |
| `data/diario_incidentes.json` | JSON | dinâmico | **Gerado pelo uso**: golpes sofridos e lições |

### O que os dados contam

Lendo os quatro arquivos juntos, aparece uma história coerente:

- João poupa **R$ 2.511,10/mês** (50,2% da renda) — disciplina financeira acima da média
- Falta **R$ 5.000** para a reserva de emergência, cujo prazo **já venceu**
- Ele declarou `aceita_risco: false`, mas seu perfil é `moderado` — uma **tensão** que o agente precisa respeitar (prevalece o mais conservador)
- O histórico mostra interesse recorrente em Tesouro Selic e metas — ou seja, ele **já busca** essa orientação

Essa leitura definiu o caso de uso: o gargalo não é dinheiro, é **direcionamento**.

---

## 2.2 Estratégia de integração

### Por que não RAG (embeddings + busca vetorial)

A escolha óbvia seria vetorizar os arquivos e fazer busca semântica. Foi descartada por três motivos:

1. **Volume não justifica.** 20 registros cabem inteiros em qualquer contexto. RAG resolveria um problema que não existe.
2. **RAG não calcula.** Recuperar os trechos certos do CSV não impede o LLM de somar errado. O problema real é aritmética, não recuperação.
3. **Perda de precisão.** Busca semântica é aproximada. Extrato bancário exige exatidão.

### A escolha: Function Calling sobre dados estruturados

Os dados são carregados uma vez na memória e expostos ao LLM através de **16 ferramentas tipadas**. O modelo não recebe os dados — ele recebe a *capacidade de perguntar* aos dados.

```
LLM  →  "preciso de somar_por_categoria('alimentacao')"
             ↓
Python lê o CSV, filtra, soma  →  570.00
             ↓
LLM  ←  {"total_formatado": "R$ 570,00", "_fonte": "data/transacoes.csv (2 registros)"}
```

| Abordagem | Precisão numérica | Rastreabilidade |
|---|---|---|
| Dump do CSV no prompt | ❌ modelo soma e erra | ❌ |
| RAG / embeddings | ❌ modelo soma e erra | ⚠️ parcial |
| **Function calling** | ✅ **Python calcula** | ✅ **campo `_fonte`** |

---

## 2.3 As 16 ferramentas

| Ferramenta | Parâmetros | Retorna |
|---|---|---|
| `somar_por_categoria` | `categoria: str` | Total, contagem e detalhe dos lançamentos |
| `resumo_financeiro` | — | Entradas, saídas, saldo, taxa de poupança, ranking |
| `consultar_perfil` | — | Dados cadastrais e metas |
| `progresso_metas` | — | % concluído, quanto falta, aporte necessário, se está no ritmo |
| `recomendar_produtos` | — | Produtos compatíveis **e bloqueados**, com motivo |
| `montar_plano` | `sem_cortes: bool` | Plano de ação em etapas; respeita veto a cortes |
| `simular_economia` | `corte_pct, categorias, excluir` | Economia projetada e impacto no prazo da meta |
| `historico_atendimento` | — | Atendimentos e temas recorrentes |
| `analisar_resiliencia` | — | Meses de fôlego sem renda, no cenário normal e no enxuto |
| `avaliar_compra` | `valor: float` | Se a compra cabe, quanto atrasa a meta, veredito |
| `diagnostico_geral` | — | Pontos fortes, pontos de atenção e prioridade |
| `listar_golpes` | — | Catálogo de golpes + regras de ouro |
| `detalhar_golpe` | `golpe_id: str` | Ficha completa de um golpe |
| `analisar_suspeita` | `relato: str` | Nível de risco, golpe provável e bandeiras |
| `registrar_incidente` | `golpe_id, relato, valor, caiu` | Grava no diário de aprendizado |
| `consultar_diario` | — | Histórico de incidentes e lições |

### Contrato de retorno

Toda ferramenta devolve um dicionário com três garantias:

```python
{
    "total": 570.0,                                    # valor bruto
    "total_formatado": "R$ 570,00",                    # já em padrão BR
    "_fonte": "data/transacoes.csv (2 registros)"      # rastreabilidade
}
```

O campo `_formatado` existe para que **o LLM nunca precise formatar moeda** — outra oportunidade de erro eliminada.

---

## 2.4 Enriquecimento: dados derivados

As ferramentas não apenas leem os arquivos — elas produzem informação que não está escrita em lugar nenhum:

| Dado derivado | Cálculo | Por que importa |
|---|---|---|
| Taxa de poupança | `saldo / entradas` | 50,2% — contextualiza a saúde financeira |
| % da renda por categoria | `gasto / entradas` | Moradia = 27,6% da renda |
| Aporte mensal necessário | `falta / meses_até_prazo` | Transforma meta em ação mensal |
| Prazo vencido | `meses_até_prazo <= 0` | Detecta que junho/2026 já passou |
| Meses economizados | `meses_antes - meses_depois` | O "e daí?" da simulação |
| Meses de fôlego | `reserva / custo_mensal` | Responde "e se eu perder o emprego?" |
| Veredito de compra | `valor` vs. saldo e reserva | Transforma desejo em decisão informada |

> **Nota de implementação:** a detecção de prazo vencido surgiu de uma falha real encontrada nos testes. A primeira versão calculava aporte mensal negativo para uma meta com prazo passado. Registrado em `docs/04-metricas.md`.

---

## 2.5 Exemplo de contexto entregue ao modelo

Pergunta: *"Qual investimento você recomenda?"*

O modelo chama `recomendar_produtos()` e recebe:

```json
{
  "perfil_investidor": "moderado",
  "aceita_risco": false,
  "produtos_compativeis": [
    {"nome": "Tesouro Selic", "risco": "baixo", "rentabilidade": "100% da Selic", "aporte_minimo": 30.0},
    {"nome": "CDB Liquidez Diária", "risco": "baixo", "rentabilidade": "102% do CDI", "aporte_minimo": 100.0},
    {"nome": "LCI/LCA", "risco": "baixo", "rentabilidade": "95% do CDI", "aporte_minimo": 1000.0}
  ],
  "produtos_bloqueados": [
    {"nome": "Fundo Multimercado", "risco": "medio",
     "motivo": "risco 'medio' incompatível com perfil 'moderado' que declarou não aceitar risco"},
    {"nome": "Fundo de Ações", "risco": "alto",
     "motivo": "risco 'alto' incompatível com perfil 'moderado' que declarou não aceitar risco"}
  ],
  "_fonte": "data/produtos_financeiros.json + data/perfil_investidor.json",
  "_aviso": "Conteúdo educacional. Não constitui recomendação de investimento."
}
```

Repare: os produtos de risco **não são omitidos** — vêm rotulados como bloqueados, com o motivo. Isso permite ao agente **explicar a recusa** em vez de simplesmente ignorar o pedido do cliente.

---

## 2.6 A base que cresce: diário de incidentes

Todas as fontes anteriores são estáticas. O `diario_incidentes.json` é diferente: **ele é escrito pelo próprio uso do agente**.

Quando o usuário relata um golpe sofrido, `registrar_incidente()` grava data, tipo classificado, valor perdido, relato e — o mais importante — a **lição** correspondente:

```json
{
  "id": 1,
  "data": "2026-09-05",
  "golpe_id": "pix_errado",
  "golpe_nome": "Golpe do Pix errado",
  "valor_perdido": 800.0,
  "caiu": true,
  "licao": "Devolução de Pix se faz pelo banco, nunca por acordo particular.",
  "sinais_que_passaram": [
    "Recebimento de valor que você não esperava",
    "Contato imediato pedindo devolução com urgência",
    "Pedido para devolver em chave Pix diferente da que enviou"
  ]
}
```

Isso muda a natureza da base de conhecimento: ela deixa de ser só uma fonte de consulta e passa a ser **memória de segurança do cliente**. Quanto mais o agente é usado, mais personalizada fica a proteção.

---

## 2.7 Como evoluir a base

O desenho suporta crescimento sem refatoração:

- **Mais transações** → basta adicionar linhas no CSV; as ferramentas escalam
- **Múltiplos clientes** → parametrizar `cliente_id` no carregamento
- **Dados de mercado** (Selic, CDI, IPCA) → nova ferramenta consultando API do Banco Central
- **Base antifraude viva** → alimentar `golpes.json` com boletins da Febraban e do Banco Central
- **Base grande (10k+ registros)** → aí sim vale RAG **para busca textual**, mantendo as ferramentas para os números
