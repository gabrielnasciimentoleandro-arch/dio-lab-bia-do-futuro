"""
ferramentas.py — Camada determinística do agente Luma.

PRINCÍPIO CENTRAL DO PROJETO:
    O LLM NÃO CALCULA. Ele interpreta a pergunta, escolhe uma ferramenta,
    e explica o resultado. Todo número que chega ao usuário foi produzido
    aqui, por Python, a partir dos arquivos em data/.

Isso torna o agente MATEMATICAMENTE INCAPAZ de alucinar um valor.
Cada retorno carrega o campo "_fonte" para citação obrigatória na resposta.
"""

from __future__ import annotations

import csv
import re
import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------- carga base
def _carregar_json(nome: str) -> Any:
    with open(DATA_DIR / nome, encoding="utf-8") as f:
        return json.load(f)


def _carregar_csv(nome: str) -> list[dict]:
    with open(DATA_DIR / nome, encoding="utf-8-sig", newline="") as f:
        return [dict(linha) for linha in csv.DictReader(f)]


PERFIL: dict = _carregar_json("perfil_investidor.json")
PRODUTOS: list[dict] = _carregar_json("produtos_financeiros.json")
TRANSACOES: list[dict] = _carregar_csv("transacoes.csv")
ATENDIMENTOS: list[dict] = _carregar_csv("historico_atendimento.csv")

# Categorias consideradas supérfluas para o cálculo de potencial de economia.
CATEGORIAS_FLEXIVEIS = {"lazer", "alimentacao"}

# Rótulos de exibição — a base guarda sem acento, o usuário lê com acento.
ROTULOS = {
    "alimentacao": "alimentação",
    "moradia": "moradia",
    "transporte": "transporte",
    "saude": "saúde",
    "lazer": "lazer",
    "receita": "receita",
}


def rotulo(categoria: str) -> str:
    return ROTULOS.get(categoria.lower(), categoria)


# Sinônimos que o cliente usa para nomear cada categoria da base.
SINONIMOS_CAT = {
    "moradia": ("moradia", "casa", "aluguel", "aluguer", "luz", "energia",
                "condominio", "agua", "iptu", "moradias"),
    "alimentacao": ("alimentacao", "alimentação", "comida", "mercado",
                    "supermercado", "restaurante", "ifood", "delivery",
                    "lanche", "alimento"),
    "transporte": ("transporte", "uber", "gasolina", "combustivel", "onibus",
                   "carro", "99", "taxi", "metro", "passagem"),
    "saude": ("saude", "saúde", "farmacia", "remedio", "academia", "medico",
              "plano de saude", "dentista"),
    "lazer": ("lazer", "netflix", "streaming", "cinema", "diversao",
              "assinatura", "spotify", "bar", "festa"),
}


