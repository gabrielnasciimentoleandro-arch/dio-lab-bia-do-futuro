"""
cli.py — Interface de terminal do agente Luma.

Existe para garantir que QUALQUER avaliador consiga rodar o projeto,
mesmo sem instalar Streamlit e sem ter chave de API.

Uso:
    python src/cli.py
    GOOGLE_API_KEY=sua_chave python src/cli.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agente import AgenteLuma  # noqa: E402

VERDE, AMARELO, CINZA, NEGRITO, RESET = "\033[92m", "\033[93m", "\033[90m", "\033[1m", "\033[0m"


def limpar_markdown(t: str) -> str:
    return t.replace("**", "")


def main() -> None:
    agente = AgenteLuma()
    modo = ("Gemini conectado" if agente.modo == "gemini"
            else "modo demo (defina GOOGLE_API_KEY para ativar a IA)")

    print(f"\n{NEGRITO}{'-' * 68}")
    print("  Luma — Agente Financeira Inteligente")
    print(f"{'-' * 68}{RESET}")
    print(f"{CINZA}  {modo} · digite 'sair' para encerrar{RESET}\n")
    print(f"{VERDE} {limpar_markdown(agente.saudacao_proativa())}{RESET}\n")

    while True:
        try:
            pergunta = input(f"{NEGRITO} você: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nAté logo! \n")
            return

        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit", "q"}:
            print("\nAté logo! \n")
            return

        r = agente.responder(pergunta)
        print(f"\n{VERDE} Luma:{RESET} {limpar_markdown(r.texto)}")

        rodape = [f" {r.latencia_ms}ms"]
        if r.ferramentas_usadas:
            rodape.append(" " + ", ".join(dict.fromkeys(r.ferramentas_usadas)))
        if r.guardrails_acionados:
            rodape.append(" " + ", ".join(r.guardrails_acionados))
        print(f"{CINZA}   {' · '.join(rodape)}{RESET}\n")


if __name__ == "__main__":
    main()
