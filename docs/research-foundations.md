# Research foundations

Agentic does not try to reproduce every agent paper or maximize benchmark
features. It applies a compact set of findings that improve reliability without
requiring a large model, a vector database, or always-on cloud services.

## Evidence translated into the runtime

| Research | Useful finding | Agentic implementation |
| --- | --- | --- |
| [ReAct](https://arxiv.org/abs/2210.03629) | reasoning is more grounded when interleaved with environment actions and observations | one validated action per cycle, followed by a fresh symbolic observation |
| [Reflexion](https://arxiv.org/abs/2303.11366) | verbal feedback from failed attempts can improve the next attempt without weight updates | a bounded episodic reflection buffer carries recent failures into the next decision |
| [MemGPT](https://arxiv.org/abs/2310.08560) | tiered memory preserves useful context under a limited context window | short recent trajectories, temporary reflections, and separately persisted explicit user feedback |
| [Voyager](https://arxiv.org/abs/2305.16291) | reusable, interpretable skills plus execution feedback improve transfer | task-selected Markdown skills with a strict prompt budget |
| [Toolformer](https://arxiv.org/abs/2302.04761) | smaller models benefit from explicit tool APIs and demonstrations | a small typed action vocabulary, few-shot examples, and bounded arguments |
| [OSWorld](https://arxiv.org/abs/2404.07972) | computer agents struggle with GUI grounding and need execution-based verification | OCR/symbolic UI state, screen-change detection, repeat blocking, and post-action observation |
| [AgentDojo](https://arxiv.org/abs/2406.13352) | content returned by tools can contain indirect prompt injections | screen, DOM, OCR, and extracted text are labeled untrusted; typed tools and allowlists remain authoritative |
| [MobileLLM](https://arxiv.org/abs/2402.14905) | sub-billion and small models can perform useful API calling when the interface is constrained | concise prompts, limited skills, deterministic retrieval, and no extra model call unless JSON repair is needed |
| [Phi-3](https://arxiv.org/abs/2404.14219) and [Qwen2.5](https://arxiv.org/abs/2412.15115) | capable small models make on-device use practical | configurable Ollama models with a 3B default and documented upgrade path |

The implementation deliberately avoids hidden chain-of-thought storage,
unbounded autonomous self-modification, executable downloaded skills, and a
large always-on retrieval stack. Those choices reduce memory use and make the
system easier to inspect.

## Current limitations

- OCR grounding is less reliable than accessibility-tree or strong vision-model
  grounding.
- Reflection helps recovery but does not guarantee correct planning.
- Prompt-level injection guidance is defense in depth, not a security boundary;
  typed actions and allowlists are the boundary.
- Hardware claims need reproducible measurements on multiple machines. The
  repository therefore describes the 3B profile as a recommended starting point,
  not a universal performance guarantee.

## Evaluation direction

Future releases should measure task completion, unsafe-action rejection,
recovery after a failed action, peak memory, startup time, and first-token
latency. Computer-use quality should be evaluated by resulting state, not by
matching one expected click sequence.
