# SPEC — Apresentacao 01: Ciclo de Vida da Banana (Musa spp.)

GOAL:    Fazer o espectador compreender em 60 segundos que a bananeira e uma planta herbacea gigante cujo pseudocaule morre apos frutificar, perpetuando-se pelo rizoma subterraneo e pelo perfilho sucessor.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps, arquivo final apresentacao_01_ciclo_banana.mp4 (--quality delivery).
TIME:    60.0 s x 30 fps = 1800 frames. Sincronizacao de cenas e legendas governada pelos timestamps de ap01_timings.json.
LOOK:    ground #0B0D0A com vinheta radial local e grao filmico deterministico (opacity 0.045);
         ink primaria #F3EFE2, ink secundaria #C7C1B0;
         acento principal #E2B43B (ouro banana) para palavras-chave, vetores ativos e indicadores numericos;
         acento secundario #3B6E47 (verde folha) para filetes de 2px, barras e fundos de contraste (texto verde legivel em #7AC289);
         display: Playfair Display 700/800, 72px-104px, tracking -0.025em;
         body: Inter 400/600, 32px-42px, tracking -0.01em;
         telemetry: JetBrains Mono 500, 28px-32px, tracking 0.06em, tabular-nums;
         safe zones: conteudo dentro de 90% action-safe (96..1824 x 54..1026), textos e legendas dentro de 80% title-safe (192..1728 x 108..972), banda de legendas em y=832..962.
OBJECTS: 5 placas ilustrativas 16:9 (01_rizoma_broto.png .. 05_sucessao_perfilho.png),
         5 diagramas vetoriais SVG progressivos (escala subterranea, eixo de bracteas, vetores g vs auxina, curva C2H4 vs acucares, anel de sucessao),
         camada dedicada de legendas sincronizadas (compositions/captions.html).
MOTION:  power4.out / expo.out (0.28s-0.45s) em entradas; power2.inOut para camera lenta (scale/pan); power3.in (0.18s) em saidas.
         Variacao de entradas por cena: sem fade+slide repetitivo; titulos imoveis apos o pouso.
SHOTS:   Cena 01 (~0-12s): Rizoma e Broto Espadim — frame 0 ja povoado, push-in lento, escala de profundidade animada.
         Cena 02 (~12-24s): Diferenciacao Floral e Mangara — split esquerdo 60% por cortina vertical clip-path + arcos de bracteas em sequencia.
         Cena 03 (~24-36s): Partenocarpia e Geotropismo Negativo — placa ancorada a direita + vetores de gravidade vs curvatura de auxina (+135 deg).
         Cena 04 (~36-48s): Climaterio, Etileno C2H4 e Conversao Amido->Acucares — faixa panoramica widescreen + grafico bifasico e medidor numerico.
         Cena 05 (~48-60s): Senescencia, Corte e Sucessao — pull-out revelador + anel de ciclo perpetuo + tese final imovel nos ultimos 2.5s.
BANNED:  Fundo preto vazio com elementos minusculos no centro; neon/glow/particulas decorativas; gradientes roxo/azul IA;
         capsulas rounded-full em texto; sparkles; cantoneiras/HUD decorativo; grids simetricos de 3 cards;
         texto menor que 28px em leitura; frame 0 preto; loops infinitos de flutuacao em titulos; emojis.
QA:      npx hyperframes check --json (0 erros); snapshots no meio de cada uma das 5 cenas + check visual via read_file;
         ffprobe no MP4 final (1920x1080, 30fps, 59.5-60.5s, audio valido); ffmpeg volumedetect (nao-mudo).
