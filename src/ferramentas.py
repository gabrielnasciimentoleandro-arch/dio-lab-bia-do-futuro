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


def brl(valor: float) -> str:
    """Formata float como moeda brasileira: 1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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

        meses_nec = int(-(-falta // saldo_mensal)) if saldo_mensal > 0 and falta > 0 else 0

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


def simular_economia(corte_pct: float = 30.0) -> dict:
    """Simula cortar X% das categorias flexíveis e o impacto no prazo das metas."""
    resumo = resumo_financeiro()
    gastos: dict[str, float] = {}
    for t in TRANSACOES:
        if t["tipo"] == "saida":
            gastos[t["categoria"]] = gastos.get(t["categoria"], 0.0) + float(t["valor"])

    economia = 0.0
    detalhe = []
    for cat in CATEGORIAS_FLEXIVEIS:
        if cat in gastos:
            valor = gastos[cat] * (corte_pct / 100)
            economia += valor
            detalhe.append({
                "categoria": rotulo(cat),
                "gasto_atual_formatado": brl(gastos[cat]),
                "economia_formatado": brl(valor),
            })

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
        f"o que no seu ritmo leva cerca de {m['meses_no_ritmo_atual']} mês(es)."
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


FERRAMENTAS = {
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
