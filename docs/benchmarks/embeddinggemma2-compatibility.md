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
contains Torch 2.14.1, Transformers 5.19.0, SentenceTransformers 6.1.0,
Safetensors 0.8.0, and Hugging Face Hub 1.33.0. That runtime reports MPS
available, and SentenceTransformer exposes the `model_kwargs` argument used for
selective encoder configuration. No global or repository dependencies were
installed.

The complete pinned snapshot was downloaded explicitly outside Git. After fixing
SentenceTransformer's top-level config_kwargs and installing the processor's Pillow
and torchvision dependencies, real offline MPS and CPU adapter inference passed.
The adapter explicitly normalizes finite nonzero host vectors after model inference.
Raw reproducible three-sample smoke reports are embedding-mps.json and
embedding-cpu.json in this directory; these are synthetic compatibility inputs,
not a relevance benchmark or a representative performance study.

Executed in a contained Python 3.11 environment:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RESEARCHOS_EMBEDDING_DEVICE=mps python -m backend.embeddings.benchmark --repeat 3
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 RESEARCHOS_EMBEDDING_DEVICE=cpu python -m backend.embeddings.benchmark --repeat 3
```

A standard-library exact cosine index stores title and available source abstract
vectors with the pinned manifest and a complete catalog digest. Builds replace the
index atomically; failed builds preserve the previous file. Corpus/model/prompt/
dimension/normalization mismatch blocks dense access. The small-corpus scan returns
all ranked IDs before hard filtering; no labeled retrieval-quality claim is made.

Workers stopped when their account usage limit was reached; the lead completed
these runtime corrections and executed the compatibility probes.

## Sources

- [Publisher model card](https://huggingface.co/google/embeddinggemma-2)
- [Immutable model configuration](https://huggingface.co/google/embeddinggemma-2/tree/914f7f89142e33e77833254d9c9b90c3cef7303b)
- [Transformers EmbeddingGemma 2 documentation](https://huggingface.co/docs/transformers/model_doc/embedding_gemma2)
