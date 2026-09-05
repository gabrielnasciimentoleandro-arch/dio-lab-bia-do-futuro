"""
agente.py — Orquestrador da agente Luma.

Fluxo:
    pergunta -> [LLM escolhe ferramenta] -> Python calcula -> [LLM redige]
             -> guardrails de compliance -> resposta + fonte

Funciona em dois modos:
  * GEMINI  : usa a API do Google Gemini (function calling nativo).
  * DEMO    : sem chave de API. Roteia por palavras-chave e usa templates.
              Garante que QUALQUER avaliador consiga rodar o projeto.

Convenção de marcadores textuais (a interface converte em ícone):
    [fonte]  citação da origem do dado
    [aviso]  disclaimer de compliance
    [sinal]  bandeira vermelha detectada
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass, field

import ferramentas as tools
from prompts import SYSTEM_PROMPT

MODELO = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --------------------------------------------------------------- guardrails
PADROES_SENSIVEIS = re.compile(
    r"\b(senha|pin|cvv|c[óo]digo de seguran[çc]a|token banc[áa]rio)\b", re.I
)
PADROES_INJECAO = re.compile(
    r"(ignore (as |suas )?(instru[çc][õo]es|regras)|esque[çc]a (as |suas )?regras|"
    r"aja como|voc[êe] agora [ée]|system prompt|revele (seu|o) prompt)", re.I
)
PADROES_TERCEIROS = re.compile(
    r"(de (um|uma|meu|minha|outro|outra) (amigo|amiga|colega|vizinho|vizinha|primo|prima|"
    r"irmao|irma|cliente|pessoa)|do (meu|joao|joão)? ?(amigo|colega|vizinho|chefe)|"
    r"da (minha)? ?(amiga|colega|vizinha|esposa|namorada)|"
    r"dados de (outra|outro) (pessoa|cliente)|conta (do|da) (meu|minha|outro|outra))", re.I
)
PROMESSA_FUTURA = re.compile(
    r"\b(vai render|vai ganhar|garante|garantido|lucro certo|com certeza vai|"
    r"rentabilidade garantida|sem risco)\b", re.I
)

DISCLAIMER = "[aviso] Conteúdo educacional. Não constitui recomendação de investimento."


def _normalizar(t: str) -> str:
    """Minúsculas e sem acento — usado no roteamento por palavra-chave."""
    t = unicodedata.normalize("NFD", t.strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _extrair_valor(texto: str) -> float | None:
    """Extrai valores como '40 mil', 'R$ 40.000', '3k', '1.500,50'."""
    t = texto.replace("r$", " ").strip()

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(mil|k)\b", t)
    if m:
        return float(m.group(1).replace(".", "").replace(",", ".")) * 1000

    m = re.search(r"(\d+(?:\.\d{3})*(?:,\d{2})?|\d+(?:\.\d+)?)", t)
    if m:
        bruto = m.group(1)
        if "," in bruto:
            valor = float(bruto.replace(".", "").replace(",", "."))
        elif bruto.count(".") >= 1 and len(bruto.split(".")[-1]) == 3:
            valor = float(bruto.replace(".", ""))
        else:
            valor = float(bruto)
        return valor if valor >= 100 else None
    return None


@dataclass
class Resposta:
    texto: str
    ferramentas_usadas: list[str] = field(default_factory=list)
    fontes: list[str] = field(default_factory=list)
    latencia_ms: int = 0
    guardrails_acionados: list[str] = field(default_factory=list)
    modo: str = "demo"
    # Se a resposta termina oferecendo um proximo passo ("Quer que eu simule?"),
    # este campo guarda o que um "sim" deve executar.
    oferta: str | None = None


# Cada oferta vira uma chave aqui; o valor e a pergunta que o roteamento ja
# sabe responder. O "sim" reaproveita as rotas existentes.
OFERTAS = {
    "metas": "quanto falta para minhas metas",
    "simular": "simular corte de 30% nos gastos",
    "categorias": "quanto gastei por categoria",
    "resumo": "qual meu resumo do mes",
    "diagnostico": "faz um diagnostico geral das minhas financas",
    "golpes": "quais sao os golpes mais comuns",
    "diario": "me mostra meu diario de aprendizado",
    "produtos": "quais produtos combinam com meu perfil",
    "resiliencia": "quanto tempo eu aguento se perder o emprego",
    "maior_gasto": "quanto gastei com moradia",
}

CONFIRMACAO = re.compile(
    r"^\s*(sim|s|claro|quero|qero|quero sim|sim quero|pode|pode ser|pode sim|"
    r"manda|mandar|bora|vamos|isso|isso ai|isso mesmo|por favor|pf|blz|beleza|"
    r"ok|okay|ta bom|t\u00e1 bom|ta|aceito|topo|show|legal|certo|com certeza|"
    r"seria bom|gostaria|quero ver|ver|mostra|mostrar|me mostra|simula|"
    r"detalha|detalhar|abre|abrir|continua|continuar|segue|uhum|aham|"
    r"afirmativo|positivo|yes|y|sim por favor|quero saber|manda ver)"
    r"[\s!.,?]*$",
    re.I,
)

NEGACAO = re.compile(
    r"^\s*(nao|n\u00e3o|n|nop|agora nao|agora n\u00e3o|depois|deixa|deixa pra la|"
    r"melhor nao|melhor n\u00e3o|nao quero|n\u00e3o quero|nao obrigado|"
    r"talvez depois|nem|no)[\s!.,?]*$",
    re.I,
)


# Mapeia a ferramenta usada -> topico, para "resume isso" saber do que falar.
TOPICO_POR_TOOL = {
    "montar_plano": "plano",
    "resumo_financeiro": "categorias",
    "somar_por_categoria": "categorias",
    "listar_golpes": "golpes",
    "detalhar_golpe": "golpes",
    "analisar_suspeita": "golpes",
    "progresso_metas": "metas",
    "simular_economia": "metas",
    "diagnostico_geral": "diagnostico",
    "recomendar_produtos": "produtos",
    "analisar_resiliencia": "diagnostico",
}


def _topico_de(resposta) -> str | None:
    for tool in resposta.ferramentas_usadas:
        if tool in TOPICO_POR_TOOL:
            return TOPICO_POR_TOOL[tool]
    return None


def _validar_entrada(pergunta: str) -> tuple[str, str] | None:
    """Guardrails de ENTRADA. Retorna (motivo, resposta) se deve bloquear."""
    if PADROES_SENSIVEIS.search(pergunta):
        return (
            "dado_sensivel",
            "Não trabalho com senhas, PIN ou CVV — e um conselho importante: "
            "nunca compartilhe esses dados com ninguém, nem com atendentes do banco.\n\n"
            "Posso ajudar com seus gastos, metas ou produtos. O que você prefere?",
        )
    if PADROES_TERCEIROS.search(_normalizar(pergunta)):
        return (
            "privacidade_terceiros",
            "Consigo acessar apenas os seus dados — não tenho e não posso consultar "
            "informações financeiras de outras pessoas, mesmo que sejam próximas a você. "
            "Isso vale para todo mundo: os dados de cada cliente ficam protegidos.\n\n"
            "Se quiser, seu amigo pode conversar comigo pela conta dele. "
            "Enquanto isso, posso continuar com as suas finanças — quer ver o resumo do mês?",
        )
    if PADROES_INJECAO.search(pergunta):
        return (
            "prompt_injection",
            "Minhas regras de funcionamento são fixas e não podem ser alteradas "
            "durante a conversa — é isso que garante que eu não invente informações "
            "sobre o seu dinheiro.\n\nMas sigo à disposição: quer ver o progresso "
            "da sua reserva de emergência?",
        )
    return None


def _validar_saida(texto: str, usou_produtos: bool) -> tuple[str, list[str]]:
    """Guardrails de SAÍDA: compliance antes de entregar ao usuário."""
    acionados: list[str] = []

    if PROMESSA_FUTURA.search(texto):
        texto = PROMESSA_FUTURA.sub("historicamente rendeu", texto)
        acionados.append("promessa_rentabilidade_removida")

    if usou_produtos and DISCLAIMER not in texto:
        texto += f"\n\n{DISCLAIMER}"
        acionados.append("disclaimer_injetado")

    return texto, acionados


# ------------------------------------------------------------------- schemas
SCHEMAS = [
    {
        "name": "somar_por_categoria",
        "description": "Soma quanto o cliente gastou numa categoria específica "
                       "(alimentacao, moradia, transporte, saude, lazer).",
        "parameters": {
            "type": "object",
            "properties": {"categoria": {"type": "string",
                                         "description": "Categoria em minúsculas, sem acento."}},
            "required": ["categoria"],
        },
    },
    {
        "name": "resumo_financeiro",
        "description": "Panorama do mês: entradas, saídas, saldo, taxa de poupança e ranking.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_perfil",
        "description": "Dados cadastrais do cliente: idade, renda, perfil e metas.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "progresso_metas",
        "description": "Progresso das metas, quanto falta, aporte necessário e se está no ritmo.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "recomendar_produtos",
        "description": "Produtos compatíveis com o perfil e os bloqueados por risco.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "simular_economia",
        "description": "Simula cortar uma porcentagem dos gastos. Aceita categorias específicas e categorias que o cliente NÃO pode cortar.",
        "parameters": {
            "type": "object",
            "properties": {
                "corte_pct": {"type": "number", "description": "Padrão 30."},
                "categorias": {"type": "array", "items": {"type": "string"},
                               "description": "Cortar apenas estas categorias."},
                "excluir": {"type": "array", "items": {"type": "string"},
                            "description": "Categorias que o cliente vetou."},
            },
        },
    },
    {
        "name": "montar_plano",
        "description": ("Monta um plano de ação em etapas para atingir a reserva. "
                        "Use quando o cliente pedir plano, planejamento ou 'o que fazer'. "
                        "sem_cortes=true quando ele pedir para não reduzir gastos."),
        "parameters": {
            "type": "object",
            "properties": {"sem_cortes": {"type": "boolean",
                                          "description": "True se o cliente vetou cortes."}},
        },
    },
    {
        "name": "historico_atendimento",
        "description": "Atendimentos anteriores do cliente e temas recorrentes.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "analisar_resiliencia",
        "description": "Quantos meses o cliente sobrevive com a reserva se perder a renda.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "avaliar_compra",
        "description": "Avalia se uma compra cabe no orçamento e o quanto atrasa a meta.",
        "parameters": {
            "type": "object",
            "properties": {"valor": {"type": "number", "description": "Valor da compra em reais."}},
            "required": ["valor"],
        },
    },
    {
        "name": "diagnostico_geral",
        "description": "Diagnóstico com pontos fortes, atenção e a próxima ação prioritária.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "listar_golpes",
        "description": "Catálogo dos golpes financeiros mais comuns e as regras de ouro.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "detalhar_golpe",
        "description": "Ficha completa de um golpe: como funciona, sinais e conduta.",
        "parameters": {
            "type": "object",
            "properties": {"golpe_id": {"type": "string"}},
            "required": ["golpe_id"],
        },
    },
    {
        "name": "analisar_suspeita",
        "description": "Analisa o relato de uma abordagem suspeita e classifica o risco de golpe.",
        "parameters": {
            "type": "object",
            "properties": {"relato": {"type": "string", "description": "Descrição da situação."}},
            "required": ["relato"],
        },
    },
    {
        "name": "registrar_incidente",
        "description": "Registra um golpe sofrido no diário de aprendizado do cliente.",
        "parameters": {
            "type": "object",
            "properties": {
                "golpe_id": {"type": "string"},
                "relato": {"type": "string"},
                "valor": {"type": "number"},
                "caiu": {"type": "boolean"},
            },
            "required": ["golpe_id", "relato"],
        },
    },
    {
        "name": "consultar_diario",
        "description": "Histórico de incidentes de golpe e lições aprendidas.",
        "parameters": {"type": "object", "properties": {}},
    },
]


class AgenteLuma:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.modo = "demo"
        self.client = None
        self._fallbacks = 0
        self._oferta_pendente: str | None = None
        # Memória de curto prazo: sobre o que a última resposta falou. Permite
        # "resume isso", "me dá só duas" e "qual a mais importante" — pedidos
        # que só fazem sentido em relação à resposta anterior.
        self._ultimo_topico: str | None = None

        if self.api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(
                    model_name=MODELO,
                    system_instruction=SYSTEM_PROMPT,
                    tools=[{"function_declarations": SCHEMAS}],
                )
                self.chat = self.client.start_chat()
                self.modo = "gemini"
            except Exception as e:  # pragma: no cover
                print(f"[Luma] Gemini indisponível ({e}). Usando modo demo.")

    # ------------------------------------------------------------ público
    def responder(self, pergunta: str) -> Resposta:
        inicio = time.perf_counter()

        bloqueio = _validar_entrada(pergunta)
        if bloqueio:
            motivo, texto = bloqueio
            return Resposta(
                texto=texto,
                latencia_ms=int((time.perf_counter() - inicio) * 1000),
                guardrails_acionados=[motivo],
                modo=self.modo,
            )

        # --- resolucao de oferta pendente -------------------------------
        # A agente termina quase toda resposta oferecendo um proximo passo.
        # Sem memoria dessa oferta, um "sim quero" caia no fallback: ela
        # perguntava e nao entendia a resposta.
        pendente = self._oferta_pendente
        if pendente and CONFIRMACAO.match(pergunta.strip()):
            self._oferta_pendente = None
            self._fallbacks = 0
            r = self._responder_demo(OFERTAS[pendente])
            r.guardrails_acionados.append(f"oferta_aceita:{pendente}")
            r.texto, extras = _validar_saida(
                r.texto, "recomendar_produtos" in r.ferramentas_usadas)
            r.guardrails_acionados += extras
            r.latencia_ms = int((time.perf_counter() - inicio) * 1000)
            r.modo = self.modo
            self._oferta_pendente = r.oferta
            self._ultimo_topico = _topico_de(r) or self._ultimo_topico
            return r

        if pendente and NEGACAO.match(pergunta.strip()):
            self._oferta_pendente = None
            primeiro = tools.PERFIL["nome"].split()[0]
            return Resposta(
                texto=f"Tranquilo, {primeiro}. Fico por aqui então — quando quiser "
                      f"revisar seus gastos, suas metas ou tirar dúvida sobre "
                      f"alguma abordagem suspeita, é só chamar.",
                latencia_ms=int((time.perf_counter() - inicio) * 1000),
                modo=self.modo,
            )

        if self.modo == "gemini":
            r = self._responder_gemini(pergunta)
        else:
            r = self._responder_demo(pergunta)

        r.texto, extras = _validar_saida(r.texto, "recomendar_produtos" in r.ferramentas_usadas)
        r.guardrails_acionados += extras
        r.latencia_ms = int((time.perf_counter() - inicio) * 1000)
        r.modo = self.modo
        self._oferta_pendente = r.oferta
        self._ultimo_topico = _topico_de(r) or self._ultimo_topico
        return r

    # ------------------------------------------------------------- gemini
    def _responder_gemini(self, pergunta: str) -> Resposta:
        usadas: list[str] = []
        fontes: list[str] = []

        resp = self.chat.send_message(pergunta)

        for _ in range(5):  # até 5 rodadas de tool-calling
            chamadas = [
                p.function_call
                for p in resp.candidates[0].content.parts
                if getattr(p, "function_call", None) and p.function_call.name
            ]
            if not chamadas:
                break

            respostas_tools = []
            for fc in chamadas:
                args = dict(fc.args) if fc.args else {}
                resultado = tools.executar(fc.name, args)
                usadas.append(fc.name)
                if "_fonte" in resultado:
                    fontes.append(resultado["_fonte"])
                respostas_tools.append(
                    {"function_response": {"name": fc.name, "response": resultado}}
                )

            resp = self.chat.send_message(respostas_tools)

        texto = "".join(
            p.text for p in resp.candidates[0].content.parts if getattr(p, "text", None)
        ).strip()

        return Resposta(texto=texto, ferramentas_usadas=usadas,
                        fontes=list(dict.fromkeys(fontes)))

    # --------------------------------------------------------------- demo
    def _responder_demo(self, pergunta: str) -> Resposta:
        """Roteamento por palavra-chave. Mesmas ferramentas, redação por template."""
        p = _normalizar(pergunta)
        nome = tools.PERFIL["nome"].split()[0]

        # ------------------------------------------------- refinar resposta
        # "resume", "me dá só duas", "qual a mais importante": pedidos que se
        # referem ao que a agente ACABOU de dizer. Sem memória do último
        # tópico, caíam no fallback — a conversa não se interligava.
        # "me mostra um resumo dos gastos" e consulta, nao pedido de sintese.
        # So tratamos como refinamento quando o resumo se refere ao que ja foi
        # dito ("resume isso", "resume ai") ou vem sozinho ("resume").
        pede_resumo_novo = re.search(r"\b(resumo|resumao)\b.*\b(gasto|mes|mês|"
                                     r"financ\w+|conta|extrato|categoria)", p)
        quer_menos = None if pede_resumo_novo else re.search(
            r"\b(simplific\w+|resum[ae]\b|resumir|encurt\w+|mais curto|muito longo|"
            r"muito grande|muita coisa|so o essencial|só o essencial|"
            r"direto ao ponto|objetiv\w+|preguica|preguiça|"
            r"(me )?d[ae] (so|só|apenas) )", p)
        quer_top = re.search(
            r"\b(duas|dois|tres|três|3|2|1|uma|um)\b.*\b(opcoes|opções|opcao|"
            r"opção|melhores|principais|mais importantes|dicas|coisas|etapas)\b"
            r"|\b(qual|quais)\b.*\b(mais importante|prioridade|primeiro|"
            r"melhor|comeco por|começo por)\b|\bso as? (duas|dois|principais)\b", p)

        if (quer_menos or quer_top) and self._ultimo_topico:
            return self._refinar(self._ultimo_topico, p, nome, quer_top)

        # ---------------------------------------------------- conversação
        SAUDACAO = (r"(oi+|ola+|opa|eai|e ai|fala|alo+|hey|hello|hi|"
                    r"bom dia|boa tarde|boa noite)")
        COMPLEMENTO = r"(tudo bem|tudo bom|beleza|como vai|td bem)"
        if re.fullmatch(rf"{SAUDACAO}([ ,!]+{COMPLEMENTO})?[ !.?]*", p) or \
           re.fullmatch(rf"{COMPLEMENTO}[ ,!]*({SAUDACAO})?[ !.?]*", p):
            metas = tools.progresso_metas()
            m = metas["metas"][0]
            return Resposta(
                texto=f"Olá, {nome}! Tudo bem por aqui.\n\n"
                      f"Sua reserva de emergência está **{m['progresso_pct']}% concluída** — "
                      f"faltam **{m['falta_formatado']}**.\n\n"
                      f"Posso te ajudar com:\n"
                      f"- Gastos por categoria (*\"quanto gastei com alimentação?\"*)\n"
                      f"- Progresso das metas (*\"quanto falta pra minha meta?\"*)\n"
                      f"- Simulação de economia (*\"simule um corte de 30%\"*)\n"
                      f"- Segurança contra golpes (*\"recebi uma ligação suspeita\"*)\n\n"
                      f"O que você quer ver primeiro?\n\n[fonte] {metas['_fonte']}",
                ferramentas_usadas=["progresso_metas"], fontes=[metas["_fonte"]],
            )

        if re.fullmatch(r"(muito )?(obrigad[oa]|valeu|vlw|tks|thanks|show|"
                        r"legal|otimo|perfeito|top|entendi|ok|blz)[!.]*", p):
            return Resposta(
                texto=f"Por nada, {nome}. Sempre que quiser revisar seus números "
                      f"ou simular um cenário, é só chamar.\n\n"
                      f"Quer que eu já deixe uma sugestão de próximo passo para a sua reserva?",
                oferta="metas",
            )

        # ------------------------------------------------------- fora de escopo
        # ATENCAO: "tempo" como substring capturava "em quanto TEMPO eu tenho
        # lucro?" — uma pergunta financeira legitima. Clima exige contexto
        # explicito; nunca a palavra solta.
        fora_escopo_re = (
            r"\b(previsao do tempo|tempo (hoje|amanha|agora)|clima|chuva|chove|"
            r"temperatura|futebol|campeonato|placar|receita de|politica|"
            r"presidente|eleicao|piada|musica|filme|namorad)\w*\b"
        )
        if re.search(fora_escopo_re, p) and not any(
            t in p for t in ("gast", "invest", "meta", "reserva", "saldo", "golpe",
                             "lucro", "render", "dinheiro")
        ):
            return Resposta(
                texto=f"Essa eu não sei mesmo, {nome} — desculpa. Cuido só das suas "
                      f"finanças, e fora desse assunto eu não seria de muita ajuda.\n\n"
                      f"Mas se quiser, posso te mostrar como está a sua reserva de "
                      f"emergência. Topa?",
                oferta="metas",
            )

        # --- suporte técnico: FORA DO ESCOPO
        # A Luma cuida do dinheiro, não do aparelho. Um agente financeiro que
        # opina sobre celular infectado está inventando fora da sua base — o
        # oposto do princípio anti-alucinação. Recusa explícita e reconduz.
        aparelho = r"(celular|telefone|aparelho|smartphone|notebook|computador|pc)"
        sintoma = (r"(lent[oa]|quente|esquenta\w*|trava\w*|devagar|estranh[oa]|"
                   r"infectad[oa]|virus|v[ií]rus|malware|lerd[oa]|bateria|"
                   r"reinicia\w*|desliga\w*|formatar|atualiza\w*)")
        if (re.search(rf"\b{aparelho}\b(?:\W+\w+){{0,4}}?\W+\b{sintoma}\b", p)
                or re.search(rf"\b{sintoma}\b(?:\W+\w+){{0,4}}?\W+\b{aparelho}\b", p)):
            return Resposta(
                texto=f"Desculpa, {nome} — isso eu não sei avaliar. Cuido das suas "
                      f"finanças, não da parte técnica do aparelho. Se eu palpitasse "
                      f"sobre o seu celular estaria inventando, e prefiro te dizer a "
                      f"verdade: não é a minha área.\n\n"
                      f"Para isso, vale procurar a assistência técnica ou o suporte do "
                      f"fabricante.\n\n"
                      f"Agora, se o que te preocupa é o **seu dinheiro** — uma cobrança "
                      f"que você não reconhece, uma mensagem estranha pedindo Pix ou uma "
                      f"ligação suspeita —, aí sim me conta que eu analiso com você."
            )

        # --- expectativa de lucro / enriquecer rápido
        # Tema CENTRAL de educação financeira: nao pode cair no fallback.
        # A Luma nao promete retorno (compliance), mas tambem nao se esquiva:
        # devolve o horizonte real calculado com os numeros do proprio cliente.
        # Relato de OFERTA suspeita ("me ofereceram 10% ao mes garantido") nao e
        # duvida sobre lucro: e antifraude. Deixa passar para analisar_suspeita.
        oferta_suspeita = (
            re.search(r"\b(me ofereceram|me oferecer\w*|me chamaram|me convidaram|"
                      r"apareceu uma oferta|recebi uma proposta|me mandaram)\b", p)
            or re.search(r"\b(garantid\w+|risco zero|sem risco|lucro certo)\b", p)
        )
        if not oferta_suspeita and (
                re.search(r"\b(lucr\w+|render|rende|rendimento|rentabilidade|"
                          r"enriquecer|ficar rico|dobrar|multiplicar)\b", p)
                or re.search(r"\bganhar (mais )?dinheiro\b", p)
                or re.search(r"\bdinheiro (rapido|facil)\b", p)
                or re.search(r"\b(quanto|quando|em quanto tempo)\b.*\b(vou ter|"
                             r"consigo|posso ter|tempo)\b.*\b(lucro|retorno|"
                             r"dinheiro)\b", p)):
            pr = tools.recomendar_produtos()
            res = tools.resumo_financeiro()
            met = tools.progresso_metas()["metas"][0]
            top = pr["produtos_compativeis"][0] if pr["produtos_compativeis"] else None

            pressa = bool(re.search(r"\b(rapido|facil|urgente|ja|agora|"
                                    r"enriquecer|ficar rico|dobrar)\b", p))

            abertura = (
                f"Vou ser honesta com você, {nome}, mesmo que não seja o que você "
                f"quer ouvir: **não existe ganho rápido e seguro**. Toda promessa de "
                f"lucro alto em pouco tempo ou é risco escondido, ou é golpe — dos "
                f"nove que eu monitoro, três começam exatamente assim.\n\n"
                if pressa else
                f"Boa pergunta, {nome}. Não posso prometer retorno nenhum — ninguém "
                f"pode, e quem promete está mentindo. Mas posso te mostrar o que os "
                f"seus números dizem.\n\n"
            )

            corpo = (
                f"O que eu **posso** afirmar, olhando a sua base:\n\n"
                f"- Você sobra **{res['saldo_formatado']}** por mês. Esse é o seu "
                f"motor real de crescimento — bem mais previsível que rendimento.\n"
                f"- Faltam **{met['falta_formatado']}** para fechar sua reserva de "
                f"emergência: {tools.prazo_texto(met['meses_no_ritmo_atual'])}.\n"
            )
            if top:
                corpo += (f"- Compatível com seu perfil **{pr['perfil_investidor']}**: "
                          f"**{top['nome']}**, que rende {top['rentabilidade']} "
                          f"ao ano, com risco {top['risco']}.\n")
            if pr["produtos_bloqueados"]:
                corpo += (f"- Deixei **{len(pr['produtos_bloqueados'])} produto(s)** de "
                          f"fora: rendem mais, mas você declarou não aceitar risco.\n")

            fecho = ("\nA sequência que faz sentido é: primeiro a reserva de "
                     "emergência, depois investir o excedente. Investir antes de ter "
                     "reserva costuma terminar em resgate no pior momento.\n\n"
                     "Quer que eu simule quanto você acelera cortando 30% de uma "
                     "categoria?")

            return Resposta(
                texto=abertura + corpo + fecho + f"\n\n[fonte] {pr['_fonte']}",
                ferramentas_usadas=["recomendar_produtos", "resumo_financeiro",
                                    "progresso_metas"],
                fontes=[pr["_fonte"], res["_fonte"]],
                oferta="simular",
            )

        # ======================================================== ANTIFRAUDE
        # --- relato de golpe já sofrido
        if any(t in p for t in ("cai no golpe", "cai num golpe", "fui golpead",
                                "me golpearam", "fui enganad", "perdi dinheiro",
                                "me roubaram", "sofri um golpe", "fui vitima",
                                "me aplicaram", "registrar golpe", "cai nesse")):
            a = tools.analisar_suspeita(pergunta)
            valor = _extrair_valor(p) or 0.0
            gid = a["golpe_provavel"]["id"] if a["golpe_provavel"] else "nao_classificado"
            r = tools.registrar_incidente(gid, pergunta, valor, caiu=True)
            inc = r["incidente"]

            sinais = "\n".join(f"- {s}" for s in inc["sinais_que_passaram"]) or \
                     "- Urgência para movimentar dinheiro"
            perda = (f"\n\nValor registrado: **{r['valor_perdido_formatado']}**."
                     if inc["valor_perdido"] > 0 else "")

            return Resposta(
                texto=f"Sinto muito que isso tenha acontecido com você. E quero dizer uma "
                      f"coisa antes de tudo: **cair em golpe não é burrice**. Esses ataques "
                      f"são desenhados por profissionais para explorar pressa e confiança — "
                      f"acontece com gente muito atenta.\n\n"
                      f"Registrei no seu **diário de aprendizado** como *{inc['golpe_nome']}*."
                      f"{perda}\n\n"
                      f"**Os sinais que costumam aparecer nesse golpe:**\n{sinais}\n\n"
                      f"**Lição para guardar:** {inc['licao']}\n\n"
                      f"**Providências agora:**\n"
                      f"1. Avise seu banco imediatamente pelo canal oficial\n"
                      f"2. Registre um boletim de ocorrência (dá para fazer online)\n"
                      f"3. Se foi Pix, peça ao banco a abertura do MED\n"
                      f"4. Troque suas senhas\n\n"
                      f"Vou lembrar desse episódio para te alertar se algo parecido "
                      f"aparecer. Quer ver seu diário completo?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["analisar_suspeita", "registrar_incidente"],
                fontes=[r["_fonte"]],
                oferta="diario",
            )

        # --- diário de aprendizado
        if any(t in p for t in ("meu diario", "diario de golpe", "diario de aprendiz",
                                "meus incidentes", "golpes que sofri",
                                "historico de golpe", "ja cai em algum")):
            r = tools.consultar_diario()
            if r["vazio"]:
                return Resposta(
                    texto="Seu diário de golpes está vazio — e esse é o melhor cenário "
                          "possível.\n\nSe algum dia você passar por uma situação suspeita, "
                          "me conte: eu registro, explico os sinais e guardo a lição para "
                          "te alertar depois.\n\nQuer conhecer os golpes mais comuns antes "
                          "que eles cheguem até você?",
                    ferramentas_usadas=["consultar_diario"], fontes=[r["_fonte"]],
                )
            linhas = "\n".join(
                f"- **{i['data']}** — {i['golpe']} ({i['valor_formatado']})\n  *{i['licao']}*"
                for i in r["incidentes"]
            )
            return Resposta(
                texto=f"Seu diário de aprendizado tem **{r['total']} registro(s)**, "
                      f"com perda total de **{r['total_perdido_formatado']}**.\n\n{linhas}\n\n"
                      f"Tipo mais recorrente: **{r['tipo_recorrente']}** — vale redobrar a "
                      f"atenção com esse padrão.\n\n"
                      f"Cada registro aqui é uma defesa a mais. Quer revisar os sinais "
                      f"desse golpe?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["consultar_diario"], fontes=[r["_fonte"]],
            )

        # --- análise de suspeita em andamento
        if any(t in p for t in ("e golpe", "isso e golpe", "sera golpe", "parece golpe",
                                "desconfi", "suspeit", "me ligaram", "recebi uma ligacao",
                                "recebi um sms", "recebi uma mensagem", "me mandaram",
                                "me ofereceram", "pediram meu", "pediram que eu",
                                "conta segura", "recebi um pix", "pix por engano",
                                "clicei no link", "cliquei no link", "e confiavel",
                                "posso confiar", "verificar se")):
            a = tools.analisar_suspeita(pergunta)

            if a["golpe_provavel"]:
                g = a["golpe_provavel"]
                sinais = "\n".join(f"- {s}" for s in g["sinais_de_alerta"][:4])
                acoes = "\n".join(f"{i}. {x}" for i, x in enumerate(g["o_que_fazer"], 1))
                corpo = (f"**Risco {a['nivel_risco']}** — {a['veredito']}\n\n"
                         f"O padrão que você descreveu bate com **{g['nome']}**.\n\n"
                         f"**Sinais típicos desse golpe:**\n{sinais}\n\n"
                         f"**O que fazer agora:**\n{acoes}\n\n"
                         f"**{g['frase_chave']}**")
            else:
                regras = "\n".join(f"- {x}" for x in a["regras_de_ouro"])
                corpo = (f"**{a['veredito']}**\n\n"
                         f"Não reconheci um padrão específico no seu relato, mas guarde "
                         f"estas regras:\n\n{regras}\n\n"
                         f"Me conte mais detalhes se quiser que eu analise melhor.")

            if a["bandeiras_vermelhas"]:
                nomes = {"urgencia": "pressa artificial", "sigilo": "pedido de sigilo",
                         "dado_sensivel": "pedido de dado sensível",
                         "pagamento_pf": "pagamento para pessoa física"}
                bf = ", ".join(nomes.get(b, b) for b in a["bandeiras_vermelhas"])
                corpo += f"\n\n[sinal] Sinais genéricos detectados: {bf}."

            return Resposta(
                texto=f"{corpo}\n\nSe você já perdeu dinheiro, me avise que eu registro "
                      f"no seu diário de aprendizado.\n\n[fonte] {a['_fonte']}",
                ferramentas_usadas=["analisar_suspeita"], fontes=[a["_fonte"]],
            )

        # --- catálogo educativo de golpes
        if any(t in p for t in ("golpe", "fraude", "seguranca", "me proteger", "protecao",
                                "phishing", "estelionato", "como nao cair")):
            r = tools.listar_golpes()
            lista = "\n".join(f"- **{g['nome']}** — *{g['frase_chave']}*" for g in r["golpes"])
            regras = "\n".join(f"{i}. {x}" for i, x in enumerate(r["regras_de_ouro"][:5], 1))
            return Resposta(
                texto=f"Ótimo que você quer se prevenir — essa é a melhor defesa.\n\n"
                      f"**As {r['total']} fraudes mais comuns hoje:**\n{lista}\n\n"
                      f"**Regras de ouro:**\n{regras}\n\n"
                      f"Quer que eu detalhe algum desses golpes? Ou, se recebeu algo "
                      f"suspeito, me descreva a situação que eu analiso.\n\n"
                      f"[fonte] {r['_fonte']}",
                ferramentas_usadas=["listar_golpes"], fontes=[r["_fonte"]],
                oferta="golpes",
            )

        # ==================================================== VIDA FINANCEIRA
        # --- resiliência: "e se eu perder o emprego?"
        if any(t in p for t in ("perder o emprego", "perder meu emprego",
                                "ficar desempregado", "desemprego", "for demitido",
                                "ser demitido", "me demitir", "quanto tempo eu aguento",
                                "quanto tempo sobrevivo", "der errado", "acontecer algo")):
            r = tools.analisar_resiliencia()
            return Resposta(
                texto=f"Essa é exatamente a pergunta que a reserva de emergência existe "
                      f"para responder.\n\n"
                      f"Com **{r['reserva_atual_formatado']}** guardados e um custo de vida "
                      f"de **{r['custo_mensal_formatado']}** por mês, você teria "
                      f"**{r['meses_de_folego']} meses** de fôlego sem nenhuma renda.\n\n"
                      f"Cortando o supérfluo (lazer e parte da alimentação), esse prazo "
                      f"sobe para **{r['meses_de_folego_enxuto']} meses**.\n\n"
                      f"Leitura: nível **{r['nivel']}** — {r['leitura']}. "
                      f"Quando você completar a meta de reserva, chega a "
                      f"**{r['meses_cobertos_pela_meta']} meses**.\n\n"
                      f"Quer ver como acelerar até lá?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["analisar_resiliencia"], fontes=[r["_fonte"]],
                oferta="simular",
            )

        # --- avaliação de compra
        if any(t in p for t in ("posso comprar", "vale a pena comprar", "consigo comprar",
                                "da pra comprar", "quero comprar", "penso em comprar",
                                "trocar de carro", "comprar um carro", "financiar")):
            valor = _extrair_valor(p)
            if valor:
                r = tools.avaliar_compra(valor)
                if r["veredito"] == "prematuro":
                    corpo = (
                        f"Antes de {r['valor_formatado']}, tem uma coisa na frente: "
                        f"faltam **{r['falta_reserva_formatado']}** para fechar sua reserva "
                        f"de emergência.\n\n"
                        f"Se você usar o saldo para essa compra, ficaria sem colchão — e é "
                        f"justamente aí que as pessoas acabam recorrendo a crédito caro.\n\n"
                        f"No seu ritmo, juntar {r['valor_formatado']} levaria cerca de "
                        f"**{r['meses_poupando']} meses**.\n\n"
                        f"Sugestão: fecha a reserva primeiro (faltam poucos meses) e depois "
                        f"a gente planeja essa compra com tranquilidade. "
                        f"Quer montar esse plano?"
                    )
                elif r["veredito"] == "pesado":
                    corpo = (f"{r['valor_formatado']} equivale a cerca de "
                             f"**{r['meses_poupando']} meses** do seu saldo mensal "
                             f"({r['saldo_mensal_formatado']}). É um compromisso pesado.\n\n"
                             f"Quer que eu simule um prazo de poupança para essa meta?")
                else:
                    corpo = (f"Considerando seu saldo de {r['saldo_mensal_formatado']}/mês e "
                             f"a reserva já completa, {r['valor_formatado']} representa cerca "
                             f"de **{r['meses_poupando']} meses** de poupança. É viável com "
                             f"planejamento.\n\nQuer que eu monte o cronograma?")
                return Resposta(
                    texto=f"{corpo}\n\n[fonte] {r['_fonte']}",
                    ferramentas_usadas=["avaliar_compra"], fontes=[r["_fonte"]],
                    oferta="simular",
                )

        # --- dívida
        if any(t in p for t in ("endividad", "divida", "dividas", "devendo",
                                "no vermelho", "cheque especial", "rotativo",
                                "atrasad", "negativad", "nome sujo", "spc", "serasa")):
            r = tools.resumo_financeiro()
            return Resposta(
                texto=f"Sinto muito que esteja passando por isso — e você deu o passo mais "
                      f"difícil, que é encarar a situação.\n\n"
                      f"Preciso ser transparente: **não tenho suas dívidas na base**, então "
                      f"não consigo calcular juros ou montar um plano de quitação com "
                      f"números reais.\n\n"
                      f"O que eu consigo mostrar é sua capacidade de pagamento: hoje sobram "
                      f"**{r['saldo_formatado']}** por mês, e sua maior despesa é "
                      f"**{r['maior_gasto']['categoria']}** "
                      f"({r['maior_gasto']['valor_formatado']}).\n\n"
                      f"Uma orientação geral: priorize sempre a dívida de **maior juro** "
                      f"(cartão rotativo e cheque especial costumam ser os mais caros) e "
                      f"procure o banco para negociar — quase sempre há espaço.\n\n"
                      f"Quer que eu simule quanto você liberaria por mês cortando gastos?\n\n"
                      f"[fonte] {r['_fonte']}",
                ferramentas_usadas=["resumo_financeiro"], fontes=[r["_fonte"]],
                oferta="simular",
            )

        # --- diagnóstico / conselho aberto
        if any(t in p for t in ("me da um conselho", "me de um conselho", "diagnostico",
                                "como estou", "como estao minhas financas", "vou bem",
                                "estou bem", "o que voce acha", "me avalia", "analisa",
                                "o que eu faco", "por onde comeco", "o que devo fazer",
                                "o que fazer", "sobrando", "sobrou")) \
           or re.search(r"\b(uma |alguma )?dicas?\b", p):
            r = tools.diagnostico_geral()
            fortes = "\n".join(f"- {x}" for x in r["pontos_fortes"])
            atencao = "\n".join(f"- {x}" for x in r["pontos_de_atencao"])
            return Resposta(
                texto=f"Fiz um diagnóstico geral das suas finanças:\n\n"
                      f"**O que está indo bem**\n{fortes}\n\n"
                      f"**O que merece atenção**\n{atencao}\n\n"
                      f"**Prioridade agora:** {r['prioridade']}\n\n"
                      f"Quer que eu detalhe algum desses pontos?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["diagnostico_geral"], fontes=[r["_fonte"]],
                oferta="diagnostico",
            )

        # --- quem é você / ajuda
        if any(t in p for t in ("quem e voce", "o que voce faz", "como funciona",
                                "voce pode", "help", "o que voce sabe",
                                "no que voce pode", "suas funcoes", "seus recursos")) \
           or re.fullmatch(r"(me )?ajuda?[!.?]*", p):
            return Resposta(
                texto=f"Sou a **Luma**, sua agente financeira. Trabalho só com os dados "
                      f"reais da sua base — e nunca invento números.\n\n"
                      f"Consigo te ajudar com:\n"
                      f"- **Gastos**: quanto você gastou em cada categoria\n"
                      f"- **Resumo do mês**: entradas, saídas, saldo e taxa de poupança\n"
                      f"- **Metas**: progresso, quanto falta e se está no ritmo\n"
                      f"- **Simulações**: impacto de cortar gastos no prazo da meta\n"
                      f"- **Produtos**: os compatíveis com seu perfil "
                      f"{tools.PERFIL['perfil_investidor']}\n"
                      f"- **Segurança**: identificar golpes e proteger seu celular\n\n"
                      f"Todo número que eu falo vem com a fonte. Por onde começamos?"
            )

        # --- plano de ação (cocriação)
        # Precisa vir ANTES da simulação: "vamos poupar sem cortar gastos" tem
        # a palavra "poupar" e era capturado pelo corte automático — sugerindo
        # exatamente o que o cliente acabara de vetar.
        pede_plano = re.search(
            r"\b(plano|planejamento|planejar|estrategia|estratégia|"
            r"organizar|organizacao|roteiro|caminho|passo a passo|"
            r"por onde (eu )?(comec|começ|inici)\w*|o que (eu )?(faco|faço|fazer)|"
            r"o que podemos fazer|o que fazer|me ajuda a|"
            r"vamos (bolar|montar|criar|fazer|pensar|traçar|tracar))\b", p
        )
        quer_poupar = re.search(r"\b(poupar|guardar|juntar|economizar mais|"
                                r"render mais|fazer render)\b", p)

        if pede_plano or (quer_poupar and re.search(
                r"\b(sem cortar|nao cortar|não cortar|sem mexer|sem reduzir|"
                r"com o que (ja|já) (tenho|tenhos|sobra)|sem tirar)\b", p)):

            # O cliente pode vetar cortes explicitamente.
            sem_cortes = bool(re.search(
                r"\b(sem cortar|nao cortar|não cortar|sem mexer|sem reduzir|"
                r"sem tirar|nao quero cortar|não quero cortar|"
                r"com o que (ja|já) (tenho|tenhos|sobra)|sem abrir mao|"
                r"sem abrir mão|mantendo meus gastos)\b", p))

            r = tools.montar_plano(sem_cortes=sem_cortes)

            abertura = (
                f"Vamos montar juntos, {nome}. E olhando seus números, a boa "
                f"notícia é que **você não precisa cortar nada** — já sobra "
                f"{r['saldo_disponivel_formatado']} por mês, "
                f"{r['taxa_poupanca_pct']}% da sua renda. O problema não é "
                f"quanto sobra, é que esse dinheiro fica solto.\n\n"
                if sem_cortes else
                f"Vamos montar juntos, {nome}. Parti do que a sua base já "
                f"mostra: você fecha o mês com {r['saldo_disponivel_formatado']} "
                f"e faltam {r['falta_reserva_formatado']} para a reserva.\n\n"
            )

            corpo = "\n\n".join(
                f"**{i}. {e['titulo']}**\n{e['acao']}\n*Resultado:* {e['impacto']}"
                for i, e in enumerate(r["etapas"], 1)
            )

            extra = ""
            if r["alavanca_opcional"]:
                a = r["alavanca_opcional"]
                extra = f"\n\n---\n\n**{a['titulo']}** — {a['acao']} ({a['impacto']})"

            fecho = ("\n\nEsse é o esqueleto. Me diz qual etapa faz sentido para a "
                     "sua realidade que a gente ajusta — se alguma não couber, "
                     "eu refaço o plano sem ela.")

            return Resposta(
                texto=abertura + corpo + extra + fecho + f"\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["montar_plano"], fontes=[r["_fonte"]],
                oferta="metas",
            )

        # --- simulação
        if (re.search(r"\b(simul\w*|cort\w+|economi\w+|reduz\w+|antecip\w+|"
                      r"sobraria|poupar mais|gastar menos)\b", p)
                or "outra coisa" in p or "outra opcao" in p):
            m = re.search(r"(\d{1,2})\s*%", p)
            pct = float(m.group(1)) if m else 30.0

            # O cliente pode vetar categorias ("moradia não posso", "menos
            # aluguel") ou pedir uma específica ("corta do transporte").
            mencionadas = tools.detectar_categorias(p)
            veto_re = (r"(nao posso|não posso|nao da|não dá|nao dah|impossivel|"
                       r"nao consigo|não consigo|menos|exceto|fora|tirando|"
                       r"sem mexer|nao quero cortar|não quero cortar|precisa|"
                       r"nao tem como|não tem como)")
            tem_veto = bool(re.search(veto_re, p))

            excluir = mencionadas if tem_veto else None
            categorias = mencionadas if (mencionadas and not tem_veto) else None

            # "me indique outra coisa" após uma simulação: veta o que já foi
            # sugerido e procura alternativa.
            if re.search(r"\b(outra coisa|outra opcao|outra categoria|"
                         r"alguma outra|mais alguma)\b", p) and not mencionadas:
                excluir = list(tools.CATEGORIAS_FLEXIVEIS)

            r = tools.simular_economia(pct, categorias=categorias, excluir=excluir)

            if r["sem_categorias"]:
                alt = r["alternativas"]
                lista = "\n".join(
                    f"- **{a['categoria']}**: gasta {a['gasto_formatado']}, "
                    f"cortando {pct:.0f}% economizaria {a['economia_possivel_formatado']}"
                    for a in alt[:4]
                ) or "- Não sobrou categoria com gasto registrado."
                return Resposta(
                    texto=f"Entendi, {nome} — tirando o que você não pode mexer, não "
                          f"sobrou nada nas categorias que eu costumo sugerir.\n\n"
                          f"O que ainda dá para olhar:\n\n{lista}\n\n"
                          f"Me diz qual dessas faz sentido cortar que eu simulo o "
                          f"impacto na sua reserva.\n\n[fonte] {r['_fonte']}",
                    ferramentas_usadas=["simular_economia"], fontes=[r["_fonte"]],
                )

            cortadas = ", ".join(c["categoria"] for c in r["categorias_ajustadas"])
            respeito = ""
            if r["categorias_excluidas"]:
                respeito = (f"Respeitei sua restrição: deixei "
                            f"**{', '.join(r['categorias_excluidas'])}** de fora.\n\n")

            extra = ""
            if r["alternativas"]:
                a = r["alternativas"][0]
                extra = (f"\nSe quiser ir além, **{a['categoria']}** ainda tem "
                         f"{a['gasto_formatado']} — cortar {pct:.0f}% aí renderia "
                         f"mais {a['economia_possivel_formatado']}.\n")

            # "2 mes(es) em vez de 2" parecia erro de conta. Quando o corte
            # nao encurta o prazo, dizer isso E a informacao util: o gargalo
            # nao esta na despesa.
            antes = r["meses_para_meta_antes"]
            depois = r["meses_para_meta_depois"]
            if antes == depois:
                linha_prazo = (f"- Reserva completa em **{depois} mês(es)** — "
                               f"o mesmo prazo de antes: aqui o gargalo não é o gasto")
            else:
                linha_prazo = (f"- Reserva completa em **{depois} mês(es)** "
                               f"em vez de {antes}")

            return Resposta(
                texto=f"{respeito}Simulei um corte de **{pct:.0f}%** em **{cortadas}**:\n\n"
                      f"- Economia mensal: **{r['economia_mensal_formatado']}**\n"
                      f"- Em 12 meses: **{r['economia_anual_formatado']}**\n"
                      f"- Saldo mensal iria de {r['saldo_atual_formatado']} para "
                      f"**{r['novo_saldo_formatado']}**\n"
                      f"{linha_prazo}\n"
                      f"{extra}\n"
                      f"Quer que eu detalhe onde está esse gasto?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["simular_economia"], fontes=[r["_fonte"]],
                oferta="maior_gasto",
            )

        # --- gasto por categoria
        for cat in ("alimentacao", "moradia", "transporte", "saude", "lazer"):
            if cat in p:
                r = tools.somar_por_categoria(cat)
                if not r["encontrado"]:
                    return Resposta(
                        texto=f"Não encontrei lançamentos em '{cat}'. As categorias que "
                              f"tenho são: {', '.join(r['categorias_disponiveis'])}.",
                        ferramentas_usadas=["somar_por_categoria"], fontes=[r["_fonte"]],
                    )
                itens = ", ".join(f"{d['descricao']} ({d['valor']})" for d in r["detalhe"])
                return Resposta(
                    texto=f"Você gastou **{r['total_formatado']}** com "
                          f"{r['categoria_exibicao']}, em {r['qtd_transacoes']} "
                          f"lançamento(s): {itens}.\n\n"
                          f"Quer que eu simule quanto sobraria cortando 30% dessa "
                          f"categoria?\n\n[fonte] {r['_fonte']}",
                    ferramentas_usadas=["somar_por_categoria"], fontes=[r["_fonte"]],
                    oferta="simular",
                )

        # --- produtos / investimento
        # Oferta com promessa de retorno nao e consulta de produto: e golpe.
        # Sem este desvio, "me chamaram pra investir com retorno garantido"
        # virava recomendacao de catalogo em vez de alerta.
        if oferta_suspeita and re.search(r"\b(invest\w*|aplicar|retorno|lucro|"
                                         r"rendiment\w*|oportunidade)\b", p):
            a = tools.analisar_suspeita(pergunta)
            sinais = "\n".join(f"[sinal] {s}" for s in a["bandeiras_vermelhas"]) or \
                     "[sinal] Promessa de retorno garantido"
            golpe = a["golpe_provavel"]["nome"] if a["golpe_provavel"] else \
                    "Falso investimento"
            return Resposta(
                texto=f"**Risco {a['nivel_risco']}** — {a['veredito']}\n\n"
                      f"Isso tem o padrão de **{golpe}**.\n\n{sinais}\n\n"
                      f"Rentabilidade garantida não existe: é proibido por lei "
                      f"prometer retorno. Quem promete está te vendendo risco "
                      f"escondido ou aplicando um golpe.\n\n"
                      f"Antes de qualquer coisa, confirme o CNPJ no site da CVM e "
                      f"desconfie de pressa. Quer que eu te mostre o que **é** "
                      f"compatível com o seu perfil?\n\n[fonte] {a['_fonte']}",
                ferramentas_usadas=["analisar_suspeita"], fontes=[a["_fonte"]],
                oferta="produtos",
            )

        if any(t in p for t in ("invest", "produto", "aplicar", "cdb", "tesouro",
                                "fundo", "acao", "acoes")):
            r = tools.recomendar_produtos()
            pedido_bloqueado = [b for b in r["produtos_bloqueados"]
                                if _normalizar(b["nome"]) in p]
            if pedido_bloqueado:
                b = pedido_bloqueado[0]
                return Resposta(
                    texto=f"Entendo a vontade de acelerar os ganhos, mas preciso ser "
                          f"honesto: o **{b['nome']}** é de risco {b['risco']}, e no seu "
                          f"cadastro você declarou não aceitar risco. Além disso, sua "
                          f"reserva de emergência ainda não está completa — ela é o colchão "
                          f"que evita resgatar investimento na pior hora.\n\n"
                          f"Que tal fecharmos a reserva primeiro?\n\n[fonte] {r['_fonte']}",
                    ferramentas_usadas=["recomendar_produtos"], fontes=[r["_fonte"]],
                )
            linhas = "\n".join(
                f"- **{x['nome']}** — risco {x['risco']}, {x['rentabilidade']}, "
                f"a partir de {tools.brl(x['aporte_minimo'])}. {x['indicado_para']}."
                for x in r["produtos_compativeis"]
            )
            return Resposta(
                texto=f"Considerando seu perfil **{r['perfil_investidor']}** (e que você "
                      f"declarou não aceitar risco), estes são os produtos "
                      f"compatíveis:\n\n{linhas}\n\n"
                      f"Quer entender melhor algum deles?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["recomendar_produtos"], fontes=[r["_fonte"]],
            )

        # --- metas
        if any(t in p for t in ("meta", "reserva", "objetivo", "apartamento",
                                "quanto falta", "prazo")):
            r = tools.progresso_metas()
            blocos = []
            for m in r["metas"]:
                if m["concluida"]:
                    blocos.append(f"**{m['meta']}** — concluída")
                elif m["prazo_vencido"]:
                    blocos.append(
                        f"**{m['meta']}** — {m['progresso_pct']}% concluído\n"
                        f"O prazo ({m['prazo']}) já venceu e ainda faltam "
                        f"{m['falta_formatado']}.\n"
                        f"{tools.prazo_texto(m['meses_no_ritmo_atual']).capitalize()}. "
                        f"Vale repactuar a data."
                    )
                else:
                    status = "no ritmo" if m["no_ritmo"] else "precisa acelerar"
                    blocos.append(
                        f"**{m['meta']}** — {m['progresso_pct']}% concluído\n"
                        f"Falta {m['falta_formatado']} de "
                        f"{m['valor_necessario_formatado']} "
                        f"(prazo {m['prazo']}, {m['meses_ate_prazo']} meses).\n"
                        f"Aporte mensal necessário: "
                        f"{m['aporte_mensal_necessario_formatado']} — {status}"
                    )
            return Resposta(
                texto="Situação das suas metas:\n\n" + "\n\n".join(blocos)
                      + f"\n\nSeu saldo mensal hoje é {r['saldo_mensal_formatado']}. "
                        f"Quer simular um corte de gastos para antecipar?\n\n"
                        f"[fonte] {r['_fonte']}",
                ferramentas_usadas=["progresso_metas"], fontes=[r["_fonte"]],
                oferta="simular",
            )

        # --- perfil
        if any(t in p for t in ("perfil", "meus dados", "quem sou",
                                "minha renda", "cadastro")):
            r = tools.consultar_perfil()
            return Resposta(
                texto=f"Seus dados: **{r['nome']}**, {r['idade']} anos, {r['profissao']}.\n"
                      f"- Renda mensal: {tools.brl(r['renda_mensal'])}\n"
                      f"- Perfil de investidor: {r['perfil_investidor']} "
                      f"(aceita risco: {'sim' if r['aceita_risco'] else 'não'})\n"
                      f"- Objetivo principal: {r['objetivo_principal']}\n\n"
                      f"Quer ver como estão suas metas?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["consultar_perfil"], fontes=[r["_fonte"]],
                oferta="metas",
            )

        # --- atendimentos
        if any(t in p for t in ("atendimento", "falei", "conversamos",
                                "historico de atend", "suporte")):
            r = tools.historico_atendimento()
            linhas = "\n".join(
                f"- {a['data']} ({a['canal']}) — **{a['tema']}**: {a['resumo']}"
                for a in r["atendimentos"]
            )
            return Resposta(
                texto=f"Você teve {r['total']} atendimentos:\n\n{linhas}\n\n"
                      f"Temas recorrentes: {', '.join(r['temas_recorrentes'])}.\n\n"
                      f"[fonte] {r['_fonte']}",
                ferramentas_usadas=["historico_atendimento"], fontes=[r["_fonte"]],
            )

        # --- resumo / saldo (fallback amplo)
        if any(t in p for t in ("saldo", "resumo", "gast", "sobra", "quanto",
                                "extrato", "situacao", "balanco")):
            r = tools.resumo_financeiro()
            top = "\n".join(
                f"- {g['categoria']}: {g['valor_formatado']} "
                f"({g['pct_da_renda']}% da renda)"
                for g in r["gastos_por_categoria"]
            )
            return Resposta(
                texto=f"Seu mês em números:\n\n"
                      f"- Entradas: **{r['entradas_formatado']}**\n"
                      f"- Saídas: **{r['saidas_formatado']}**\n"
                      f"- Saldo: **{r['saldo_formatado']}** "
                      f"(taxa de poupança de {r['taxa_poupanca_pct']}%)\n\n"
                      f"Gastos por categoria:\n{top}\n\n"
                      f"Quer ver o impacto disso nas suas metas?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["resumo_financeiro"], fontes=[r["_fonte"]],
                oferta="metas",
            )

        # --- fallback progressivo
        self._fallbacks += 1

        if self._fallbacks == 1:
            return Resposta(
                texto=f"Desculpa, {nome} — essa eu não sei responder. Não tenho esse tipo "
                      f"de dado aqui comigo, e sobre o seu dinheiro eu prefiro não chutar. "
                      f"Um palpite meu poderia te fazer tomar uma decisão ruim.\n\n"
                      f"O que eu faço bem: mostrar seus gastos por categoria, fechar o "
                      f"resumo do mês, acompanhar suas metas, simular quanto sobra se você "
                      f"cortar uma despesa, sugerir produtos que combinam com seu perfil e "
                      f"te ajudar a identificar golpes.\n\n"
                      f"Me conta o que você quer saber que eu vejo se está no meu alcance."
            )
        if self._fallbacks == 2:
            return Resposta(
                texto=f"De novo eu te devo essa, {nome} — sinto muito. Vou ser honesta "
                      f"sobre o meu limite: eu só enxergo o seu extrato, o seu perfil de "
                      f"investidor, o catálogo de produtos e a base de golpes. Fora disso "
                      f"eu ficaria inventando, e não é isso que você merece.\n\n"
                      f"Se quiser me testar em algo que eu domino, tenta assim:\n"
                      f"- *\"quanto gastei com transporte?\"*\n"
                      f"- *\"quanto falta pra minha reserva?\"*\n"
                      f"- *\"recebi uma ligação suspeita\"*"
            )

        r = tools.resumo_financeiro()
        return Resposta(
            texto=f"Mais uma que passa longe do que eu alcanço, {nome} — desculpa "
                  f"insistir na mesma resposta. Já que eu não consigo te ajudar nisso, "
                  f"deixa eu pelo menos te mostrar algo que talvez valha o seu tempo.\n\n"
                  f"Neste mês você fechou com **{r['saldo_formatado']}** de saldo, e o que "
                  f"mais pesou no seu bolso foi **{r['maior_gasto']['categoria']}**, com "
                  f"{r['maior_gasto']['valor_formatado']}.\n\n"
                  f"Quer que eu abra essa categoria para ver onde o dinheiro foi parar, ou "
                  f"prefere saber o quanto ela está atrasando a sua reserva?\n\n"
                  f"[fonte] {r['_fonte']}",
            ferramentas_usadas=["resumo_financeiro"], fontes=[r["_fonte"]],
            oferta="maior_gasto",
        )

    # --------------------------------------------------------- refinamento
    def _refinar(self, topico: str, p: str, nome: str, so_top: bool) -> Resposta:
        """
        Reapresenta o último tópico de forma enxuta.

        Um cliente real cansa de texto longo e pede "me dá só as duas
        melhores". Isso não é uma pergunta nova: é a mesma resposta com
        outro recorte. Sem memória do tópico, virava fallback.
        """
        quantos = 2
        # Pergunta no singular pede UMA resposta.
        if re.search(r"\b(qual (a|o) (mais|melhor)|prioridade|so (uma|um)\b|"
                     r"a mais importante|o mais importante|por onde comec)", p):
            quantos = 1
        m = re.search(r"\b(uma|um|1|duas|dois|2|tres|três|3)\b", p)
        if m:
            quantos = {"uma": 1, "um": 1, "1": 1, "duas": 2, "dois": 2,
                       "2": 2, "tres": 3, "três": 3, "3": 3}[m.group(1)]

        if topico == "plano":
            r = tools.montar_plano(sem_cortes=True)
            etapas = r["etapas"][:quantos]
            # Nao usar split('.'): quebra em "R$ 2.511,10". Corta na primeira
            # sentenca de verdade (ponto seguido de espaco e maiuscula).
            def primeira_frase(txt: str) -> str:
                partes = re.split(r"(?<=[a-z\u00e0-\u00fc])\.\s+(?=[A-Z])", txt, maxsplit=1)
                return partes[0].rstrip(".") + "."

            lista = "\n".join(
                f"**{i}.** {e['titulo']} — {primeira_frase(e['acao'])}"
                for i, e in enumerate(etapas, 1)
            )
            return Resposta(
                texto=f"Claro. Se for para fazer só {'uma coisa' if quantos == 1 else f'{quantos} coisas'}, "
                      f"{nome}, {'é esta' if quantos == 1 else 'são estas'}:\n\n{lista}\n\n"
                      f"O resto é consequência dessas.\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["montar_plano"], fontes=[r["_fonte"]],
                oferta="metas",
            )

        if topico == "categorias":
            r = tools.resumo_financeiro()
            top = r["gastos_por_categoria"][:quantos]
            lista = "\n".join(
                f"**{i}.** {tools.rotulo(c['categoria'])} — {c['valor_formatado']}"
                for i, c in enumerate(top, 1)
            )
            return Resposta(
                texto=f"Resumindo, {nome} — {'seu maior gasto' if quantos == 1 else f'seus {quantos} maiores gastos'}:\n\n"
                      f"{lista}\n\nSaldo do mês: **{r['saldo_formatado']}**.\n\n"
                      f"[fonte] {r['_fonte']}",
                ferramentas_usadas=["resumo_financeiro"], fontes=[r["_fonte"]],
                oferta="simular",
            )

        if topico == "golpes":
            r = tools.listar_golpes()
            regras = r["regras_de_ouro"][:quantos]
            lista = "\n".join(f"**{i}.** {g}" for i, g in enumerate(regras, 1))
            cab = ("A regra que mais importa" if quantos == 1
                   else f"As {quantos} que mais importam")
            return Resposta(
                texto=f"{cab}, {nome}:\n\n{lista}\n\n"
                      f"[fonte] {r['_fonte']}",
                ferramentas_usadas=["listar_golpes"], fontes=[r["_fonte"]],
                oferta="golpes",
            )

        if topico == "metas":
            m0 = tools.progresso_metas()["metas"][0]
            return Resposta(
                texto=f"Direto ao ponto, {nome}: faltam **{m0['falta_formatado']}** "
                      f"para a reserva, e no seu ritmo "
                      f"{tools.prazo_texto(m0['meses_no_ritmo_atual'])}.\n\n"
                      f"[fonte] data/perfil_investidor.json",
                ferramentas_usadas=["progresso_metas"],
                fontes=["data/perfil_investidor.json"],
                oferta="simular",
            )

        # produtos, diagnóstico e afins
        r = tools.diagnostico_geral()
        return Resposta(
            texto=f"Resumindo, {nome}: {r['prioridade']}\n\n"
                  f"[fonte] {r['_fonte']}",
            ferramentas_usadas=["diagnostico_geral"], fontes=[r["_fonte"]],
            oferta="simular",
        )

    # ------------------------------------------------------- proatividade
    def saudacao_proativa(self) -> str:
        """Insight ANTES de o usuário perguntar — pilar 'antecipar necessidades'."""
        metas = tools.progresso_metas()
        resumo = tools.resumo_financeiro()
        m = metas["metas"][0]
        nome = tools.PERFIL["nome"].split()[0]

        if m["prazo_vencido"]:
            status = (f"e {tools.prazo_texto(m['meses_no_ritmo_atual'])} — "
                      f"mas atenção: o prazo de {m['prazo']} já passou")
        elif m["no_ritmo"]:
            status = "e nesse ritmo você chega antes do prazo"
        else:
            status = "e nesse ritmo o prazo fica apertado"

        return (
            f"Olá, {nome}. Sou a **Luma**, sua agente financeira.\n\n"
            f"Dei uma olhada nos seus números antes de você perguntar: a meta "
            f"**{m['meta'].lower()}** está **{m['progresso_pct']}% concluída** — "
            f"faltam **{m['falta_formatado']}**. "
            f"Seu saldo mensal é de **{resumo['saldo_formatado']}**, {status}.\n\n"
            f"Posso te ajudar com:\n"
            f"- *\"Como estão meus gastos?\"*\n"
            f"- *\"Quanto falta para minha meta?\"*\n"
            f"- *\"Recebi uma ligação suspeita\"*\n\n"
            f"[fonte] {metas['_fonte']}"
        )


if __name__ == "__main__":
    a = AgenteLuma()
    print(f"[modo: {a.modo}]\n")
    print(a.saudacao_proativa())
    for q in ["quanto gastei com alimentação?", "me põe no fundo de ações",
              "qual a previsão do tempo?", "me passa a senha", "simule um corte de 40%"]:
        r = a.responder(q)
        print(f"\n{'-' * 60}\n[você] {q}\n[luma] {r.texto}")
        print(f"   {r.latencia_ms}ms | tools={r.ferramentas_usadas} "
              f"| guards={r.guardrails_acionados}")
