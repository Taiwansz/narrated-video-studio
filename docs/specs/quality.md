# SPEC: Quality Gates

## Portoes Obrigatorios Antes de Declarar um Video Pronto
1. **Audio & Loudness (`ffprobe` + `volumedetect` + `ebur128`):**
   - Voz normalizada em aproximadamente `-17.0 LUFS` com pico maximo <= `-1.5 dBFS` (zero clipping).
   - Trilha ambiente separada em aproximadamente `-24.0 LUFS` com fade-in/fade-out e `data-volume="0.32"` no HyperFrames.
2. **Auditoria Estatica e Runtime (`npx hyperframes check --json --strict --samples 15`):**
   - `ok: true`
   - `lint`: 0 erros
   - `runtime`: 0 erros
   - `layout`: 0 erros em todas as amostras
   - `contrast`: 100% aprovado
   - `craft`: 0 erros
   - `audio`: 0 erros
3. **Inspecao Visual Real:**
   - Snapshots em `--review` e no meio/fim de cada cena inspecionados visualmente (leitura de PNG) mais quadros decodificados do `.mp4` final.
4. **Testes da Ferramenta:**
   - `python -m unittest discover -s tests -v` verde apos qualquer edicao no CLI.
