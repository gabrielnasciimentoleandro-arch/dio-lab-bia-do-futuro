# Áudio de referência do pitch

Narração sintetizada do roteiro de [`docs/05-pitch.md`](../docs/05-pitch.md).

**Isto é material de ensaio, não a entrega.** Serve para você ouvir o ritmo,
conferir onde o texto trava na boca e cronometrar antes de gravar com a sua
própria voz. O pitch enviado à banca deve ser seu — é você que vai responder
às perguntas depois.

---

## Arquivos

| Arquivo | Bloco | Duração |
|---|---|---|
| `00-pitch-completo.mp3` | Tudo, com pausas de 0,9s entre blocos | **2min56s** |
| `01-problema.mp3` | O João poupa 50% e não bate a meta | 25,8s |
| `02-solucao.mp3` | A Luma antecipa, não espera a pergunta | 17,3s |
| `03-demo1-arquitetura.mp3` | Número com fonte, o LLM não calcula | 30,1s |
| `04-demo2-cocriacao.mp3` | Plano que respeita o veto do cliente | 34,3s |
| `05-demo3-protecao.mp3` | Antifraude e recusa do fundo | 23,9s |
| `06-prova.mp3` | 62 casos, 17 falhas documentadas | 24,1s |
| `07-fecho.mp3` | Arquitetura > prompt · saber dizer "não sei" | 16,1s |

Total falado: **172s**. Com as pausas: **177s**. Sobram 3 segundos dos 180.

---

## Como usar no ensaio

1. Ouça o completo uma vez, sem fazer nada, só para pegar o ritmo geral.
2. Ouça bloco a bloco, **falando junto**. É assim que se descobre qual frase
   não cabe no fôlego.
3. Grave você lendo e compare a duração com a tabela acima. Se o seu bloco
   estiver mais de 15% acima, você está falando devagar demais para o tempo.
4. Ensaie a transição entre blocos com o app aberto: o gargalo real não é
   falar, é falar **enquanto** navega na tela.

---

## Diferenças entre o áudio e o texto escrito

Algumas palavras foram adaptadas para soarem naturais faladas:

- `transacoes.csv` -> "transações ponto csv"
- `python eval/avaliar.py` -> "python avaliar"
- Valores por extenso: "quinhentos e setenta reais", não "R$ 570,00"

Faça o mesmo ao gravar. Ler pontuação de código em voz alta soa robótico.

---

## Regerar

As chamadas de síntese estão no histórico da conversa que gerou este projeto.
Para trocar a voz ou ajustar o texto, basta refazer a partir dos blocos de
fala marcados com `>` em `docs/05-pitch.md`.
