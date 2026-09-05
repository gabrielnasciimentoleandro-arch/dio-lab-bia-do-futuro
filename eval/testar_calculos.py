"""
testar_calculos.py — testes unitários das ferramentas determinísticas.

A suíte principal (avaliar.py) testa o AGENTE contra a base real. Estes testes
atacam as FERRAMENTAS com dados sintéticos, incluindo cenários que a base fixa
nunca produz — como um mês fechando no vermelho.

Motivo de existir: o painel e o agente diziam "dá para fechar em 0 mês(es)"
quando o saldo era negativo. O 0 significava "inalcançável", mas era lido como
boa notícia. Nenhum dos 48 casos pegava isso, porque o João sempre sobra
dinheiro no CSV oficial.

Rodar:  python eval/testar_calculos.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import ferramentas as tools  # noqa: E402

falhas: list[str] = []


def checar(nome: str, obtido, esperado) -> None:
    if obtido == esperado:
        print(f"  [ok]    {nome}")
    else:
        print(f"  [FALHA] {nome}\n          esperado: {esperado!r}\n          obtido:   {obtido!r}")
        falhas.append(nome)


def contem(nome: str, texto: str, trecho: str) -> None:
    if trecho.lower() in texto.lower():
        print(f"  [ok]    {nome}")
    else:
        print(f"  [FALHA] {nome}\n          '{trecho}' não está em: {texto!r}")
        falhas.append(nome)


print("\n=== Formatação de moeda ===")
checar("brl inteiro", tools.brl(1234.5), "R$ 1.234,50")
checar("brl zero", tools.brl(0), "R$ 0,00")
checar("brl negativo", tools.brl(-488.9), "R$ -488,90")
checar("brl milhão", tools.brl(1000000), "R$ 1.000.000,00")

print("\n=== prazo_texto: o bug do '0 mês(es)' ===")
checar("meta concluída", tools.prazo_texto(0), "meta já concluída")
checar("prazo normal", tools.prazo_texto(2), "dá para fechar em 2 mês(es)")
contem("saldo negativo é inalcançável", tools.prazo_texto(None), "não chega lá")
if "0 mês" in tools.prazo_texto(None):
    falhas.append("prazo_texto(None) não pode dizer '0 mês'")
    print("  [FALHA] prazo_texto(None) não pode dizer '0 mês'")
else:
    print("  [ok]    prazo_texto(None) nunca diz '0 mês'")

print("\n=== Coerência do resumo com a base real ===")
r = tools.resumo_financeiro()
soma_cats = round(sum(c["valor"] for c in r["gastos_por_categoria"]), 2)
checar("soma das categorias == saídas", soma_cats, round(r["saidas"], 2))
checar("saldo == entradas - saídas",
       round(r["saldo"], 2), round(r["entradas"] - r["saidas"], 2))
checar("taxa de poupança confere",
       r["taxa_poupanca_pct"], round(r["saldo"] / r["entradas"] * 100, 1))

print("\n=== Guardrail de perfil (produtos de risco) ===")
pr = tools.recomendar_produtos()
if not pr["aceita_risco"]:
    riscos = {p["risco"].lower() for p in pr["produtos_compativeis"]}
    checar("avesso a risco só vê risco baixo", riscos, {"baixo"})
    checar("produtos de risco foram bloqueados",
           len(pr["produtos_bloqueados"]) > 0, True)

print("\n=== Progresso de metas ===")
for m in tools.progresso_metas()["metas"]:
    nome = m["meta"][:28]
    checar(f"{nome}: pct entre 0 e 100", 0 <= m["progresso_pct"] <= 100, True)
    checar(f"{nome}: falta nunca negativo", m["falta"] >= 0, True)

print("\n=== Detecção de fraude: marcadores decisivos ===")
for frase, esperado in [
    ("me mandaram transferir pra uma conta segura", "ALTO"),
    ("investimento com retorno garantido e risco zero", "ALTO"),
    ("meu vizinho me convidou para um churrasco", "INDETERMINADO"),
]:
    checar(f"'{frase[:34]}...'",
           tools.analisar_suspeita(frase)["nivel_risco"], esperado)

print("\n" + "=" * 62)
if falhas:
    print(f"  {len(falhas)} FALHA(S): " + ", ".join(falhas))
    sys.exit(1)
print("  Todos os testes unitários passaram.")
print("=" * 62 + "\n")
