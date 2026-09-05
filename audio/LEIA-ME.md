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
| `00-pitch-completo.mp3` | Tudo, com pausas de 0,9s entre blocos | **2min25s** |
| `01-problema.mp3` | O João guarda metade da renda e não bate a meta | 21,1s |
| `02-solucao.mp3` | A Luma fala antes de ser perguntada | 13,2s |
| `03-demo1-arquitetura.mp3` | O número tem origem; não é a IA que calcula | 22,4s |
| `04-demo2-cocriacao.mp3` | Plano que respeita o que o cliente pediu | 30,5s |
| `05-demo3-protecao.mp3` | Golpe e recusa do fundo | 22,1s |
| `06-prova.mp3` | 62 testes · 17 erros achados e corrigidos | 14,4s |
| `07-fecho.mp3` | Separar quem conversa de quem calcula | 17,2s |

Total falado: **141s**. Com as pausas: **146s**.

Sobram **34 segundos** dos três minutos. Essa folga é proposital: no vídeo real
você não só fala, você também navega, cola mensagem e espera a tela desenhar.
Um roteiro que ocupa 100% do tempo estoura sempre.

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

O roteiro foi reescrito para soar como fala, não como documentação:

- "quem soma é o código" em vez de "cálculo determinístico via function calling"
- "de onde ela tirou isso" em vez de "campo `_fonte` para rastreabilidade"
- "dezessete erros que eu achei e corrigi" em vez de "17 falhas documentadas"
- Nada de ler nome de arquivo ou comando em voz alta
- Valores por extenso: "quinhentos e setenta reais", não "R$ 570,00"

Isso não é simplificar por baixo. Quem avalia entende de tecnologia — mas um
pitch que soa como manual cansa, e cada palavra técnica a mais custa segundos
que você não tem. O vocabulário técnico está guardado para as perguntas da
banca, na tabela ao fim de `docs/05-pitch.md`.

---

## Regerar

As chamadas de síntese estão no histórico da conversa que gerou este projeto.
Para trocar a voz ou ajustar o texto, basta refazer a partir dos blocos de
fala marcados com `>` em `docs/05-pitch.md`.
