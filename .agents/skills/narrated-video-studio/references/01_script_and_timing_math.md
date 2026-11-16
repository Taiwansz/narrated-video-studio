# Matematica de Roteiro e Orcamento Temporal (PT-BR)

## 1. Taxa de Fala Real em PT-BR (`edge-tts`)
Em vozes neurais PT-BR (`pt-BR-AntonioNeural`, `pt-BR-FranciscaNeural`, `pt-BR-ThalitaMultilingualNeural`), a cadencia natural sem aceleracao artificial situa-se em:
- **130 a 148 palavras por minuto** (`2.2 a 2.5 palavras por segundo`).
- Para um video de **60 segundos** com `5 cenas` de `12.0s` cada:
  - **Orcamento ideal por cena:** `24 a 30 palavras` (`~10.8s a 11.6s` falados).
  - **Folga obrigatoria no inicio do slot (`slot_pad_sec`):** `0.15s` a `0.25s` para evitar corte brusco na transicao visual.
  - **Folga obrigatoria no final do slot:** encerrar a fala antes de `slot_end_sec - 0.30s` (e no ultimo slot antes de `total_duration_sec - 0.50s`) para respiro de encerramento.
- Para videos maiores (ex.: `2 minutos = 120s`, `8 cenas` de `15s`): manter `~32 a 38 palavras` por cena.

## 2. Regras de Escrita Falavel (Zero "Leitura de Slides")
- Frases curtas (`10 a 18 palavras` por sentenca), voz ativa, verbos concretos.
- Nunca colocar marcadores, barras (`/`), siglas nao pronunciaveis cruas ou parenteses densos no texto de narracao.
  - Ruim: `"Fase 4 (C2H4 / amido -> acucares): ~22%."`
  - Bom: `"Como fruto climaterico, a banana acelera a respiracao e libera o gas etileno."`
- Usar virgulas e pontos onde o locutor deve respirar — `edge-tts` pausa `150ms a 350ms` em pontuacao forte, o que alimenta diretamente o agrupador `build_caption_groups`.

## 3. Paridade de Tokens `WordBoundary`
O `edge-tts` emite eventos `WordBoundary` para cada palavra sintetizada. Em Portugues:
- Palavras compostas ou hifenizadas (`"corta-lo"`, `"curvando-se"`) normalmente geram `1` token `WordBoundary`.
- Simbolos matematicos (`C2H4`, `90%`, `1080p`, `O(n^2)`) podem ser fragmentados pelo motor em multiplos sub-tokens e quebrar a contagem 1:1 com `text.split()`.
- **Regra:** Escreva termos tecnicos por extenso no campo `text` de `script.json` (`"gas etileno"`, `"noventa por cento"`) enquanto mantem a notacao formal (`C2H4`, `90%`, `O(n^2)`) nos graficos SVG e cartoes visuais da tela. Use `--strict-tokens` sempre que quiser garantia absoluta 1:1.

## 4. Contrato do `script.json`
```json
{
  "title": "Titulo da Apresentacao",
  "language": "pt-BR",
  "voice": "pt-BR-AntonioNeural",
  "total_duration_sec": 60.0,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "slot_pad_sec": 0.15,
  "target_lufs": -17.0,
  "ambient_lufs": -24.0,
  "palette": {
    "ground": "#0B0D0A",
    "ink": "#F3EFE2",
    "ink_secondary": "#C7C1B0",
    "accent": "#E2B43B",
    "secondary": "#3B6E47",
    "secondary_readable": "#7AC289"
  },
  "scenes": [
    {
      "id": "scene-01-abertura",
      "composition_id": "scene-01",
      "title": "Titulo Curto",
      "kicker": "ESTAGIO 01 / 05 // CONTEXTO",
      "subtitle": "Subtitulo conciso",
      "image": "01_abertura.png",
      "duration_sec": 12.0,
      "keywords": ["palavra1", "palavra2"],
      "text": "Texto exato que sera narrado nesta cena."
    }
  ]
}
```
