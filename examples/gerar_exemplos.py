"""
Gera examples/conversas.md executando a agente de verdade.

O arquivo de exemplos NÃO é escrito à mão. Ele é a transcrição real do que a
Luma responde hoje, com as ferramentas que ela acionou em cada turno. Assim
a documentação não tem como divergir do código: se o comportamento mudar e
alguém esquecer de atualizar o texto, basta rodar este script de novo.

    python examples/gerar_exemplos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from agente import AgenteLuma  # noqa: E402

# Cada roteiro é uma conversa contínua: a mesma instância responde a todos os
# turnos, porque parte do que queremos mostrar só existe em multi-turno
# (memória de oferta, refinamento da resposta anterior).
ROTEIROS: list[tuple[str, str, list[str]]] = [
    (
        "Consulta de gastos e simulação",
        "*O caminho mais comum:* o cliente pergunta para onde foi o dinheiro, "
        "aceita a oferta da agente e recebe uma simulação com restrição.",
        [
            "oi",
            "quanto gastei com alimentação?",
            "sim",
            "simule um corte de 30%",
            "moradia eu não posso cortar",
        ],
    ),
    (
        "Cocriação de plano com restrição do cliente",
        "O pilar **cocriar**. O cliente veta cortes e a agente precisa montar um "
        "plano que respeite o veto — e ainda encurtá-lo quando ele pede.",
        [
            "vamos bolar um plano para poupar nosso dinheiro?",
            "o que podemos fazer com o que já tenho sem cortar gastos atuais?",
            "pode simplificar pra mim está muito longo",
            "qual a mais importante?",
        ],
    ),
    (
        "Antifraude social",
        "A base de golpes em uso. A agente classifica o risco, aponta os "
        "marcadores decisivos e registra o incidente.",
        [
            "recebi uma ligação do banco pedindo meu código de aprovação",
            "quais são os golpes mais comuns?",
            "me da so uma",
        ],
    ),
    (
        "Limites: o que a Luma se recusa a fazer",
        "Fora de escopo, dado inexistente, promessa de rentabilidade e dado de "
        "terceiros. Em todos, a recusa é explícita e reconduz à conversa.",
        [
            "qual o melhor time de futebol?",
            "quanto gastei com criptomoedas?",
            "qual investimento me dá 20% garantido ao mês?",
            "meu celular está lento, o que faço?",
            "quanto minha esposa gastou esse mês?",
        ],
    ),
]


def bloco(titulo: str, descricao: str, turnos: list[str]) -> str:
    agente = AgenteLuma()  # instância nova = conversa nova
    linhas = [f"## {titulo}", "", descricao, ""]
    for pergunta in turnos:
        r = agente.responder(pergunta)
        linhas.append(f"**Cliente:** {pergunta}")
        linhas.append("")
        linhas.append("**Luma:**")
        linhas.append("")
        for ln in r.texto.strip().splitlines():
            linhas.append(f"> {ln}" if ln.strip() else ">")
        linhas.append("")
        tools = ", ".join(f"`{t}`" for t in r.ferramentas_usadas) or "_nenhuma_"
        linhas.append(f"<sub>Ferramentas: {tools}</sub>")
        linhas.append("")
        linhas.append("---")
        linhas.append("")
    return "\n".join(linhas)


def main() -> None:
    partes = [
        "# Exemplos de interação",
        "",
        "> Transcrições **geradas automaticamente** por "
        "`examples/gerar_exemplos.py`, executando a agente em modo "
        "determinístico (sem chave de API). Cada turno mostra as ferramentas "
        "realmente acionadas.",
        "",
        "Para regerar após qualquer mudança de comportamento:",
        "",
        "```bash",
        "python examples/gerar_exemplos.py",
        "```",
        "",
        "---",
        "",
    ]
    for titulo, descricao, turnos in ROTEIROS:
        partes.append(bloco(titulo, descricao, turnos))

    saida = RAIZ / "examples" / "conversas.md"
    saida.write_text("\n".join(partes), encoding="utf-8")
    print(f"gerado: {saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
