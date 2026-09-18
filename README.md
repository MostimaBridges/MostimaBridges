<!--
  MAINTAINING THIS FILE
  =====================
  * Every image is self-hosted under assets/. Only the typing subtitle and the
    GitHub badge are third-party; if either disappears the page still reads
    correctly, because the same information is in the prose.
  * Dark/light switching uses <picture> + prefers-color-scheme with the LIGHT
    variant as the plain <img> fallback, so clients that ignore the media query
    (notably the GitHub mobile app) land on the default theme rather than a
    dark poster on a white page.
  * Markdown inside <div align="center"> IS parsed by GitHub, because a
    CommonMark HTML block ends at a blank line. Keep those blank lines. Never
    put markdown inside <p align="center">: the <p> closes at the first blank
    line and the content falls out of the centring.
  * Assets are committed to this repo, so they are served straight from
    raw.githubusercontent.com and are NOT proxied through GitHub's camo cache.
    Push the new file and it appears; there is no long-lived cache to bust.
  * The article column measures 846 CSS px on desktop, so every asset is
    1692 px wide — exactly 2x — and its type is sized in display pixels then
    doubled. Keep that ratio when regenerating.
  * GitHub puts a pause control on animated images, so the snake is generated
    with a complete first frame.
  * Regenerate artwork:  python scripts/build_assets.py
  * Validate the page:   python scripts/check_readme.py
-->

<!-- ============================== HERO ============================== -->
<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero/hero-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero/hero-light.webp" />
  <img src="./assets/hero/hero-light.webp" width="100%"
       alt="MostimaBridges title card: AI / LLM systems, local + cloud inference, full-stack services — set over key art of a silver-haired figure with a scythe before a crimson moon." />
</picture>

