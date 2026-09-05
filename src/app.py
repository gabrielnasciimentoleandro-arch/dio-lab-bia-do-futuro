"""
app.py — Interface web da agente Luma (Streamlit).

Design:
  * Tema claro e escuro, alternável, com contraste AA em ambos.
  * Zero emoji: todos os ícones são SVG inline (nítidos e consistentes).
  * Escala tipográfica fixa, sem tamanhos aleatórios.

Rodar:
    streamlit run src/app.py
"""

from __future__ import annotations

import base64
import os
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ferramentas as tools  # noqa: E402
from agente import AgenteLuma  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

st.set_page_config(
    page_title="Luma — Agente Financeira",
    page_icon=str(RAIZ / "assets" / "luma-avatar.png"),
    layout="centered",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------ helpers
def data_uri_png(caminho: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(caminho.read_bytes()).decode("ascii")


def data_uri_svg(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")


LOGO = RAIZ / "assets" / "luma-avatar.png"
AVATAR_LUMA = data_uri_png(LOGO) if LOGO.exists() else data_uri_svg(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<circle cx="32" cy="32" r="32" fill="#0F766E"/></svg>'
)


def avatar_user(escuro: bool) -> str:
    bg = "#334155" if escuro else "#E2E8F0"
    fg = "#94A3B8" if escuro else "#94A3B8"
    return data_uri_svg(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<circle cx="32" cy="32" r="32" fill="{bg}"/>'
        f'<circle cx="32" cy="25" r="10" fill="{fg}"/>'
        f'<path d="M12 58c0-11 9-18 20-18s20 7 20 18z" fill="{fg}"/></svg>'
    )


def ico(path_d: str, cor: str, tamanho: int = 15) -> str:
    """Ícone SVG inline com traço — substitui emoji."""
    return (
        f'<svg width="{tamanho}" height="{tamanho}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:-2px;flex-shrink:0">{path_d}</svg>'
    )


# traços (Feather-like)
P_DOC = '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>'
P_ALERT = '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
P_SHIELD = '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
P_FLAG = '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>'
P_USER = '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'
P_CHART = '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>'
P_TARGET = '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'
P_PIE = '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>'
P_KEY = '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3"/>'
P_BOOK = '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
P_CLOCK = '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
P_TOOL = '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
P_SUN = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
P_MOON = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'


# ------------------------------------------------------------------- estado
if "escuro" not in st.session_state:
    st.session_state.escuro = False
ESCURO = st.session_state.escuro

# ------------------------------------------------------------------- paleta
if ESCURO:
    C = dict(
        bg="#0B1120", bg2="#111A2E", card="#16213A", borda="#26334D",
        txt="#E8EDF7", txt2="#A8B6CE", txt3="#78889F",
        marca="#38BDF8", ok="#34D399", alerta="#FBBF24", perigo="#F87171",
        codbg="#1E293B", codfg="#7DD3FC", trilha="#1E293B",
        sombra="0 1px 3px rgba(0,0,0,.5)",
    )
else:
    C = dict(
        bg="#FFFFFF", bg2="#F7F9FC", card="#FFFFFF", borda="#E3E9F2",
        txt="#111827", txt2="#4B5563", txt3="#6B7280",
        marca="#0369A1", ok="#047857", alerta="#B45309", perigo="#B91C1C",
        codbg="#F1F5F9", codfg="#0F766E", trilha="#EDF1F7",
        sombra="0 1px 2px rgba(15,23,42,.06)",
    )

PALETA_DONUT = (["#38BDF8", "#34D399", "#FBBF24", "#A78BFA", "#F472B6", "#94A3B8"]
                if ESCURO else
                ["#0369A1", "#047857", "#B45309", "#6D28D9", "#BE185D", "#475569"])

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  :root {{
    --bg:{C['bg']}; --bg2:{C['bg2']}; --card:{C['card']}; --borda:{C['borda']};
    --txt:{C['txt']}; --txt2:{C['txt2']}; --txt3:{C['txt3']};
    --marca:{C['marca']}; --ok:{C['ok']}; --alerta:{C['alerta']}; --perigo:{C['perigo']};
  }}

  /* Sobrescreve o tema do proprio Streamlit, e nao so os nossos blocos.
     Sem isto, containers nativos (rodape do chat_input, scrollbar, spinner,
     tooltips) continuam claros quando o modo escuro esta ativo. */
  :root, .stApp, [data-testid="stAppViewContainer"] {{
      --background-color: var(--bg);
      --secondary-background-color: var(--bg2);
      --text-color: var(--txt);
      --primary-color: var(--marca);
      --border-color: var(--borda);
      color-scheme: {'dark' if ESCURO else 'light'};
  }}

  .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
  [data-testid="stBottom"], [data-testid="stBottomBlockContainer"],
  [data-testid="stBottom"] > div, .stAppViewBlockContainer {{
      background: var(--bg) !important;
  }}
  [data-testid="stHeader"] {{ background: transparent !important; }}
  html, body, [class*="css"], .stMarkdown, .stChatMessage, input, textarea, button {{
      font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
      -webkit-font-smoothing: antialiased;
  }}
  /* Escondemos a barra de ferramentas, MAS NAO o header inteiro: o botao
     que reabre a sidebar mora dentro do header. Ocultar o header deixava
     o usuario sem como trazer o painel de volta depois de fecha-lo. */
  #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
  [data-testid="stStatusWidget"] {{ display:none !important; }}
  [data-testid="stHeader"] {{
      background:transparent !important; height:0; visibility:visible;
  }}
  /* seta de reabrir a sidebar: sempre visivel e com contraste */
  [data-testid="stSidebarCollapsedControl"] {{
      visibility:visible !important; opacity:1 !important;
      top:.6rem !important; left:.6rem !important; z-index:999;
  }}
  [data-testid="stSidebarCollapsedControl"] button,
  [data-testid="stSidebarCollapseButton"] button {{
      background:var(--card) !important; color:var(--txt2) !important;
      border:1px solid var(--borda) !important; border-radius:9px !important;
      box-shadow:{C['sombra']} !important;
  }}
  [data-testid="stSidebarCollapsedControl"] button:hover,
  [data-testid="stSidebarCollapseButton"] button:hover {{
      color:var(--marca) !important; border-color:var(--marca) !important;
  }}
  [data-testid="stSidebarCollapsedControl"] svg,
  [data-testid="stSidebarCollapseButton"] svg {{ color:currentColor !important; }}
  .block-container {{ padding-top: 2rem; padding-bottom: 5rem; max-width: 800px; }}

  /* ---------- escala tipográfica (fixa, sem tamanhos avulsos) ---------- */
  /* t1 1.55rem · t2 1.0rem · corpo .945rem · aux .8rem · micro .72rem   */

  .luma-head {{ display:flex; align-items:center; gap:.8rem; margin-bottom:.3rem; }}
  .luma-mark {{
      width:44px; height:44px; border-radius:12px; flex-shrink:0;
      object-fit:contain; background:transparent;
  }}
  .luma-title {{
      font-size:1.55rem; font-weight:700; letter-spacing:-.021em;
      color:var(--txt); line-height:1.15; margin:0;
  }}
  .luma-sub {{ font-size:.8rem; color:var(--txt3); margin:.15rem 0 0; font-weight:500; }}

  .badge {{
      display:inline-flex; align-items:center; gap:.42rem;
      font-size:.72rem; font-weight:600; padding:.32rem .72rem;
      border-radius:999px; margin:.85rem 0 .3rem; letter-spacing:.005em;
  }}
  .badge-live {{
      background:{'#064E3B' if ESCURO else '#ECFDF5'};
      color:{'#6EE7B7' if ESCURO else '#065F46'};
      border:1px solid {'#065F46' if ESCURO else '#A7F3D0'};
  }}
  .badge-demo {{
      background:{'#422006' if ESCURO else '#FFFBEB'};
      color:{'#FCD34D' if ESCURO else '#92400E'};
      border:1px solid {'#78350F' if ESCURO else '#FDE68A'};
  }}
  .dot {{ width:6px; height:6px; border-radius:50%; background:currentColor; }}

  /* ---------- chat ---------- */
  .stChatMessage {{
      background:var(--card) !important; border:1px solid var(--borda);
      border-radius:14px; padding:1rem 1.15rem; box-shadow:{C['sombra']};
  }}
  /* avatar do chat vinha com fundo claro fixo do Streamlit */
  .stChatMessage img[data-testid="stChatMessageAvatarCustom"],
  [data-testid="stChatMessageAvatarCustom"] {{
      background:transparent !important; border:none !important;
      box-shadow:none !important; border-radius:9px;
  }}
  .stChatMessage p, .stChatMessage li {{
      font-size:.945rem; line-height:1.68; color:var(--txt2); margin-bottom:.55rem;
  }}
  .stChatMessage p:last-child {{ margin-bottom:0; }}
  .stChatMessage strong {{ color:var(--txt); font-weight:650; }}
  .stChatMessage em {{ color:var(--txt3); }}
  .stChatMessage h1,.stChatMessage h2,.stChatMessage h3 {{
      font-size:1rem; color:var(--txt); font-weight:650; margin:.6rem 0 .3rem;
  }}
  .stChatMessage code {{
      background:{C['codbg']}; color:{C['codfg']};
      padding:.12rem .38rem; border-radius:5px; font-size:.86em;
  }}
  .stChatMessage hr {{ border-color:var(--borda); margin:.9rem 0; }}
  .stChatMessage ul {{ padding-left:1.15rem; margin:.35rem 0 .55rem; }}
  .stChatMessage ol {{ padding-left:1.3rem; margin:.35rem 0 .55rem; }}
  .stChatMessage [data-testid="stCaptionContainer"] p {{
      font-size:.72rem !important; color:var(--txt3) !important;
      margin-top:.6rem !important; letter-spacing:.008em;
  }}

  /* linhas de marcador (fonte, aviso, sinal) */
  .mk {{
      display:flex; align-items:flex-start; gap:.45rem;
      font-size:.775rem; line-height:1.5; margin-top:.7rem;
      padding-top:.6rem; border-top:1px solid var(--borda);
  }}
  .mk-fonte {{ color:var(--txt3); }}
  .mk-aviso {{ color:var(--alerta); border-top:none; padding-top:.15rem; }}
  .mk-sinal {{ color:var(--perigo); border-top:none; padding-top:.15rem; }}

  /* ---------- sidebar ---------- */
  section[data-testid="stSidebar"] {{
      background:var(--bg2); border-right:1px solid var(--borda);
  }}
  section[data-testid="stSidebar"] .block-container {{ padding-top:1.5rem; }}
  section[data-testid="stSidebar"] * {{ color:var(--txt2); }}

  .side-label {{
      display:flex; align-items:center; gap:.4rem;
      font-size:.685rem; font-weight:700; letter-spacing:.085em;
      text-transform:uppercase; color:var(--txt3);
      margin:1.35rem 0 .5rem;
  }}
  .card {{
      background:var(--card); border:1px solid var(--borda);
      border-radius:12px; padding:.85rem .95rem; margin-bottom:.5rem;
  }}
  .card-name {{ font-size:.945rem; font-weight:650; color:var(--txt); }}
  .card-meta {{ font-size:.775rem; color:var(--txt3); margin-top:.18rem; line-height:1.5; }}
  .card-meta b {{ color:var(--txt2); font-weight:600; }}

  .kpi-row {{ display:flex; gap:.5rem; margin-bottom:.5rem; }}
  .kpi {{
      flex:1; background:var(--card); border:1px solid var(--borda);
      border-radius:12px; padding:.68rem .78rem;
  }}
  .kpi-k {{
      font-size:.655rem; font-weight:700; letter-spacing:.07em;
      text-transform:uppercase; color:var(--txt3);
  }}
  .kpi-v {{
      font-size:1rem; font-weight:700; margin-top:.16rem;
      letter-spacing:-.012em; font-variant-numeric:tabular-nums;
  }}
  .v-in {{ color:var(--ok); }} .v-out {{ color:var(--perigo); }} .v-net {{ color:var(--txt); }}

  .pill {{
      display:inline-block; font-size:.7rem; font-weight:650;
      background:{'#064E3B' if ESCURO else '#ECFDF5'};
      color:{'#6EE7B7' if ESCURO else '#047857'};
      padding:.16rem .52rem; border-radius:999px; margin-top:.32rem;
  }}

  .bar-track {{
      height:8px; background:{C['trilha']}; border-radius:999px;
      overflow:hidden; margin:.5rem 0 .42rem;
  }}
  .bar-fill {{
      height:100%; border-radius:999px;
      background:linear-gradient(90deg, var(--ok), {'#10B981' if ESCURO else '#059669'});
  }}
  .bar-legend {{
      display:flex; justify-content:space-between;
      font-size:.755rem; color:var(--txt3);
  }}
  .bar-legend b {{ color:var(--txt); font-weight:650; }}

  .leg {{ margin-top:.65rem; }}
  .leg-row {{
      display:flex; align-items:center; gap:.42rem;
      font-size:.755rem; padding:.18rem 0;
  }}
  .leg-dot {{ width:8px; height:8px; border-radius:3px; flex-shrink:0; }}
  .leg-cat {{ color:var(--txt2); text-transform:capitalize; flex:1; }}
  .leg-val {{ color:var(--txt); font-weight:600; font-variant-numeric:tabular-nums; }}
  .leg-pct {{
      color:var(--txt3); font-size:.7rem; min-width:26px;
      text-align:right; font-variant-numeric:tabular-nums;
  }}

  .shield-ok {{ border-left:3px solid var(--ok); }}
  .shield-alert {{ border-left:3px solid var(--alerta); }}
  .shield-top {{ display:flex; align-items:center; gap:.42rem; margin-bottom:.15rem; }}
  .shield-t {{ font-size:.86rem; font-weight:650; color:var(--txt); }}

  .disclaimer {{
      font-size:.7rem; color:var(--txt3); line-height:1.55;
      border-top:1px solid var(--borda); padding-top:.8rem; margin-top:1.3rem;
  }}

  /* ---------- controles ---------- */
  .stTextInput input {{
      background:var(--card) !important; color:var(--txt) !important;
      border:1px solid var(--borda) !important; border-radius:10px !important;
      font-size:.85rem !important;
  }}
  .stTextInput input::placeholder {{ color:var(--txt3) !important; }}
  .stButton button {{
      background:var(--card); border:1px solid var(--borda); border-radius:10px;
      color:var(--txt2); font-weight:550; font-size:.83rem; transition:all .15s;
  }}
  .stButton button:hover {{
      border-color:var(--marca); color:var(--marca);
      background:{'#0C1A2E' if ESCURO else '#F0F9FF'};
  }}
  /* Campo de mensagem: o wrapper, o textarea e o botao de enviar. */
  [data-testid="stChatInput"], .stChatInput {{
      background:var(--card) !important;
      border:1px solid var(--borda) !important;
      border-radius:12px !important;
      box-shadow:{C['sombra']} !important;
  }}
  [data-testid="stChatInput"] textarea, .stChatInput textarea {{
      background:transparent !important; color:var(--txt) !important;
      font-size:.92rem !important; caret-color:var(--marca);
  }}
  /* placeholder tinha ficado com fundo proprio (bloco solido azul) */
  [data-testid="stChatInput"] textarea::placeholder {{
      color:var(--txt3) !important; background:transparent !important;
      opacity:1 !important;
  }}
  [data-testid="stChatInputSubmitButton"] {{
      background:transparent !important; color:var(--txt3) !important;
  }}
  [data-testid="stChatInputSubmitButton"]:hover {{ color:var(--marca) !important; }}
  [data-testid="stChatInputSubmitButton"]:disabled {{ opacity:.45; }}

  /* barra de rolagem acompanha o tema */
  ::-webkit-scrollbar {{ width:10px; height:10px; }}
  ::-webkit-scrollbar-track {{ background:var(--bg); }}
  ::-webkit-scrollbar-thumb {{
      background:var(--borda); border-radius:999px;
      border:2px solid var(--bg);
  }}
  ::-webkit-scrollbar-thumb:hover {{ background:var(--txt3); }}

  /* tooltip nativo (o "?" dos campos) */
  [data-testid="stTooltipContent"] {{
      background:var(--card) !important; color:var(--txt2) !important;
      border:1px solid var(--borda) !important; font-size:.78rem !important;
  }}
  .stSpinner > div {{ border-top-color:var(--marca) !important; }}
  hr {{ border-color:var(--borda); }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------- renderização de marcadores
def render_msg(texto: str) -> str:
    """Converte marcadores textuais em linhas com ícone SVG e escapa o cifrão."""
    linhas_extra = []

    def captura(padrao, classe, traco, cor):
        nonlocal texto
        for m in re.findall(padrao, texto):
            linhas_extra.append(
                f'<div class="mk {classe}">{ico(traco, cor, 14)}<span>{m.strip()}</span></div>'
            )
        texto = re.sub(padrao, "", texto)

    captura(r"\[fonte\][^\n]*", "mk-fonte", P_DOC, C["txt3"])
    captura(r"\[aviso\][^\n]*", "mk-aviso", P_ALERT, C["alerta"])
    captura(r"\[sinal\][^\n]*", "mk-sinal", P_FLAG, C["perigo"])

    corpo = texto.strip().replace("$", r"\$")
    return corpo, "".join(linhas_extra).replace("[fonte]", "").replace(
        "[aviso]", "").replace("[sinal]", "")


def escrever(texto: str) -> None:
    corpo, marcadores = render_msg(texto)
    st.markdown(corpo)
    if marcadores:
        st.markdown(marcadores, unsafe_allow_html=True)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    c1, c2 = st.columns([3, 1])
    c1.markdown(f'<div class="side-label">{ico(P_KEY, C["txt3"], 13)} Conexão</div>',
                unsafe_allow_html=True)
    if c2.button("Escuro" if not ESCURO else "Claro", use_container_width=True,
                 help="Alternar tema"):
        st.session_state.escuro = not ESCURO
        st.rerun()

    key_env = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    api_key = st.text_input(
        "Google AI Studio API Key", value=key_env or "", type="password",
        label_visibility="collapsed",
        placeholder="Opcional — cole sua Google AI Studio API Key",
        help="Opcional. Sem chave, a Luma responde pelo motor determinístico "
             "(as 15 ferramentas). A chave adiciona conversa livre com o Gemini, "
             "que continua obrigado a buscar todo número nessas mesmas ferramentas.",
    )

    if st.button("Reiniciar conversa", use_container_width=True):
        for k in ("agente", "mensagens", "_key"):
            st.session_state.pop(k, None)
        st.rerun()

    # cliente
    p = tools.PERFIL
    st.markdown(f'<div class="side-label">{ico(P_USER, C["txt3"], 13)} Cliente</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="card"><div class="card-name">{p["nome"]}</div>'
        f'<div class="card-meta">{p["idade"]} anos · {p["profissao"]}</div>'
        f'<div class="card-meta">Perfil {p["perfil_investidor"]} · '
        f'{"aceita risco" if p["aceita_risco"] else "avesso a risco"}</div></div>',
        unsafe_allow_html=True,
    )

    # mês
    r = tools.resumo_financeiro()
    st.markdown(f'<div class="side-label">{ico(P_CHART, C["txt3"], 13)} Mês atual</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="kpi-row">'
        f'<div class="kpi"><div class="kpi-k">Entradas</div>'
        f'<div class="kpi-v v-in">{r["entradas_formatado"]}</div></div>'
        f'<div class="kpi"><div class="kpi-k">Saídas</div>'
        f'<div class="kpi-v v-out">{r["saidas_formatado"]}</div></div></div>'
        f'<div class="card"><div class="kpi-k">Saldo</div>'
        f'<div class="kpi-v v-net">{r["saldo_formatado"]}</div>'
        f'<span class="pill">{r["taxa_poupanca_pct"]}% poupado</span></div>',
        unsafe_allow_html=True,
    )

    # donut
    st.markdown(f'<div class="side-label">{ico(P_PIE, C["txt3"], 13)} Gastos por categoria</div>',
                unsafe_allow_html=True)
    cats = r["gastos_por_categoria"]
    total = sum(c["valor"] for c in cats) or 1
    segs, off = [], 25.0
    for i, c in enumerate(cats):
        pct = c["valor"] / total * 100
        segs.append(
            f'<circle cx="21" cy="21" r="15.9155" fill="transparent" '
            f'stroke="{PALETA_DONUT[i % len(PALETA_DONUT)]}" stroke-width="5.5" '
            f'stroke-dasharray="{pct:.2f} {100 - pct:.2f}" stroke-dashoffset="{off:.2f}"/>'
        )
        off -= pct
    donut = (
        f'<svg viewBox="0 0 42 42" style="width:108px;height:108px;display:block;margin:0 auto">'
        f'<circle cx="21" cy="21" r="15.9155" fill="transparent" stroke="{C["trilha"]}" '
        f'stroke-width="5.5"/>{"".join(segs)}'
        f'<text x="21" y="20.4" text-anchor="middle" font-size="4.4" font-weight="700" '
        f'fill="{C["txt"]}" font-family="Inter">'
        f'{r["saidas_formatado"].replace("R$ ", "")}</text>'
        f'<text x="21" y="24.6" text-anchor="middle" font-size="2.5" fill="{C["txt3"]}" '
        f'font-family="Inter">total de saídas</text></svg>'
    )
    legenda = "".join(
        f'<div class="leg-row">'
        f'<span class="leg-dot" style="background:{PALETA_DONUT[i % len(PALETA_DONUT)]}"></span>'
        f'<span class="leg-cat">{c["categoria"]}</span>'
        f'<span class="leg-val">{c["valor_formatado"]}</span>'
        f'<span class="leg-pct">{c["valor"] / total * 100:.0f}%</span></div>'
        for i, c in enumerate(cats)
    )
    st.markdown(f'<div class="card">{donut}<div class="leg">{legenda}</div></div>',
                unsafe_allow_html=True)

    # meta
    m = tools.progresso_metas()["metas"][0]
    st.markdown(f'<div class="side-label">{ico(P_TARGET, C["txt3"], 13)} '
                f'Reserva de emergência</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="card"><div class="bar-track"><div class="bar-fill" '
        f'style="width:{min(m["progresso_pct"], 100)}%"></div></div>'
        f'<div class="bar-legend"><span><b>{m["progresso_pct"]}%</b> concluído</span>'
        f'<span>faltam <b>{m["falta_formatado"]}</b></span></div></div>',
        unsafe_allow_html=True,
    )

    # escudo
    d = tools.consultar_diario()
    st.markdown(f'<div class="side-label">{ico(P_SHIELD, C["txt3"], 13)} '
                f'Escudo antifraude</div>', unsafe_allow_html=True)
    if d["vazio"]:
        st.markdown(
            f'<div class="card shield-ok"><div class="shield-top">'
            f'{ico(P_SHIELD, C["ok"], 14)}<span class="shield-t">Nenhum incidente</span></div>'
            f'<div class="card-meta">9 tipos de golpe financeiro monitorados</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="card shield-alert"><div class="shield-top">'
            f'{ico(P_BOOK, C["alerta"], 14)}'
            f'<span class="shield-t">{d["total"]} no diário</span></div>'
            f'<div class="card-meta">Perda registrada: <b>{d["total_perdido_formatado"]}</b>'
            f'<br>Padrão: {d["tipo_recorrente"]}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="disclaimer">Dados fictícios para fins educacionais. '
                'Não constitui recomendação de investimento.</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------- agente
if "agente" not in st.session_state or st.session_state.get("_key") != api_key:
    st.session_state.agente = AgenteLuma(api_key or None)
    st.session_state._key = api_key
    st.session_state.mensagens = [
        {"role": "assistant", "content": st.session_state.agente.saudacao_proativa()}
    ]

agente: AgenteLuma = st.session_state.agente
AV_USER = avatar_user(ESCURO)

st.markdown(
    f'<div class="luma-head"><img class="luma-mark" src="{AVATAR_LUMA}" alt="Luma">'
    f'<div><p class="luma-title">Luma</p>'
    f'<p class="luma-sub">Agente financeira inteligente</p></div></div>',
    unsafe_allow_html=True,
)

if agente.modo == "gemini":
    st.markdown('<span class="badge badge-live"><span class="dot"></span>'
                'Gemini conectado</span>', unsafe_allow_html=True)
else:
    # O modo determinístico NAO e um estado de erro: e o fallback que responde
    # pelas 15 tools quando nao ha LLM. Por isso o texto e afirmativo, e nao
    # um pedido de chave.
    st.markdown('<span class="badge badge-demo"><span class="dot"></span>'
                'Modo determinístico — respostas vindas direto das 15 ferramentas'
                '</span>', unsafe_allow_html=True)


for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"],
                         avatar=AVATAR_LUMA if msg["role"] == "assistant" else AV_USER):
        escrever(msg["content"])
        if msg.get("meta"):
            st.caption(msg["meta"])


if len(st.session_state.mensagens) == 1:
    st.markdown(f'<div class="side-label" style="margin-top:1.4rem">Sugestões</div>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    for i, s in enumerate(["Quanto gastei com alimentação?",
                           "Quanto falta para minha meta?",
                           "Recebi uma ligação suspeita",
                           "Me pediram um Pix por engano"]):
        if cols[i % 2].button(s, use_container_width=True, key=f"sug{i}"):
            st.session_state.pendente = s
            st.rerun()


pergunta = st.chat_input("Pergunte sobre suas finanças ou descreva algo suspeito...")
if "pendente" in st.session_state:
    pergunta = st.session_state.pop("pendente")

if pergunta:
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user", avatar=AV_USER):
        st.markdown(pergunta.replace("$", r"\$"))

    with st.chat_message("assistant", avatar=AVATAR_LUMA):
        with st.spinner("Consultando sua base de dados..."):
            resp = agente.responder(pergunta)
        escrever(resp.texto)

        partes = [f"{resp.latencia_ms} ms"]
        if resp.ferramentas_usadas:
            partes.append(", ".join(dict.fromkeys(resp.ferramentas_usadas)))
        if resp.guardrails_acionados:
            partes.append("guardrail: " + ", ".join(resp.guardrails_acionados))
        meta = "   ·   ".join(partes)
        st.caption(meta)

    st.session_state.mensagens.append(
        {"role": "assistant", "content": resp.texto, "meta": meta}
    )
