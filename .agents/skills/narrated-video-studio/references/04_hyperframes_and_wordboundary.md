# Contrato HyperFrames e Coreografia via WordBoundary

## 1. Regras Inviolaveis do Render Deterministico HyperFrames
O HyperFrames renderiza HTML quadro a quadro buscando `seek(t)` sobre timelines pausadas (`gsap.timeline({ paused: true })`). Qualquer violacao abaixo quebra a determinicidade ou falha em `npx hyperframes check --strict`:

1. **Registro obrigatorio por composicao:**
   ```js
   window.__timelines = window.__timelines || {};
   const tl = gsap.timeline({ paused: true });
   // ... tweens ...
   tl.to({}, { duration: SCENE_DURATION }, 0);
   window.__timelines["scene-01"] = tl;
   ```
   Se houver sub-composicoes (`data-composition-src="compositions/scene-01.html"`), cada arquivo deve usar `<template>`, estilizar `#root` e registrar seu proprio `data-composition-id`.
2. **Elementos temporizados:** todo elemento controlado pela timeline no root leva `class="clip"`, `data-start` e `data-duration` em segundos.
3. **Proibicoes de propriedade:**
   - Nunca animar `display`, `visibility` ou `autoAlpha` diretamente em um `.clip` — anime um wrapper filho interno (`.cap-inner`), deixando o `.clip` como container estrutural.
   - Nunca definir `transform:` no CSS de um elemento que o GSAP anima com `scale`, `x`, `y` ou `rotation` (use `transform-origin` apenas).
   - Nunca usar `Date.now()`, `Math.random()` sem seed, `setTimeout`, `requestAnimationFrame` avulso ou `repeat: -1`.
   - Nunca usar barra inicial em caminhos de midia: sempre `assets/01.png`, jamais `/assets/01.png`.
4. **Audio no Root (`index.html`):**
   - Toda tag `<audio>` precisa de `id` unico (senao o mixer a ignora), `class="clip"`, `data-start`, `data-duration` e zero `crossorigin`.
   - Voz e trilha ambiente ficam em tags `<audio>` distintas com `data-track-index="3"` e `"4"`.

## 2. Sincronizando Animacoes SVG e Cards com a Fala (`WordBoundary`)
Consulte o `timings.json` gerado pelo `synth-audio` antes de escrever os tempos do GSAP na cena:
- Se a cena dura `12.0s` (de `24.0s` a `36.0s` no video global) e a locucao pronuncia `"geotropismo negativo"` em `global = 32.61s` (`local = 8.46s`), agende o desenho do arco SVG (`strokeDashoffset -> 0`) exatamente em `t = 8.0s..9.4s` na timeline local da cena.
- **Armadilha da caixa vazia:** Se um diagrama SVG so sera desenhado aos `6s` da cena, nao deixe uma moldura retangular vazia piscando desde `t=0`. Ou desenhe os eixos/referencias estruturais logo em `0.5s..1.2s` (com dados entrando no timestamp da palavra), ou revele o container do diagrama junto com a primeira linha estrutural.

## 3. Legendas WordBoundary (`build-captions`)
O subcomando `build-captions` cria automaticamente `compositions/captions.html`:
- Agrupa palavras em blocos de `2 a 5` palavras respeitando pontuacao e pausas (`>= 150ms`).
- Garante que nenhuma legenda sobreponha a seguinte.
- Ilumina palavra por palavra de `#A7A294` para `#F3EFE2` (ou cor de acento `#E2B43B` para `keywords`) no instante exato (`w.start`) do evento `WordBoundary`.
