# Direcao Visual, Prompts de Imagem e Regras Anti-Slop

## 1. Padrao Estetico de Video Explicativo (1920x1080)
Um video tecnico ou documental de alto nivel **nao** usa B-roll generico desconexo nem cards centralizados minusculos sobre tela preta vazia.

- **Regra do Frame 0:** O quadro inicial (`0.0s`) ja deve abrir composto — imagem de fundo em movimento lento, titulo principal ancorado e estrutura do grafico visivel.
- **Hierarquia Tipografica em 1080p:**
  - Kicker tecnico (`JetBrains Mono` / monospace): `26px–28px`, caixa alta, `letter-spacing: 0.1em`, filete vertical `4px` na cor de acento.
  - Display Title (`Playfair Display` ou `Space Grotesk` / `Syne`): `66px–84px`, `font-weight: 800`, `line-height: 1.02–1.05`, `letter-spacing: -0.025em`.
  - Leitura secundaria / rotulos de cards (`Inter` / `Plus Jakarta Sans`): **minimo 28px** (texto abaixo de `24px` em 1080p perde nitidez em compressao H.264/celular).
  - Legendas sincronizadas (`captions.html`): `44px`, peso `600/700`, sombra discreta + fundo escuro semitransparente `rgba(11,13,10,0.88)` e filete de base `2px`.

## 2. Zonas Seguras (Action-Safe e Title-Safe)
- **90% Action-Safe:** `x = 96..1824`, `y = 54..1026`.
- **80% Title-Safe (textos, kickers, graficos e legendas):** `x = 192..1728`, `y = 108..972`.
- **Faixa reservada de legendas:** `y = 832..962` (`bottom: 120px`, `height: 112px`). Nenhuma cena deve colocar cards importantes ou textos informativos nessa faixa inferior.

## 3. Como Gerar Placas Visuais Sem Quebrar a Composicao
Ao acionar um gerador de imagens (`image-generator`, FLUX local ou equivalente):
1. Exija sempre proporcao **16:9 widescreen**.
2. Proiba explicitamente qualquer texto na imagem: `"no text, no labels, no letters, no numbers, no watermarks anywhere in the image"`. Texto desenhado por modelo de imagem quase sempre sai deformado e colide com a tipografia editorial.
3. Pecas com borda de papel ou margem branca (comuns em ilustracoes estilo prancha botanica/cientifica): aplique `scale >= 1.10` no container `.plate-inner` desde `t=0` com `overflow: hidden` para cortar margens externas automaticamente durante o Ken Burns.
4. Adicione gradiente direcional (`scrim-left` + `scrim-bottom`) acima da imagem e abaixo do texto para garantir contraste WCAG AA/AAA mesmo sobre cenas iluminadas.

## 4. Variacao Entre Cenas e Proibicoes Absolutas
- Varie o enquadramento entre cenas consecutivas:
  - Cena 1: Full-bleed com scrim lateral esquerdo e instrumento vetorial flutuante.
  - Cena 2: Split 60/40 com revelacao por `clip-path`.
  - Cena 3: Placa ancorada a direita e vetores fisicos a esquerda.
  - Cena 4: Palco bilateral com grafico de curva + medidores percentuais animados.
  - Cena 5: Pull-out com anel ciclico fechado e tese final imovel nos ultimos `2.5s`.
- **Proibido (AI-Slop):**
  - Emojis em qualquer texto, legenda, codigo ou arquivo.
  - Gradientes roxo/magenta genericos de IA sobre fundo preto.
  - Capsulas/pilulas arredondadas (`rounded-full`) envolvendo etiquetas de texto.
  - Icones `sparkles` ou HUDs decorativos sem funcao informacional.
