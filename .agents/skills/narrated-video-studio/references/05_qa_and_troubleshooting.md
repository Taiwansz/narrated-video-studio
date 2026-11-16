# Quality Assurance (QA), Render e Troubleshooting

## 1. Checklist Obrigatorio Pre-Render
Execute nesta ordem dentro da pasta do projeto HyperFrames:

```bash
# 1. Lint estrutural rapido
npx hyperframes lint

# 2. Check rigoroso completo (lint + runtime + layout + contraste + craft + audio)
npx hyperframes check --json --strict --samples 15

# 3. Captura visual de revisao + meio de cada cena (exemplo 60s em 5 cenas)
npx hyperframes snapshot --review
npx hyperframes snapshot --at 6,18,30,42,54
npx hyperframes snapshot --at 9.5,22,34,45.5,58.5
```
Inspecione os PNGs gerados em `.hyperframes/artifacts/snapshots/` com ferramenta de leitura de imagem antes de renderizar o MP4 final. Nunca confie apenas em `ok: true` sem olhar os quadros reais.

## 2. Render Final e Auditoria de Saida
```bash
npx hyperframes render --quality delivery --output video_final.mp4
python scripts/narrated_video_cli.py audit --project-dir . --mp4 video_final.mp4 --strict-hyperframes --output audit_report.json
```
Valores esperados no MP4 final:
- `width = 1920`, `height = 1080`, `r_frame_rate = 30/1`.
- `duration` exatamente igual ao `data-duration` da composicao raiz.
- `audio` presente (`48000 Hz`, estereo), `mean_volume` tipicamente entre `-23 dB` e `-16 dB`, `max_volume <= -1.0 dB`.
- `emoji_hits = []`.

Decodifique ao menos 3 quadros do `.mp4` renderizado para validar a composicao final apos encoding:
```bash
ffmpeg -y -ss 9.5 -i video_final.mp4 -frames:v 1 check_s1.png
ffmpeg -y -ss 34.0 -i video_final.mp4 -frames:v 1 check_s3.png
ffmpeg -y -ss 58.5 -i video_final.mp4 -frames:v 1 check_s5.png
```

## 3. Erros Comuns e Correcoes Diretas
1. **`WordBoundary` count mismatch no `edge-tts`:**
   - Causa: numeros/siglas (`C2H4`, `50%`, `1920x1080`) divididos pelo tokenizador da voz.
   - Solucao: escrever por extenso no texto de narracao (`"gas etileno"`, `"cinquenta por cento"`) ou omitir `--strict-tokens` para interpolacao proporcional automatica.
2. **Audio cortado no fim de uma cena ou estourando 60s:**
   - Causa: roteiro com mais de ~30 palavras em um slot de 12s.
   - Solucao: o `synth-audio` falha explicitamente indicando a cena excedente; enxugue 3 a 5 palavras na cena apontada e reexecute.
3. **Borda clara/branca ao redor de ilustracoes geradas:**
   - Solucao: garantir `scale >= 1.10` no wrapper interno com `overflow: hidden` no container da prancha.
4. **Legenda invisivel ou cortada fora da tela:**
   - Solucao: manter `.cap-safe-band` em `left: 192px; width: 1536px; bottom: 120px` com `data-layout-allow-caption-zone`.
5. **Contrast check falhando em texto verde/colorido sobre fundo escuro:**
   - Solucao: usar tom de alto contraste para texto legivel (`#7AC289` para texto e `#3B6E47` apenas para filetes/bordas).
