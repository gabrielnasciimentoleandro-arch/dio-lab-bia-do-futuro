"""
avaliar.py — Suíte de avaliação automatizada do agente Luma.

Roda todos os casos de eval/casos_teste.json contra o agente e gera:
  * relatório no terminal
  * eval/resultado.md  (tabela por métrica, pronta para o README)
  * eval/resultado.json

Uso:
    python eval/avaliar.py            # modo demo (sem API)
    GOOGLE_API_KEY=... python eval/avaliar.py   # contra o Gemini real
"""

from __future__ import annotations

import json
import re
import statistics
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from agente import AgenteLuma, DISCLAIMER  # noqa: E402


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def avaliar_caso(agente: AgenteLuma, caso: dict) -> dict:
    r = agente.responder(caso["pergunta"])
    texto_n = normalizar(r.texto)
    falhas: list[str] = []

    for termo in caso.get("deve_conter", []):
        if normalizar(termo) not in texto_n:
            falhas.append(f"faltou o termo '{termo}'")

    for termo in caso.get("nao_deve_conter", []):
        if normalizar(termo) in texto_n:
            falhas.append(f"contém termo proibido '{termo}'")

    esperada = caso.get("ferramenta_esperada")
    if esperada and esperada not in r.ferramentas_usadas:
        falhas.append(f"não usou a ferramenta '{esperada}'")

    guard = caso.get("guardrail_esperado")
    if guard and guard not in r.guardrails_acionados:
        falhas.append(f"guardrail '{guard}' não acionou")

    if caso.get("exige_fonte") and "[fonte]" not in r.texto:
        falhas.append("resposta sem citação de fonte")

    if caso.get("exige_disclaimer") and DISCLAIMER not in r.texto:
        falhas.append("resposta sem disclaimer de compliance")

    return {
        "id": caso["id"],
        "metrica": caso["metrica"],
        "categoria": caso["categoria"],
        "pergunta": caso["pergunta"],
        "resposta": r.texto,
        "passou": not falhas,
        "falhas": falhas,
        "ferramentas": r.ferramentas_usadas,
        "guardrails": r.guardrails_acionados,
        "latencia_ms": r.latencia_ms,
    }


def main() -> int:
    suite = json.loads((RAIZ / "eval" / "casos_teste.json").read_text(encoding="utf-8"))
    agente = AgenteLuma()

    print(f"\n{'='*66}\n  SUÍTE DE AVALIAÇÃO — AGENTE LUMA")
    print(f"  modo: {agente.modo}  |  casos: {len(suite['casos'])}\n{'='*66}\n")

    resultados = [avaliar_caso(agente, c) for c in suite["casos"]]

    for r in resultados:
        icone = "✅" if r["passou"] else "❌"
        print(f"{icone} [{r['id']}] {r['pergunta'][:52]:<52} {r['latencia_ms']:>4}ms")
        for f in r["falhas"]:
            print(f"      ↳ {f}")

    # agregação por métrica
    por_metrica: dict[str, list[dict]] = {}
    for r in resultados:
        por_metrica.setdefault(r["metrica"], []).append(r)

    linhas_md = []
    print(f"\n{'='*66}\n  RESULTADO POR MÉTRICA\n{'='*66}")
    for metrica, itens in sorted(por_metrica.items()):
        ok = sum(i["passou"] for i in itens)
        pct = ok / len(itens) * 100
        nota = round(pct / 20, 1)  # escala 1-5
        print(f"  {metrica.capitalize():<16} {ok:>2}/{len(itens):<3} {pct:>5.1f}%   nota {nota}/5")
        linhas_md.append(f"| {metrica.capitalize()} | {ok}/{len(itens)} | {pct:.1f}% | {nota}/5 |")

    total_ok = sum(r["passou"] for r in resultados)
    pct_geral = total_ok / len(resultados) * 100
    lat = [r["latencia_ms"] for r in resultados]

    print(f"\n  {'GERAL':<16} {total_ok:>2}/{len(resultados):<3} {pct_geral:>5.1f}%   "
          f"nota {round(pct_geral/20, 1)}/5")
    print(f"  Latência média: {statistics.mean(lat):.0f}ms  |  p95: {max(lat)}ms")
    print(f"  Guardrails acionados: "
          f"{sum(1 for r in resultados if r['guardrails'])}/{len(resultados)}\n")

    # ---------------------------------------------------------- relatórios
    falhas_md = "\n".join(
        f"- **[{r['id']}]** {r['pergunta']} → {'; '.join(r['falhas'])}"
        for r in resultados if not r["passou"]
    ) or "_Nenhuma falha._"

    md = f"""# Resultado da Avaliação Automatizada

> Gerado por `eval/avaliar.py` em {datetime.now():%d/%m/%Y %H:%M} · modo `{agente.modo}` · {len(resultados)} casos

## Resumo por Métrica

| Métrica | Aprovados | Taxa | Nota |
|---|---|---|---|
{chr(10).join(linhas_md)}
| **GERAL** | **{total_ok}/{len(resultados)}** | **{pct_geral:.1f}%** | **{round(pct_geral/20, 1)}/5** |

## Observabilidade

| Indicador | Valor |
|---|---|
| Latência média | {statistics.mean(lat):.0f} ms |
| Latência máxima | {max(lat)} ms |
| Casos com guardrail acionado | {sum(1 for r in resultados if r['guardrails'])} |
| Casos com citação de fonte | {sum(1 for r in resultados if '[fonte]' in r['resposta'])} |

## Falhas Detectadas

{falhas_md}

## Detalhamento

| ID | Métrica | Categoria | Pergunta | Resultado |
|---|---|---|---|---|
""" + "\n".join(
        f"| {r['id']} | {r['metrica']} | {r['categoria']} | {r['pergunta'][:44]} | "
        f"{'✅' if r['passou'] else '❌'} |" for r in resultados
    ) + "\n"

    (RAIZ / "eval" / "resultado.md").write_text(md, encoding="utf-8")
    (RAIZ / "eval" / "resultado.json").write_text(
        json.dumps({"modo": agente.modo, "geral_pct": pct_geral, "resultados": resultados},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"📄 eval/resultado.md e eval/resultado.json gerados.\n")
    return 0 if total_ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