def _norm_cat(texto: str) -> str:
    """
    Converte o que o usuário escreveu na chave da base.
    'aluguel', 'casa' e 'luz' -> 'moradia'.
    """
    t = unicodedata.normalize("NFD", texto.strip().lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    for chave, termos in SINONIMOS_CAT.items():
        if t == chave or t in termos:
            return chave
    for chave, termos in SINONIMOS_CAT.items():
        if any(termo in t for termo in termos):
            return chave
    return t


def detectar_categorias(texto: str) -> list[str]:
    """Extrai todas as categorias mencionadas numa frase livre."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    achadas = []
    for chave, termos in SINONIMOS_CAT.items():
        if any(re.search(rf"\b{re.escape(termo)}\b", t) for termo in termos):
            achadas.append(chave)
    return achadas


def brl(valor: float) -> str:
    """Formata float como moeda brasileira: 1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def prazo_texto(meses: int | None) -> str:
    """
    Traduz 'meses_no_ritmo_atual' em linguagem honesta.

    None significa saldo zero ou negativo: a meta NÃO é alcançável no ritmo
    atual. Sem isto a interface dizia "dá para fechar em 0 mês(es)", que soa
    como boa notícia quando na verdade é o pior cenário possível.
    """
    if meses is None:
        return "no ritmo atual você não chega lá — o mês está fechando no vermelho"
    if meses == 0:
        return "meta já concluída"
    return f"dá para fechar em {meses} mês(es)"


# ------------------------------------------------------------------ FERRAMENTAS
def somar_por_categoria(categoria: str) -> dict:
    """Soma as SAÍDAS de uma categoria. Ex.: 'alimentacao' -> 570.00"""
    categoria = (categoria or "").strip().lower()
    itens = [
        t for t in TRANSACOES
        if t["categoria"].lower() == categoria and t["tipo"] == "saida"
    ]

    if not itens:
        disponiveis = sorted({
            t["categoria"] for t in TRANSACOES if t["tipo"] == "saida"
        })
        return {
            "encontrado": False,
            "categoria": categoria,
            "categorias_disponiveis": [rotulo(c) for c in disponiveis],
            "_fonte": "data/transacoes.csv",
        }

    total = sum(float(t["valor"]) for t in itens)
    return {
        "encontrado": True,
        "categoria": categoria,
        "categoria_exibicao": rotulo(categoria),
        "total": round(total, 2),
        "total_formatado": brl(total),
        "qtd_transacoes": len(itens),
        "detalhe": [
            {"data": t["data"], "descricao": t["descricao"], "valor": brl(float(t["valor"]))}
            for t in itens
        ],
        "_fonte": f"data/transacoes.csv ({len(itens)} registros)",
    }


def resumo_financeiro() -> dict:
    """Panorama do mês: entradas, saídas, saldo e gastos por categoria."""
    entradas = sum(float(t["valor"]) for t in TRANSACOES if t["tipo"] == "entrada")
    saidas = sum(float(t["valor"]) for t in TRANSACOES if t["tipo"] == "saida")
    saldo = entradas - saidas

    por_categoria: dict[str, float] = {}
    for t in TRANSACOES:
        if t["tipo"] == "saida":
            por_categoria[t["categoria"]] = por_categoria.get(t["categoria"], 0.0) + float(t["valor"])

    ranking = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)

    return {
        "entradas": round(entradas, 2),
        "entradas_formatado": brl(entradas),
        "saidas": round(saidas, 2),
        "saidas_formatado": brl(saidas),
        "saldo": round(saldo, 2),
        "saldo_formatado": brl(saldo),
        "taxa_poupanca_pct": round(saldo / entradas * 100, 1) if entradas else 0.0,
        "gastos_por_categoria": [
            {"categoria": rotulo(c), "valor": round(v, 2), "valor_formatado": brl(v),
             "pct_da_renda": round(v / entradas * 100, 1) if entradas else 0.0}
            for c, v in ranking
        ],
        "maior_gasto": {"categoria": rotulo(ranking[0][0]), "valor_formatado": brl(ranking[0][1])} if ranking else None,
        "_fonte": f"data/transacoes.csv ({len(TRANSACOES)} registros)",
    }


def consultar_perfil() -> dict:
    """Dados cadastrais e metas do cliente."""
    return {**PERFIL, "_fonte": "data/perfil_investidor.json"}


