# SPEC: Main — Narrated Video Studio

## Objetivo
Empacotar em formato reutilizavel (Skill + CLI deterministico + Projeto de Referencia) o pipeline completo que transforma qualquer tema ou texto bruto em um video explicativo MP4 `1920x1080 @ 30fps` narrado em PT-BR (ou outro idioma suportado), com legendas sincronizadas por `WordBoundary`, ilustracoes 16:9 sem texto e animacoes vetoriais GSAP quadro a quadro via HyperFrames.

## Escopo
1. Skill agentica estruturada (`SKILL.md` + `references/*.md`) com integracao declarada as skills nativas do HyperFrames (`hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use`).
2. CLI Python deterministico (`scripts/narrated_video_cli.py`) com subcomandos:
   - `doctor`
   - `voices`
   - `synth-audio`
   - `synth-ambient`
   - `build-captions`
   - `scaffold-video`
   - `audit`
3. Exemplo canonico reproduzivel em `examples/ciclo-da-banana-60s/`.
4. Suite de testes automatizados (`tests/test_narrated_video_cli.py`).

## Criterios de Aceite
- Qualquer agente (Claude Code, Codex, Antigravity, Gemini CLI, OpenCode) consegue instalar a skill, rodar `narrated_video_cli.py doctor`, gerar roteiro dentro do orcamento de palavras, sintetizar audio e `timings.json`, gerar `captions.html`, fazer scaffold das cenas HyperFrames, auditar com `hyperframes check --strict` e renderizar o MP4 final sem passos obscuros.
- Zero emojis em todos os arquivos, codigos e outputs.
- Zero dependencias pagas obrigatorias.
