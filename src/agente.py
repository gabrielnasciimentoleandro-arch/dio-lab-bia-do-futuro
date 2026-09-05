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
        "description": "Simula cortar uma porcentagem dos gastos flexíveis.",
        "parameters": {
            "type": "object",
            "properties": {"corte_pct": {"type": "number", "description": "Padrão 30."}},
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
    {
        "name": "higiene_digital",
        "description": "Portas de entrada de malware no celular e checklist mensal de segurança.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "checar_infeccao",
        "description": "Cruza sintomas do celular com sinais de comprometimento por malware.",
        "parameters": {
            "type": "object",
            "properties": {"relato": {"type": "string"}},
            "required": ["relato"],
        },
    },
]


class AgenteLuma:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.modo = "demo"
        self.client = None
        self._fallbacks = 0

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

        if self.modo == "gemini":
            r = self._responder_gemini(pergunta)
        else:
            r = self._responder_demo(pergunta)

        r.texto, extras = _validar_saida(r.texto, "recomendar_produtos" in r.ferramentas_usadas)
        r.guardrails_acionados += extras
        r.latencia_ms = int((time.perf_counter() - inicio) * 1000)
        r.modo = self.modo
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
                      f"Quer que eu já deixe uma sugestão de próximo passo para a sua reserva?"
            )

        # ------------------------------------------------------- fora de escopo
        fora_escopo = ("tempo", "clima", "chuva", "futebol", "jogo", "receita de",
                       "politica", "presidente", "piada")
        if any(t in p for t in fora_escopo) and not any(
            t in p for t in ("gast", "invest", "meta", "reserva", "saldo", "golpe")
        ):
            return Resposta(
                texto=f"Essa eu não sei mesmo, {nome} — desculpa. Cuido só das suas "
                      f"finanças, e fora desse assunto eu não seria de muita ajuda.\n\n"
                      f"Mas se quiser, posso te mostrar como está a sua reserva de "
                      f"emergência. Topa?"
            )

        # ======================================================== ANTIFRAUDE
        # --- suspeita de celular infectado (vetor técnico)
        # Usamos proximidade, e nao substring colada: "celular esta quente" e
        # "celular ta muito lento" tem palavras no meio e falhavam com
        # gatilhos do tipo "celular quente".
        aparelho = r"(celular|telefone|aparelho|smartphone|cel)"
        sintoma = (r"(lent[oa]|quente|esquenta\w*|trava\w*|devagar|estranh[oa]|"
                   r"infectad[oa]|virus|lerd[oa]|pesad[oa]|reinicia\w*|desliga\w* sozinho)")
        infeccao_regex = (
            rf"\b{aparelho}\b(?:\W+\w+){{0,4}}?\W+\b{sintoma}\b"
            rf"|\b{sintoma}\b(?:\W+\w+){{0,4}}?\W+\b{aparelho}\b"
        )
        # Pergunta educativa ("como o virus entra?", "posso instalar apk?") NAO e
        # relato de sintoma: deve cair na higiene digital, logo abaixo.
        educativo = re.search(
            r"^\s*(como|posso|devo|vale a pena|e seguro|é seguro|o que (e|é)|qual|"
            r"quais|por que|porque|existe)\b", p
        ) or any(t in p for t in ("como evitar", "como prevenir", "como proteger",
                                  "fora da loja", "higiene digital"))

        if not educativo and (re.search(infeccao_regex, p) or any(t in p for t in (
                "bateria acabando", "bateria durando", "bateria descarregando",
                "aparecendo anuncio", "anuncios estranhos", "pop up", "popup",
                "app que nao instalei", "aplicativo estranho", "consumo de dados",
                "app desconhecido", "virus no celular", "malware", "spyware",
                "acesso remoto", "anydesk", "teamviewer",
                "instalei um apk", "baixei um apk"))):
            r = tools.checar_infeccao(pergunta)

            if r["qtd_sinais"]:
                sinais = "\n".join(f"- {s}" for s in r["sinais_encontrados"])
                acoes = "\n".join(f"{i}. {a}" for i, a in enumerate(r["acao_imediata"], 1))
                corpo = (f"**Risco {r['nivel_risco']}** — {r['veredito']}\n\n"
                         f"**O que você descreveu bate com:**\n{sinais}\n\n"
                         f"Isso importa para o seu dinheiro: um celular comprometido permite "
                         f"que o golpista veja sua senha ou movimente a conta **sem nenhuma "
                         f"ligação** — o dinheiro some enquanto você dorme.\n\n"
                         f"**Faça agora, nesta ordem:**\n{acoes}\n\n"
                         f"**Importante:** não troque a senha antes de limpar o aparelho. "
                         f"Se ele estiver infectado, a senha nova é capturada na hora.")
            else:
                lista = "\n".join(f"- {s}" for s in r["todos_os_sinais"])
                corpo = (f"**Risco {r['nivel_risco']}** — {r['veredito']}\n\n"
                         f"Os sinais clássicos de celular comprometido são:\n{lista}\n\n"
                         f"Se algum desses aparecer, me avise.")

            return Resposta(
                texto=f"{corpo}\n\nQuer ver as portas de entrada mais comuns de vírus "
                      f"no celular?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["checar_infeccao"], fontes=[r["_fonte"]],
            )

        # --- higiene digital: como o malware entra
        if any(t in p for t in ("como o virus entra", "como pega virus", "como me infecto",
                                "higiene digital", "proteger meu celular",
                                "seguranca do celular", "porta de entrada", "banner",
                                "apk", "fora da loja", "wifi publico", "wi-fi publico",
                                "permissao de acessibilidade", "checklist",
                                "como evitar virus", "instalar app")):
            r = tools.higiene_digital()
            vetores = "\n\n".join(
                f"**{i}. {v['vetor']}**\n*Exemplo:* {v['exemplo']}\n{v['defesa']}"
                for i, v in enumerate(r["portas_de_entrada"], 1)
            )
            check = "\n".join(f"- [ ] {c}" for c in r["checklist_mensal"])
            return Resposta(
                texto=f"Boa — prevenir a infecção é mais eficaz do que remediar o roubo.\n\n"
                      f"Antes do golpe existir, o vírus precisa entrar. Estas são as "
                      f"**{r['total_vetores']} portas de entrada** mais usadas:\n\n{vetores}\n\n"
                      f"---\n\n**Checklist mensal de segurança:**\n{check}\n\n"
                      f"Se o seu celular já anda estranho, me descreva o que está "
                      f"acontecendo que eu analiso.\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["higiene_digital"], fontes=[r["_fonte"]],
            )

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
                )

        # --- produtos / investimento
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
                        f"No seu ritmo atual, dá para fechar em "
                        f"{m['meses_no_ritmo_atual']} mês(es). Vale repactuar a data."
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
            )

        # --- simulação
        if any(t in p for t in ("simul", "cortar", "economiz", "reduzir",
                                "antecipar", "sobraria")):
            m = re.search(r"(\d{1,2})\s*%", p)
            r = tools.simular_economia(float(m.group(1)) if m else 30.0)
            return Resposta(
                texto=f"Simulei um corte de **{r['corte_pct']:.0f}%** nos gastos flexíveis "
                      f"(alimentação e lazer):\n\n"
                      f"- Economia mensal: **{r['economia_mensal_formatado']}**\n"
                      f"- Em 12 meses: **{r['economia_anual_formatado']}**\n"
                      f"- Saldo mensal iria de {r['saldo_atual_formatado']} para "
                      f"**{r['novo_saldo_formatado']}**\n"
                      f"- Reserva completa em **{r['meses_para_meta_depois']} mês(es)** "
                      f"em vez de {r['meses_para_meta_antes']}\n\n"
                      f"Quer que eu detalhe onde está esse gasto?\n\n[fonte] {r['_fonte']}",
                ferramentas_usadas=["simular_economia"], fontes=[r["_fonte"]],
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
        )

    # ------------------------------------------------------- proatividade
    def saudacao_proativa(self) -> str:
        """Insight ANTES de o usuário perguntar — pilar 'antecipar necessidades'."""
        metas = tools.progresso_metas()
        resumo = tools.resumo_financeiro()
        m = metas["metas"][0]
        nome = tools.PERFIL["nome"].split()[0]

        if m["prazo_vencido"]:
            status = (f"o que dá para fechar em **{m['meses_no_ritmo_atual']} mês(es)** — "
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