**Strands** · [@MostimaBridges](https://github.com/MostimaBridges)

把 AI 系统从模型接口一路做到能上线 —— 多 Provider 编排、本地推理、后端服务、前端与部署。
**AI systems, end to end — provider orchestration, local inference, backend services, frontend, deployment.**

<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=18&duration=2800&pause=900&color=FF4D7E&center=true&vCenter=true&width=880&height=44&lines=Multi-provider+LLM+routing+%2F+cloud+fallback+%2B+local+GGUF%3BResilience%3A+circuit+breaking%2C+capacity+queues%2C+quota+ledgers%3BStreaming+state+machines+%2B+structured-output+contracts%3BPhoto+to+validated+circuit+graph%2C+rules+in+front+of+the+LLM%3BFastAPI+%2F+Postgres+%2F+Nginx+%2F+vanilla+JS+%2F+Vue+%2F+PyTorch" />
  <source media="(prefers-color-scheme: light)"
          srcset="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=18&duration=2800&pause=900&color=C2185B&center=true&vCenter=true&width=880&height=44&lines=Multi-provider+LLM+routing+%2F+cloud+fallback+%2B+local+GGUF%3BResilience%3A+circuit+breaking%2C+capacity+queues%2C+quota+ledgers%3BStreaming+state+machines+%2B+structured-output+contracts%3BPhoto+to+validated+circuit+graph%2C+rules+in+front+of+the+LLM%3BFastAPI+%2F+Postgres+%2F+Nginx+%2F+vanilla+JS+%2F+Vue+%2F+PyTorch" />
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=18&duration=2800&pause=900&color=C2185B&center=true&vCenter=true&width=880&height=44&lines=Multi-provider+LLM+routing+%2F+cloud+fallback+%2B+local+GGUF%3BResilience%3A+circuit+breaking%2C+capacity+queues%2C+quota+ledgers%3BStreaming+state+machines+%2B+structured-output+contracts%3BPhoto+to+validated+circuit+graph%2C+rules+in+front+of+the+LLM%3BFastAPI+%2F+Postgres+%2F+Nginx+%2F+vanilla+JS+%2F+Vue+%2F+PyTorch"
       alt="Multi-provider LLM routing with cloud fallback and local GGUF; circuit breaking, capacity queues, quota ledgers; streaming state machines and structured-output contracts; photo to validated circuit graph; FastAPI, Postgres, Nginx, vanilla JS, Vue, PyTorch." />
</picture>

</div>

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- ============================== ABOUT ============================== -->
## // ABOUT

I build AI systems end to end — the model interface, the failure handling around it, and the product on top.

Concretely: one streaming provider interface over cloud APIs and local GGUF nodes, with a circuit breaker,
bounded capacity queues, daily quota ledgers, token and cost budgets, and an ordered fallback chain behind it.
Streaming is treated as a protocol, not a pipe — metadata deltas are parsed out of the token stream so they
never leak into visible text, stored history or summaries.

Then the parts people actually touch: FastAPI services, Postgres, a hand-maintained reverse proxy, and
frontends written by hand. Separate from that, a computer-vision system that turns a photo of a classroom
circuit into a validated `nodes + edges` graph — where a deterministic rule engine, not an LLM, owns the answer.

不做"接了一个大模型"的 Demo，而是把模型、规则、结构化输出和界面做成能跑、能查、能上线的系统。

Windows-first tooling, Linux-portable services. Two systems, ~840 commits over eight months, solo.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- ========================= CURRENTLY BUILDING ========================= -->
## // CURRENTLY BUILDING

| Track | What is actually in it |
| :-- | :-- |
| **Multi-provider LLM serving** | Per-request provider resolution from a DB registry, ordered fallback with per-attempt state rebuild, circuit breaking, quota reservation/settlement, token+cost budgets |
| **Local inference nodes** | Self-hosted GGUF runtime behind the same provider interface, with layered transport attestation (listener → SSH session → data plane → runtime → models → auth → gateway) |
| **Structured-output vision** | YOLO detection plus a deterministic topology solver that abstains instead of guessing, with an optional LLM layer bound to the same JSON contract |
| **Windows-first tooling** | PyInstaller packaging, PowerShell diagnostics and rollback scripts, service/environment consoles, offline-capable delivery |

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- =========================== SELECTED WORK =========================== -->
## // SELECTED WORK

Both systems below are private repositories. The cards describe architecture and engineering practice only —
no source, endpoints, credentials or user data. Codenames are public-safe aliases.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/projects/tessera-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/projects/tessera-light.webp" />
  <img src="./assets/projects/tessera-light.webp" width="100%"
       alt="TESSERA card: multi-service AI platform. Request path from clients through a gateway and provider registry to local and cloud backends, with a circuit breaker and ordered fallback chain." />
</picture>
</p>

#### 01 · TESSERA — multi-service AI platform `private`

A multi-site web platform whose core is a home-grown LLM serving layer: three FastAPI services behind one
reverse proxy, an admin-managed provider registry, and a frontend written without a framework.

**Engineering notes**

- **Provider layer** — one async streaming interface over OpenAI-compatible cloud endpoints and a local GGUF
  runtime, normalising request, event and usage shapes. A shared client pool is keyed per endpoint/model/key;
  streaming uses two deadlines, a first-token deadline and a stream-idle timeout, so a node that accepts a
  connection and then stalls is treated differently from one that never answers.
- **Resilience with deliberate semantics** — the circuit breaker does *not* open on `BUSY` or `MODEL_LOADING`,
  because a saturated node is not a broken node. Capacity domains are bounded and emit a `queued` status to the
  client instead of failing. Daily quota uses reserve → settle → release so a crashed request cannot silently
  consume budget, and startup recovery rewrites orphaned in-flight generations and returns their reservations.
- **Streaming protocol** — an incremental parser separates hidden metadata from visible text mid-stream, with the
  parser rebuilt per provider attempt so a failed attempt cannot poison a fallback. Reasoning output is displayed
  but never persisted or replayed.
- **Persona pipeline** — canon is compiled into provider-scoped prefixes with prompt-cache-friendly stable
  prefixes first, versioned through publish / activate / approve, and gated by a blind evaluation harness whose
  release check scans for contiguous verbatim leakage from the source material.
- **Ops surface** — background retention purges, typed DB-backed runtime settings that apply without a restart,
  hand-rolled idempotent column migrations with a forward-incompatibility guard, and health probes with TTL-based
  freshness rather than per-request pings.

`Python` · `FastAPI` · `SQLAlchemy 2` · `Pydantic` · `asyncio` · `httpx` · `Postgres` · `Nginx` · `vanilla JS`

**Scale** — a production-scale Python AI platform with 60+ modules, 170+ API
endpoints, and extensive test coverage; 678 commits since January 2026.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/projects/aurora-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/projects/aurora-light.webp" />
  <img src="./assets/projects/aurora-light.webp" width="100%"
       alt="AURORA card: circuit vision and topology engine. A photo goes to a YOLO detector, then either a deterministic rule engine or an LLM layer, both emitting one nodes-and-edges JSON contract that drives a canvas, an export and a decision trace." />
</picture>
</p>

#### 02 · AURORA — circuit vision & topology engine `private`

One codebase that turns a photo of a middle-school physics circuit into a validated circuit graph. YOLO detects
components; a hand-written rule engine infers topology; an LLM is an optional semantic layer behind the same
JSON contract that feeds a desktop editor, a training toolbox, a web app and a packaged Windows build.

**Engineering notes**

- **The rule engine refuses to guess.** If any wire evidence exists, only wire-derived edges are emitted and
  templates are never consulted. A node with real geometry but no supporting evidence yields zero edges and an
  `unknown` circuit type rather than a plausible-looking invention. Every ambiguity test abstains: an ownership
  cost gap below a fixed margin returns nothing, and an orientation search that exceeds its combination budget
  gives up with the comment that an orientation must never be chosen merely because it survived a cutoff.
- **Algorithms chosen on purpose.** Wire segments are merged by union-find over a geometric join predicate that
  rejects merges crossing a component via continuous box intersection, and refuses to merge parallel wires as
  they lengthen. The series fallback builds a Prim minimum spanning tree closed into a cycle by preorder DFS —
  deliberately replacing greedy nearest-neighbour, because an MST is a 2-approximation of metric TSP and does not
  produce cross-graph flying wires. A disjoint-set validator runs on every exit path and *diagnoses* unsafe
  topology rather than silently repairing it.
- **Provenance and explainability ship with the result.** Every edge records why it exists — template match,
  wire bridge, ratio heuristic, MST fallback, dangling repair — and each stage appends a decision record, so a
  wrong answer is traceable to the branch that produced it.
- **Browser-side inference.** ONNX Runtime Web runs detection fully client-side in a web worker, preferring
  WebGPU and falling back to threaded SIMD WASM, with provider timeouts and upload pixel budgets scaled by a
  device tier. Cross-origin isolation headers are served on every response so multi-threaded WASM actually
  engages; the runtime is vendored locally for offline use.
- **Testing as a contract.** Regression cases are hand-authored at the edge level and compared as multisets that
  preserve port sides and duplicate edges, with a canonical form that treats swapping two identical resistors as
  the same topology. Seven markers are `xfail(strict=True)`, so known drift fails the suite if it silently
  disappears.

`Python` · `Ultralytics YOLO` · `PyTorch` · `ONNX Runtime` · `TensorRT` · `OpenCV` · `CustomTkinter` · `FastAPI` · `ONNX Runtime Web`

**Scale** — rule engine 2,415 lines and 71 methods in a single class; comprehensive test coverage backed by 240+ assertion-based tests, 7 of them `xfail(strict=True)` drift markers;
13 classroom-experiment presets; six delivery surfaces from one contract; 161 commits since April 2026.

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- ======================== ENGINEERING FOCUS ======================== -->
## // ENGINEERING FOCUS

Not a language list — the areas where the work actually happens.

| Area | What it means here |
| :-- | :-- |
| **AI / LLM systems** | Provider abstraction over OpenAI-compatible SSE, local GGUF via llama.cpp, streaming parsers, structured-output contracts with tolerant extraction and reparative validation, prompt/context budgeting, persona compilation, offline evaluation harnesses |
| **Backend** | FastAPI, SQLAlchemy 2, Pydantic, asyncio concurrency with per-conversation locks, JWT auth with token-version revocation, idempotent hand-rolled migrations, admission control, background task lifecycle |
| **Frontend** | Vanilla JS at scale with no framework or bundler, Vue 3 + TypeScript + Pinia + Vite, canvas editors with world/view transforms, SSE clients, responsive layout without a UI kit |
| **Vision / ML** | Ultralytics YOLO across PyTorch, ONNX Runtime and TensorRT backends, hardware-tiered inference configuration, self-healing fallback when a backend or input size mismatches, model export and precision conversion |
| **Algorithms** | Union-find clustering, Prim MST, A\* orthogonal routing, disjoint-set validation, PCA axis analysis, geometric intersection tests, custom relevance ranking with CJK bigram expansion |
| **Infrastructure** | Nginx with TLS, multi-site reverse proxying, rate-limit zones and buffering disabled for SSE; Windows service tooling; PowerShell diagnostics, deployment export and rollback |
| **Quality** | pytest across two suites, Playwright browser E2E, ruff, coverage gates, pre-commit hooks that run per-subsystem test gates, a multi-job CI workflow with a deployment-version gate |

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- ============================== STACK ============================== -->
## // STACK

Only what I have actually shipped with.

| Layer | In use |
| :-- | :-- |
| **Languages** | `Python` · `TypeScript` · `JavaScript` · `PowerShell` · `Bash` · `SQL` |
| **Backend** | `FastAPI` · `SQLAlchemy 2` · `Pydantic` · `asyncio` · `httpx` · `uvicorn` · `python-jose` |
| **Data** | `PostgreSQL` · `SQLite` · `JSON Schema` contracts |
| **AI / LLM** | OpenAI-compatible APIs · `llama.cpp` / GGUF · SSE streaming · tool calling · prompt & context budgeting |
| **Vision / ML** | `Ultralytics YOLO` · `PyTorch` · `ONNX Runtime` · `TensorRT` · `OpenCV` · OpenVINO & TFLite (export) |
| **Frontend** | `Vue 3` · `Pinia` · `Vite` · `ONNX Runtime Web` · canvas 2D · hand-written CSS |
| **Infra** | `Nginx` · TLS · reverse proxy · rate limiting · Windows services · `PyInstaller` |
| **Quality** | `pytest` · `Playwright` · `ruff` · `coverage.py` · `pre-commit` · `GitHub Actions` |

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- ============================= ACTIVITY ============================= -->
## // ACTIVITY

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/generated/snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/generated/snake-light.svg" />
  <img src="./assets/generated/snake-light.svg" width="100%"
       alt="Contribution graph for the last year, animated as a snake that eats the squares." />
</picture>
</p>

<sub>Rebuilt once a day by GitHub Actions — see [`.github/workflows/snake.yml`](.github/workflows/snake.yml).</sub>

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/ornaments/divider-dark.webp" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/ornaments/divider-light.webp" />
  <img src="./assets/ornaments/divider-light.webp" width="100%" alt="" />
</picture>
</p>

<!-- ============================= CONNECT ============================= -->
## // CONNECT

<div align="center">

<img src="./assets/misc/strand-portrait.webp" width="170"
     alt="Portrait of the artist's original character, clipped into a crimson diamond." />

Most of this work lives in private repositories. If you want to talk about multi-provider LLM serving,
local inference infrastructure, or deterministic vision-and-rules pipelines — open an issue or reach me on GitHub.

[![GitHub](https://img.shields.io/badge/GitHub-MostimaBridges-E11D5C?style=flat-square&labelColor=1A1027&logo=github&logoColor=white)](https://github.com/MostimaBridges)

<img src="./assets/icons/monogram.svg" width="34" alt="" />

</div>

<!-- ============================== FOOTER ============================== -->
<sub>
Art, project cards, dividers and the monogram are generated from
<a href="./scripts/build_assets.py">scripts/build_assets.py</a>, so the whole palette stays in one place.
The contribution snake is regenerated daily by GitHub Actions.
</sub>