def progresso_metas() -> dict:
    """Progresso de cada meta e projeção de prazo com base no saldo mensal."""
    resumo = resumo_financeiro()
    saldo_mensal = resumo["saldo"]
    reserva = float(PERFIL.get("reserva_emergencia_atual", 0))
    hoje = date.today()

    metas = []
    for m in PERFIL.get("metas", []):
        necessario = float(m["valor_necessario"])
        # A reserva atual só conta para a meta de reserva de emergência.
        acumulado = reserva if "reserva" in m["meta"].lower() else 0.0
        falta = max(necessario - acumulado, 0.0)
        pct = round(acumulado / necessario * 100, 1) if necessario else 0.0

        # ATENCAO: 0 é ambíguo — pode significar "meta concluída" ou "saldo
        # negativo, nunca alcança". None marca o caso inalcançável, para a UI
        # e o agente não dizerem "dá para fechar em 0 mês(es)".
        if falta <= 0:
            meses_nec = 0
        elif saldo_mensal > 0:
            meses_nec = int(-(-falta // saldo_mensal))
        else:
            meses_nec = None  # saldo zero ou negativo: inalcançável no ritmo atual

        ano, mes = map(int, m["prazo"].split("-"))
        meses_ate_prazo = (ano - hoje.year) * 12 + (mes - hoje.month)
        prazo_vencido = meses_ate_prazo <= 0 and falta > 0
        aporte_ideal = round(falta / meses_ate_prazo, 2) if meses_ate_prazo > 0 and falta > 0 else 0.0

        metas.append({
            "prazo_vencido": prazo_vencido,
            "meta": m["meta"],
            "valor_necessario": necessario,
            "valor_necessario_formatado": brl(necessario),
            "acumulado_formatado": brl(acumulado),
            "falta": round(falta, 2),
            "falta_formatado": brl(falta),
            "progresso_pct": pct,
            "prazo": m["prazo"],
            "meses_ate_prazo": meses_ate_prazo,
            "aporte_mensal_necessario_formatado": brl(aporte_ideal),
            "meses_no_ritmo_atual": meses_nec,
            "no_ritmo": bool(not prazo_vencido and meses_nec and meses_ate_prazo > 0
                             and meses_nec <= meses_ate_prazo),
            "concluida": falta == 0,
        })

    return {
        "saldo_mensal_formatado": brl(saldo_mensal),
        "metas": metas,
        "_fonte": "data/perfil_investidor.json + data/transacoes.csv",
    }


def recomendar_produtos() -> dict:
    """
    Filtra produtos compatíveis com o perfil.
    GUARDRAIL: se aceita_risco=False, produtos de risco médio/alto são
    BLOQUEADOS na origem — o LLM nunca chega a vê-los como opção.
    """
    perfil_risco = PERFIL.get("perfil_investidor", "conservador").lower()
    aceita_risco = bool(PERFIL.get("aceita_risco", False))

    if not aceita_risco:
        permitidos = {"baixo"}
    elif perfil_risco == "moderado":
        permitidos = {"baixo", "medio"}
    elif perfil_risco in ("arrojado", "agressivo"):
        permitidos = {"baixo", "medio", "alto"}
    else:
        permitidos = {"baixo"}

    compativeis = [p for p in PRODUTOS if p["risco"].lower() in permitidos]
    bloqueados = [
        {"nome": p["nome"], "risco": p["risco"],
         "motivo": f"risco '{p['risco']}' incompatível com perfil '{perfil_risco}' que declarou não aceitar risco"}
        for p in PRODUTOS if p["risco"].lower() not in permitidos
    ]

    return {
        "perfil_investidor": perfil_risco,
        "aceita_risco": aceita_risco,
        "produtos_compativeis": compativeis,
        "produtos_bloqueados": bloqueados,
        "_fonte": "data/produtos_financeiros.json + data/perfil_investidor.json",
        "_aviso": "Conteúdo educacional. Não constitui recomendação de investimento.",
    }


def simular_economia(corte_pct: float = 30.0,
                     categorias: list[str] | None = None,
                     excluir: list[str] | None = None) -> dict:
    """
    Simula cortar X% de gastos e o impacto no prazo das metas.

    categorias: quais cortar. Padrão = as flexíveis (alimentação e lazer).
                Aceita categorias fixas se o usuário pedir explicitamente.
    excluir:    categorias que o usuário disse que NÃO pode cortar.

    O cliente precisa poder dizer "moradia não dá para mexer". Sem os
    parâmetros, a simulação era sempre a mesma e ignorava a restrição.
    """
    resumo = resumo_financeiro()
    gastos: dict[str, float] = {}
    for t in TRANSACOES:
        if t["tipo"] == "saida":
            gastos[t["categoria"]] = gastos.get(t["categoria"], 0.0) + float(t["valor"])

    excluir_norm = {_norm_cat(c) for c in (excluir or [])}

    if categorias:
        alvo = [_norm_cat(c) for c in categorias]
    else:
        # Ordena por valor: cortar onde há mais dinheiro faz mais diferença.
        alvo = sorted(CATEGORIAS_FLEXIVEIS, key=lambda c: -gastos.get(c, 0.0))

    alvo = [c for c in alvo if c not in excluir_norm and gastos.get(c, 0.0) > 0]

    economia = 0.0
    detalhe = []
    for cat in alvo:
        valor = gastos[cat] * (corte_pct / 100)
        economia += valor
        detalhe.append({
            "categoria": rotulo(cat),
            "gasto_atual_formatado": brl(gastos[cat]),
            "economia_formatado": brl(valor),
        })

    # Alternativas que sobraram: o que ainda dá para cortar, da maior p/ menor.
    alternativas = [
        {"categoria": rotulo(c), "gasto_formatado": brl(v),
         "economia_possivel_formatado": brl(v * corte_pct / 100)}
        for c, v in sorted(gastos.items(), key=lambda kv: -kv[1])
        if c not in alvo and c not in excluir_norm
    ]

    novo_saldo = resumo["saldo"] + economia
    reserva = float(PERFIL.get("reserva_emergencia_atual", 0))
    meta_reserva = next(
        (float(m["valor_necessario"]) for m in PERFIL.get("metas", [])
         if "reserva" in m["meta"].lower()), 0.0
    )
    falta = max(meta_reserva - reserva, 0.0)

    meses_antes = int(-(-falta // resumo["saldo"])) if resumo["saldo"] > 0 and falta else 0
    meses_depois = int(-(-falta // novo_saldo)) if novo_saldo > 0 and falta else 0

    return {
        "corte_pct": corte_pct,
        "categorias_ajustadas": detalhe,
        "categorias_excluidas": [rotulo(c) for c in excluir_norm],
        "alternativas": alternativas,
        "sem_categorias": not detalhe,
        "economia_mensal": round(economia, 2),
        "economia_mensal_formatado": brl(economia),
        "economia_anual_formatado": brl(economia * 12),
        "saldo_atual_formatado": brl(resumo["saldo"]),
        "novo_saldo_formatado": brl(novo_saldo),
        "meses_para_meta_antes": meses_antes,
        "meses_para_meta_depois": meses_depois,
        "meses_economizados": max(meses_antes - meses_depois, 0),
        "_fonte": "data/transacoes.csv + data/perfil_investidor.json",
    }


def analisar_resiliencia() -> dict:
    """
    Quantos meses o cliente sobrevive com a reserva atual se perder a renda.
    Responde à pergunta que dá sentido à reserva de emergência.
    """
    resumo = resumo_financeiro()
    reserva = float(PERFIL.get("reserva_emergencia_atual", 0))
    custo_mensal = resumo["saidas"]

    # Cenário enxuto: corta 100% de lazer e 40% de alimentação
    gastos = {g["categoria"]: g["valor"] for g in resumo["gastos_por_categoria"]}
    corte = gastos.get("lazer", 0.0) + gastos.get("alimentação", 0.0) * 0.4
    custo_enxuto = custo_mensal - corte

    meses = reserva / custo_mensal if custo_mensal else 0.0
    meses_enxuto = reserva / custo_enxuto if custo_enxuto else 0.0

    meta_reserva = next(
        (float(m["valor_necessario"]) for m in PERFIL.get("metas", [])
         if "reserva" in m["meta"].lower()), 0.0
    )
    meses_meta = meta_reserva / custo_mensal if custo_mensal else 0.0

    if meses >= 6:
        nivel, leitura = "confortável", "você está dentro da recomendação de 6 meses"
    elif meses >= 3:
        nivel, leitura = "razoável", "acima do mínimo de 3 meses, mas ainda abaixo do ideal de 6"
    else:
        nivel, leitura = "frágil", "abaixo do mínimo recomendado de 3 meses"

    return {
        "reserva_atual_formatado": brl(reserva),
        "custo_mensal_formatado": brl(custo_mensal),
        "custo_enxuto_formatado": brl(custo_enxuto),
        "meses_de_folego": round(meses, 1),
        "meses_de_folego_enxuto": round(meses_enxuto, 1),
        "meses_cobertos_pela_meta": round(meses_meta, 1),
        "nivel": nivel,
        "leitura": leitura,
        "_fonte": "data/perfil_investidor.json + data/transacoes.csv",
    }


def avaliar_compra(valor: float) -> dict:
    """Avalia o impacto de uma compra: cabe no saldo? atrasa a meta?"""
    resumo = resumo_financeiro()
    saldo = resumo["saldo"]
    reserva = float(PERFIL.get("reserva_emergencia_atual", 0))
    meta_reserva = next(
        (float(m["valor_necessario"]) for m in PERFIL.get("metas", [])
         if "reserva" in m["meta"].lower()), 0.0
    )
    falta_reserva = max(meta_reserva - reserva, 0.0)
    reserva_completa = falta_reserva == 0

    meses_poupando = valor / saldo if saldo > 0 else 0.0
    atraso = int(-(-valor // saldo)) if saldo > 0 else 0
    compromete_reserva = valor > (reserva - meta_reserva) if reserva_completa else True

    if reserva_completa and meses_poupando <= 6:
        veredito = "cabe"
    elif not reserva_completa:
        veredito = "prematuro"
    else:
        veredito = "pesado"

    return {
        "valor_formatado": brl(valor),
        "saldo_mensal_formatado": brl(saldo),
        "meses_poupando": round(meses_poupando, 1),
        "atraso_na_meta_meses": atraso,
        "reserva_completa": reserva_completa,
        "falta_reserva_formatado": brl(falta_reserva),
        "compromete_reserva": compromete_reserva,
        "veredito": veredito,
        "_fonte": "data/transacoes.csv + data/perfil_investidor.json",
        "_aviso": "Análise de impacto no orçamento. Não constitui recomendação de investimento.",
    }


def diagnostico_geral() -> dict:
    """Diagnóstico completo com pontos fortes, atenção e a próxima ação prioritária."""
    resumo = resumo_financeiro()
    metas = progresso_metas()
    resil = analisar_resiliencia()
    m = metas["metas"][0]

    fortes, atencao = [], []

    if resumo["taxa_poupanca_pct"] >= 20:
        fortes.append(f"Você poupa {resumo['taxa_poupanca_pct']}% da renda — "
                      f"bem acima da média brasileira, que fica perto de 5%")
    if resumo["saldo"] > 0:
        fortes.append(f"Seu mês fecha positivo em {resumo['saldo_formatado']}")

    maior = resumo["gastos_por_categoria"][0]
    if maior["pct_da_renda"] > 30:
        atencao.append(f"{maior['categoria'].capitalize()} consome "
                       f"{maior['pct_da_renda']}% da renda (o ideal fica até 30%)")
    if resil["meses_de_folego"] < 6:
        atencao.append(f"Sua reserva cobre {resil['meses_de_folego']} meses — "
                       f"a recomendação é 6")
    if m["prazo_vencido"]:
        atencao.append(f"O prazo da {m['meta'].lower()} ({m['prazo']}) já venceu")

    prioridade = (
        f"Completar a reserva de emergência: faltam {m['falta_formatado']}, "
        f"e {prazo_texto(m['meses_no_ritmo_atual'])}."
        if not m["concluida"] else
        "Reserva completa. O próximo passo é direcionar o saldo para a meta seguinte."
    )

    return {
        "pontos_fortes": fortes,
        "pontos_de_atencao": atencao,
        "prioridade": prioridade,
        "saldo_formatado": resumo["saldo_formatado"],
        "_fonte": "data/transacoes.csv + data/perfil_investidor.json",
    }


def historico_atendimento() -> dict:
    """Atendimentos anteriores — dá memória de longo prazo ao agente."""
    return {
        "total": len(ATENDIMENTOS),
        "atendimentos": ATENDIMENTOS,
        "temas_recorrentes": sorted({a["tema"] for a in ATENDIMENTOS}),
        "_fonte": f"data/historico_atendimento.csv ({len(ATENDIMENTOS)} registros)",
    }


# ============================================================ ANTIFRAUDE
GOLPES: dict = _carregar_json("golpes.json")
DIARIO_PATH = DATA_DIR / "diario_incidentes.json"


def _carregar_diario() -> list[dict]:
    if DIARIO_PATH.exists():
        with open(DIARIO_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def _salvar_diario(registros: list[dict]) -> None:
    with open(DIARIO_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


def listar_golpes() -> dict:
    """Catálogo de golpes conhecidos + regras de ouro."""
    return {
        "regras_de_ouro": GOLPES["regras_de_ouro"],
        "golpes": [
            {"id": g["id"], "nome": g["nome"], "frase_chave": g["frase_chave"]}
            for g in GOLPES["golpes"]
        ],
        "total": len(GOLPES["golpes"]),
        "_fonte": "data/golpes.json",
    }


def detalhar_golpe(golpe_id: str) -> dict:
    """Ficha completa de um golpe: como funciona, sinais e conduta."""
    for g in GOLPES["golpes"]:
        if g["id"] == golpe_id or _slug(golpe_id) in _slug(g["nome"]):
            return {**g, "_fonte": "data/golpes.json"}
    return {
        "encontrado": False,
        "golpes_disponiveis": [g["nome"] for g in GOLPES["golpes"]],
        "_fonte": "data/golpes.json",
    }


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def analisar_suspeita(relato: str) -> dict:
    """
    Analisa a descrição de uma abordagem suspeita e devolve um nível de risco
    com base em SINAIS OBJETIVOS encontrados no texto — não em opinião do modelo.
    """
    txt = _slug(relato)

    GATILHOS = {
        "falso_funcionario": ["conta segura", "conta espelho", "central de seguranca",
                              "falso funcionario", "falso gerente", "golpe do banco",
                              "gerente ligou", "banco ligou", "invadiram sua conta",
                              "compra suspeita", "transferir para outra conta",
                              "codigo que chegou", "instalar aplicativo"],
        "pix_errado": ["pix por engano", "pix errado", "recebi um pix", "devolver o pix",
                       "caiu na minha conta", "mandaram sem querer", "outra chave",
                       "golpe do pix", "pix"],
        "falso_investimento": ["rendimento garantido", "lucro garantido", "risco zero",
                               "piramide", "falso investimento", "investimento falso",
                               "sem risco", "ao mes garantido", "robo de investimento",
                               "dobrar seu dinheiro", "indicar amigos", "trader"],
        "phishing": ["clicou no link", "cliquei no link", "recebi um sms", "link do banco",
                     "phishing", "site falso", "link falso",
                     "atualizar cadastro", "premio", "restituicao", "encomenda parada",
                     "conta bloqueada", "site do banco"],
        "whatsapp_clonado": ["numero novo", "mudei de numero", "perdi o celular",
                             "parente pediu", "filho pediu", "mae pediu", "whatsapp",
                             "falso parente", "se passou por"],
        "emprestimo_taxa": ["taxa antecipada", "pagar para liberar", "pagar taxa",
                            "emprestimo para negativado", "credito aprovado sem consulta",
                            "seguro do emprestimo", "iof adiantado"],
        "maquininha_troca_cartao": ["maquininha", "cartao nao passou", "trocaram meu cartao",
                                    "motoboy", "buscar o cartao", "levar o cartao"],
    }

    UNIVERSAIS = {
        "urgencia": ["urgente", "agora", "rapido", "so hoje", "ultima chance",
                     "voce vai perder", "imediatamente", "poucas horas"],
        "sigilo": ["nao conte", "segredo", "nao avise", "sem falar com ninguem"],
        "dado_sensivel": ["senha", "cvv", "codigo", "token", "pin", "cartao"],
        "pagamento_pf": ["pessoa fisica", "cpf de outra", "conta de terceiro"],
    }

    # Marcadores decisivos: sozinhos já caracterizam golpe conhecido.
    DECISIVOS = [
        "conta segura", "conta espelho", "conta do banco central",
        "lucro garantido", "rendimento garantido", "risco zero",
        "retorno garantido", "ganho garantido", "sem risco nenhum",
        "rentabilidade garantida", "lucro certo",
        "pagar taxa", "taxa antecipada", "pagar para liberar",
        "buscar o cartao", "levar o cartao", "buscar seu cartao",
    ]
    decisivo = [d for d in DECISIVOS if d in txt]

    pontos: dict[str, int] = {}
    for gid, termos in GATILHOS.items():
        achados = [t for t in termos if t in txt]
        if achados:
            pontos[gid] = len(achados)

    bandeiras = [nome for nome, termos in UNIVERSAIS.items()
                 if any(t in txt for t in termos)]

    score = (max(pontos.values()) * 2 if pontos else 0) + len(bandeiras)
    if decisivo:
        score = max(score, 5)

    if score >= 4:
        nivel, veredito = "ALTO", "Isso tem cara de golpe. Não avance."
    elif score >= 2:
        nivel, veredito = "MÉDIO", "Há sinais preocupantes. Pare e confirme pelo canal oficial."
    elif score >= 1:
        nivel, veredito = "BAIXO", "Um sinal chamou atenção. Vale confirmar antes de agir."
    else:
        nivel, veredito = "INDETERMINADO", "Não identifiquei um padrão conhecido no seu relato."

    provavel = None
    if pontos:
        gid = max(pontos, key=pontos.get)
        provavel = next(g for g in GOLPES["golpes"] if g["id"] == gid)

    return {
        "nivel_risco": nivel,
        "veredito": veredito,
        "score": score,
        "golpe_provavel": (
            {"id": provavel["id"], "nome": provavel["nome"],
             "frase_chave": provavel["frase_chave"],
             "sinais_de_alerta": provavel["sinais_de_alerta"],
             "o_que_fazer": provavel["o_que_fazer"]}
            if provavel else None
        ),
        "bandeiras_vermelhas": bandeiras,
        "marcadores_decisivos": decisivo,
        "regras_de_ouro": GOLPES["regras_de_ouro"][:3],
        "_fonte": "data/golpes.json",
    }


def registrar_incidente(golpe_id: str, relato: str, valor: float = 0.0,
                        caiu: bool = True) -> dict:
    """
    Registra um golpe sofrido no diário de aprendizado.
    Transforma o episódio em lição e alimenta alertas personalizados futuros.
    """
    registros = _carregar_diario()

    ficha = next((g for g in GOLPES["golpes"] if g["id"] == golpe_id), None)

    novo = {
        "id": len(registros) + 1,
        "data": date.today().isoformat(),
        "golpe_id": golpe_id,
        "golpe_nome": ficha["nome"] if ficha else "Não classificado",
        "relato": relato[:400],
        "valor_perdido": round(float(valor), 2),
        "caiu": bool(caiu),
        "licao": ficha["frase_chave"] if ficha else
                 "Diante de urgência para movimentar dinheiro, pare e confirme pelo canal oficial.",
        "sinais_que_passaram": ficha["sinais_de_alerta"][:3] if ficha else [],
    }
    registros.append(novo)
    _salvar_diario(registros)

    total = sum(r["valor_perdido"] for r in registros)
    return {
        "registrado": True,
        "incidente": novo,
        "valor_perdido_formatado": brl(novo["valor_perdido"]),
        "total_incidentes": len(registros),
        "total_perdido_formatado": brl(total),
        "_fonte": "data/diario_incidentes.json",
    }


def consultar_diario() -> dict:
    """Histórico de incidentes e lições aprendidas."""
    registros = _carregar_diario()
    if not registros:
        return {
            "vazio": True,
            "total": 0,
            "mensagem": "Nenhum incidente registrado — ótimo sinal.",
            "_fonte": "data/diario_incidentes.json",
        }

    total = sum(r["valor_perdido"] for r in registros)
    tipos: dict[str, int] = {}
    for r in registros:
        tipos[r["golpe_nome"]] = tipos.get(r["golpe_nome"], 0) + 1
    recorrente = max(tipos, key=tipos.get)

    return {
        "vazio": False,
        "total": len(registros),
        "total_perdido_formatado": brl(total),
        "tipo_recorrente": recorrente,
        "incidentes": [
            {"data": r["data"], "golpe": r["golpe_nome"],
             "valor_formatado": brl(r["valor_perdido"]),
             "caiu": r["caiu"], "licao": r["licao"]}
            for r in registros
        ],
        "licoes": list(dict.fromkeys(r["licao"] for r in registros)),
        "_fonte": f"data/diario_incidentes.json ({len(registros)} registros)",
    }


def montar_plano(sem_cortes: bool = False) -> dict:
    """
    Monta um plano de ação em etapas para o cliente atingir a reserva.

    sem_cortes=True: o cliente pediu para NÃO reduzir gastos. O plano então
    trabalha apenas com o dinheiro que já sobra — direcionamento, automação
    e rendimento — sem sugerir corte nenhum.

    Existe porque "vamos montar um plano juntos" é cocriação, um dos pilares
    do agente, e caía no fallback: ele sabia responder consultas isoladas mas
    não sabia organizar um caminho.
    """
    resumo = resumo_financeiro()
    metas = progresso_metas()["metas"]
    meta = metas[0]
    produtos = recomendar_produtos()
    saldo = resumo["saldo"]
    falta = meta["falta"]

    etapas: list[dict] = []

    # Etapa 1 — o dinheiro que já existe e não está trabalhando.
    if saldo > 0:
        etapas.append({
            "titulo": "Automatizar o que já sobra",
            "acao": (f"Você já fecha o mês com {brl(saldo)} — {resumo['taxa_poupanca_pct']}% "
                     f"da renda. O problema não é o quanto sobra, é que sobra solto. "
                     f"Programe uma transferência automática no dia do salário."),
            "impacto": f"{brl(saldo)}/mês indo para a reserva sem depender de disciplina",
        })

    # Etapa 2 — onde guardar (sem prometer retorno).
    if produtos["produtos_compativeis"]:
        p = produtos["produtos_compativeis"][0]
        liquidos = [x["nome"] for x in produtos["produtos_compativeis"][:2]]
        etapas.append({
            "titulo": "Colocar a reserva para render",
            "acao": (f"Reserva de emergência precisa de liquidez diária, não de "
                     f"rentabilidade alta. Compatíveis com seu perfil "
                     f"{produtos['perfil_investidor']}: {' ou '.join(liquidos)}. "
                     f"O {p['nome']} rende {p['rentabilidade']}, risco {p['risco']}."),
            "impacto": "O mesmo dinheiro, rendendo em vez de parado na conta",
        })

    # Etapa 3 — o prazo, com o número real.
    if falta > 0:
        etapas.append({
            "titulo": "Fechar a reserva",
            "acao": (f"Faltam {brl(falta)}. Mantendo {brl(saldo)}/mês, "
                     f"{prazo_texto(meta['meses_no_ritmo_atual'])}."
                     + (f" O prazo de {meta['prazo']} já venceu — vale repactuar "
                        f"para uma data realista." if meta["prazo_vencido"] else "")),
            "impacto": f"Reserva de {meta['valor_necessario_formatado']} completa",
        })

    # Etapa 4 — só depois da reserva, a próxima meta.
    if len(metas) > 1:
        prox = metas[1]
        etapas.append({
            "titulo": f"Só então atacar: {prox['meta'].lower()}",
            "acao": (f"Com a reserva pronta, o mesmo {brl(saldo)}/mês passa a "
                     f"construir os {prox['valor_necessario_formatado']}. "
                     f"Investir antes de ter reserva costuma terminar em resgate "
                     f"no pior momento."),
            "impacto": "Ordem correta: proteção primeiro, patrimônio depois",
        })

    # Alavanca extra — só se o cliente NÃO vetou cortes.
    alavanca = None
    if not sem_cortes:
        sim = simular_economia(30)
        if sim["economia_mensal"] > 0:
            cats = ", ".join(c["categoria"] for c in sim["categorias_ajustadas"])
            alavanca = {
                "titulo": "Acelerar (opcional)",
                "acao": (f"Se quiser antecipar, cortar 30% em {cats} liberaria "
                         f"{sim['economia_mensal_formatado']}/mês a mais."),
                "impacto": f"{sim['economia_anual_formatado']} em 12 meses",
            }

    return {
        "sem_cortes": sem_cortes,
        "saldo_disponivel_formatado": brl(saldo),
        "taxa_poupanca_pct": resumo["taxa_poupanca_pct"],
        "falta_reserva_formatado": brl(falta),
        "etapas": etapas,
        "total_etapas": len(etapas),
        "alavanca_opcional": alavanca,
        "_fonte": ("data/transacoes.csv + data/perfil_investidor.json "
                   "+ data/produtos_financeiros.json"),
    }


FERRAMENTAS = {
    "montar_plano": montar_plano,
    "somar_por_categoria": somar_por_categoria,
    "resumo_financeiro": resumo_financeiro,
    "consultar_perfil": consultar_perfil,
    "progresso_metas": progresso_metas,
    "recomendar_produtos": recomendar_produtos,
    "simular_economia": simular_economia,
    "historico_atendimento": historico_atendimento,
    "analisar_resiliencia": analisar_resiliencia,
    "avaliar_compra": avaliar_compra,
    "diagnostico_geral": diagnostico_geral,
    "listar_golpes": listar_golpes,
    "detalhar_golpe": detalhar_golpe,
    "analisar_suspeita": analisar_suspeita,
    "registrar_incidente": registrar_incidente,
    "consultar_diario": consultar_diario,
}


def executar(nome: str, argumentos: dict | None = None) -> dict:
    """Despacha a chamada de ferramenta vinda do LLM."""
    if nome not in FERRAMENTAS:
        return {"erro": f"Ferramenta '{nome}' não existe.",
                "ferramentas_validas": list(FERRAMENTAS)}
    try:
        return FERRAMENTAS[nome](**(argumentos or {}))
    except TypeError as e:
        return {"erro": f"Argumentos inválidos para '{nome}': {e}"}


if __name__ == "__main__":
    for nome in FERRAMENTAS:
        print(f"\n{'=' * 60}\n{nome}\n{'=' * 60}")
        args = {"categoria": "alimentacao"} if nome == "somar_por_categoria" else {}
        print(json.dumps(executar(nome, args), ensure_ascii=False, indent=2)[:700])
