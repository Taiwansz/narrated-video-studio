# SPEC: Security & Hygiene

## Controles Aplicados
1. **Confinamento de Caminhos (`Path Traversal Prevention`):**
   - Nomes de cena (`id`, `composition_id`) passam por sanitizacao estrita (`^[a-zA-Z0-9_-]+$`), impedindo `../` ou injecao de caminhos ao gerar arquivos em `assets/`, `cenas/` ou `compositions/`.
2. **Execucao Segura de Subprocessos:**
   - Todas as chamadas a `ffmpeg`, `ffprobe` e `npx` usam lista de argumentos explicitos com `shell=False`.
3. **Resiliencia e Protecao de Rate Limit:**
   - Cliente `edge-tts` encapsulado com `MonotonicRateLimiter` (`time.monotonic()`) e retry exponencial com jitter para erros transientes (`429`, `5xx`, desconexao WebSocket), evitando spam de requisicoes.
4. **Higiene de Segredos e Dependencias:**
   - Zero API keys exigidas ou hardcoded no repositorio.
   - Instalacoes Python isoladas exclusivamente via `.venv` ou `uv`, nunca `pip install` global.
5. **Tolerancia Zero a Emojis:**
   - O subcomando `audit` varre HTML, JSON, SRT e Markdown com regex Unicode estrita e falha caso detecte qualquer emoji.
