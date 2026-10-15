# EmbeddingGemma 2 compatibility record

## Source verification

Checked 2026-10-15 against Google's publisher page on Hugging Face, the live
Hugging Face model API, and the Hugging Face Transformers model documentation.

- Publisher/checkpoint: [`google/embeddinggemma-2`](https://huggingface.co/google/embeddinggemma-2)
- Immutable model revision at check: `914f7f89142e33e77833254d9c9b90c3cef7303b`
- License listed by publisher: Apache-2.0
- Model card configuration: 740M total parameters; selectively loadable 270M
  text path (130M transformer + 140M embedder), with separate vision/audio
  encoders. The current repository publishes one 1,488,915,288-byte
  `model.safetensors` file; selective loading removes unused components from
  the loaded model but does not make that source artifact a 270M download.
- Text vectors use the shared 768-dimensional output. Supported Matryoshka
  widths include 512, 256, and 128; re-normalize after truncation. This adapter
  currently fixes the contract at 768 dimensions.
- Context window: 8,192 tokens.
- Retrieval query template: `task: search result | query: {query}`.
- Titled document template: `title: {title} | text: {text}`. Empty titles use
  `title: none`.
- Hugging Face's card documents `SentenceTransformer` selective loading with
  `config_kwargs={"vision_config": None, "audio_config": None}`. It recommends
  the `SearchQuery` prompt for queries and manual title formatting for titled
  documents.

The card describes the model's evaluation results, but those figures are not
local-corpus evidence and are not treated as an MVP benchmark here.

## Runtime compatibility check

Host: Apple Silicon arm64, macOS Darwin 27.0.0, 16 GiB RAM, 50 GiB free at
inspection. Python 3.11.16 is available. The pre-existing Python 3.10.7 runtime
has Torch 2.8.0 with MPS available, Transformers 4.57.3, and no
SentenceTransformers. A separate Python 3.11 virtual environment under `/tmp`
is being used for the pinned model smoke check; no global or repository
dependencies are installed.

No local throughput, latency, peak-memory, or quality benchmark should be
claimed until the pinned model is loaded and measured with a recorded command.

## Sources

- [Publisher model card](https://huggingface.co/google/embeddinggemma-2)
- [Immutable model configuration](https://huggingface.co/google/embeddinggemma-2/tree/914f7f89142e33e77833254d9c9b90c3cef7303b)
- [Transformers EmbeddingGemma 2 documentation](https://huggingface.co/docs/transformers/model_doc/embedding_gemma2)
