# Engenharia de Voz, Loudness e Trilha Ambiente

## 1. Matriz de Vozes Gratuitas PT-BR (`edge-tts`)
O `edge-tts` nao exige chave de API e entrega eventos `WordBoundary` em microssegundos (`offset / 10_000_000`). Vozes recomendadas para aulas e documentarios tecnicos:

| Voz | Perfil | Uso Recomendado |
| :--- | :--- | :--- |
| `pt-BR-AntonioNeural` | Masculina, grave, cadencia documental | Canal Dark, documentario cientifico, arquitetura de sistemas |
| `pt-BR-ThalitaMultilingualNeural` | Feminina, natural, excelente em anglicismos | Conteudo tecnico com termos em ingles (`AST`, `Lexer`, `Docker`) |
| `pt-BR-FranciscaNeural` | Feminina, clara e didatica | Tutoriais, explicacoes passo a passo |

Verifique a lista viva com:
```bash
python scripts/narrated_video_cli.py voices --locale pt-BR --output voices.json
```

## 2. Normalizacao Uniforme e Protecao Contra Clipping
Nunca normalize cada cena isoladamente antes de juntar o video: se uma cena tiver silêncio menor ou pico diferente, o volume da voz vai oscilar entre cortes.
O `narrated_video_cli.py synth-audio`:
1. Recorta cada cena ate `last_word_end + 0.14s` com fade-out de `25ms` (`afade`) para eliminar cliques de fim de frase.
2. Concatena as falas temporariamente e mede `integrated_lufs` e `max_volume_db` via `ffmpeg -af volumedetect,ebur128`.
3. Calcula um **unico ganho uniforme**:
   `gain_db = min(target_lufs - integrated_lufs, -1.5 - max_volume_db)`
   Garantindo alvo `-17.0 LUFS` na voz principal e teto estrito de pico em `-1.5 dBFS` (zero clipping).
4. Monta `narration.mp3` usando `adelay` exato nos offsets de cada cena (`slot_start_sec + slot_pad_sec`) em `48000 Hz`, estereo, `192 kbps`.

## 3. Trilha Ambiente Sem Copyright (`synth-ambient`)
O subcomando `synth-ambient` (ou flag `--ambient` em `synth-audio`) sintetiza via `ffmpeg` (`lavfi`) uma cama harmonica suave (acorde de quinta/nona filtrado com `lowpass=f=680`, eco suave e fades de entrada/saida) calibrada em `-24.0 LUFS`.
No `index.html` do HyperFrames, a trilha entra separada da voz com `data-volume="0.32"`, garantindo separacao limpa entre locucao e fundo sem disputa de frequencias medias.

## 4. Substituicao por Voz Humana Real
Se o autor ou docente preferir narrar com a propria voz:
1. Grave o roteiro lendo `ROTEIRO` / `script.json` em `.mp3` ou `.wav`.
2. Normalize a voz gravada com `ffmpeg` ou `npx hyperframes normalize-audio` para `-17 LUFS`.
3. Substitua `assets/narration.mp3` no projeto HyperFrames.
4. Extraia os novos timestamps palavra por palavra com Whisper PT-BR:
   ```bash
   npx hyperframes transcribe assets/narration.mp3 --model small --language pt --json --output transcript.json
   ```
   *(Atencao: sempre passar `--language pt`, pois o default `small.en` traduz ou corrompe portugues.)*
5. Atualize `timings.json` e execute `build-captions` novamente.
