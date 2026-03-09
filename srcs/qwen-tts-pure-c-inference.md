---
title: "Qwen-TTS: Text-to-Speech inference in pure C"
date: 2026-03-09
description: A pure C inference engine for Qwen3-TTS with streaming, HTTP server, voice cloning, and more — no Python needed
---

![Qwen-TTS cover image](/static/qwen-tts-cover.png)

I built a **pure C inference engine** for [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice), Alibaba's open-source text-to-speech model. The goal: run high-quality multilingual TTS on CPU, with zero Python dependencies, inspired by [antirez's](https://github.com/antirez) approach to minimal C inference engines (specifically his [qwen-asr](https://github.com/antirez/qwen-asr) project). The code is on GitHub: [gabriele-mastrapasqua/qwen3-tts](https://github.com/gabriele-mastrapasqua/qwen3-tts).

What started as a "let's just get the basic pipeline working" turned into a full-featured TTS engine with streaming output, an HTTP server, voice cloning, and custom voice design — all in a single C binary.

## Why pure C?

The official Qwen3-TTS runs on PyTorch with the usual stack of transformers, tokenizers, and CUDA. That's fine for a GPU server, but I wanted something that runs anywhere — a single binary, no runtime dependencies, just mmap the model weights and go.

The result: `make blas`, point it at a model directory, and you get a ~200KB binary that does everything.

## The architecture

Qwen3-TTS is a three-stage pipeline:

1. **Talker** — a 28-layer causal Qwen3 LLM (0.6B or 1.7B params) with GQA, RoPE, and SwiGLU that generates discrete audio frame tokens from text
2. **Code Predictor** — a 5-layer transformer that runs 15 sequential passes per frame, filling in the remaining codebook entries
3. **Speech Decoder** — a causal ConvNet with Snake activations, ResBlocks, and 480x upsampling that converts discrete codes to 24kHz audio

Each stage was reimplemented from scratch in C. The model supports 9 preset voices, 10 languages, and both 0.6B and 1.7B model sizes (auto-detected from weights).

## BF16 weights, float32 compute

The model weights are stored in bfloat16 and memory-mapped directly from standard HuggingFace safetensors files. On Apple Silicon, bf16-to-f32 conversion is essentially free (it's just a left shift), and this approach gives **bit-identical results** to the Python reference with greedy decoding.

I did experiment with INT4 quantization, but for the 0.6B model the matrices are too small to be bandwidth-bound — the Q4 unpack overhead actually made it **20% slower**. BF16 turned out to be the sweet spot.

## Streaming output

The speech decoder is fully causal (no lookahead), which made streaming architecturally possible. The engine generates N frames, decodes a chunk through the speech decoder, and writes audio immediately — no need to wait for the full sequence.

```bash
# Pipe raw PCM to an audio player for real-time playback
./qwen_tts -d qwen3-tts-0.6b --text "Hello world" --stdout | \
    play -t raw -r 24000 -e signed -b 16 -c 1 -
```

First audio arrives within ~1 second. The speech decoder uses incremental decoding with KV caching, so each streaming chunk is O(chunk_size) rather than re-processing the full sequence.

## HTTP server

The engine includes an embedded HTTP server — no nginx, no FastAPI, just start it and send requests:

```bash
# Start server (model loaded once, shared across requests)
./qwen_tts -d qwen3-tts-0.6b --serve 8080

# Generate speech
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","speaker":"ryan","language":"English"}' \
  -o output.wav
```

It also has an **OpenAI-compatible endpoint** (`/v1/audio/speech`) so you can use it as a drop-in replacement for OpenAI's TTS API in existing apps, plus a streaming endpoint that sends chunked PCM as it generates.

## Voice cloning

Using the Base model variant, you can clone any voice from a few seconds of reference audio:

```bash
./qwen_tts -d qwen3-tts-0.6b-base --text "Hello, this is my cloned voice." \
    --ref-audio reference.wav -o cloned.wav
```

Under the hood, this runs a full ECAPA-TDNN speaker encoder to extract a 1024-dim speaker embedding from the reference audio's mel spectrogram. You can save and reload embeddings to avoid re-extracting:

```bash
# Extract and save
./qwen_tts -d qwen3-tts-0.6b-base --text "Hello" \
    --ref-audio ref.wav --save-voice my_voice.bin -o out.wav

# Reuse later (instant)
./qwen_tts -d qwen3-tts-0.6b-base --text "Another sentence" \
    --load-voice my_voice.bin -o out2.wav
```

The speech tokenizer encoder (Mimi-based, with 4-stage strided convolutions, 8-layer transformer, and split RVQ quantization) was also implemented for the full ICL mode.

## VoiceDesign

The 1.7B VoiceDesign model can create entirely new voices from natural language descriptions:

```bash
./qwen_tts -d qwen3-tts-voice-design -l English \
    --instruct "A deep male voice with a British accent, speaking slowly and calmly" \
    --text "Hello, this is a test." -o british.wav
```

No reference audio needed — just describe what you want.

## Style and emotion control

The 1.7B CustomVoice model supports an `--instruct` flag to control speaking style:

```bash
./qwen_tts -d qwen3-tts-1.7b --text "I cannot believe you did that." \
    --instruct "Speak in a very angry and aggressive tone" -o angry.wav

./qwen_tts -d qwen3-tts-1.7b --text "I cannot believe you did that." \
    --instruct "Speak very slowly and softly, in a sad whisper" -o whisper.wav
```

Same text, completely different delivery.

## Performance

On Apple Silicon (M-series, 4 threads):

| Model | Speed | Per-frame |
|-------|-------|-----------|
| 0.6B | ~0.7-0.86x realtime | Talker 24ms + CP 70ms |
| 1.7B | ~0.48x realtime | Talker 92ms + CP 75ms |

The bottleneck is the Code Predictor — 15 sequential autoregressive passes per frame, no way around it.

Key optimizations:

- **NEON-optimized bf16 matvec** with multi-row fusion (2-row fused dispatch)
- **Fused gate+up projections** for SwiGLU in both Talker and Code Predictor
- **Unified QKV dispatch** to reduce threading overhead
- **NEON kernels** for RMSNorm, attention (dot+V accum), RoPE, Snake activation
- **Fused argmax+matvec** in the Code Predictor hot loop
- **im2col + BLAS sgemm** for the ConvNet decoder, with tiling for large sequences
- **Incremental speech decoder** with KV cache for streaming
- **4-thread dispatch_apply** (sweet spot — 8 threads hit the memory bandwidth ceiling)

Starting from ~0.4x realtime pre-optimization, these brought the 0.6B model to ~0.86x realtime.

## The Metal GPU detour

I implemented a full Metal GPU backend — compute shaders, GPU-side transformer, the works. The result? **~1.3x slower** than the optimized NEON CPU path. On Apple Silicon, CPU and GPU share the same memory bus, so there's no bandwidth advantage. The NEON path was already near-optimal for these model sizes. Deleted the whole thing.

## The debugging journey

Getting bit-identical output required tracking down some non-obvious issues:

- The model config says `"interleaved": true` for RoPE, but the Python code actually uses NeoX split-half rotation (the opposite!)
- The Code Predictor's first codebook uses the *Talker's* codec embedding, not its own
- Snake activations store alpha and beta in **log space** — `sin²(exp(alpha) * x)`, not `sin²(alpha * x)`
- All convolutions in the speech decoder are causal (left-only padding), including transposed convolutions
- ResBlock dilations are [1, 3, 9], not [1, 1, 1] as you might assume
- The 1.7B model needs a projection layer (2048→1024) between the Talker and Code Predictor that isn't in the 0.6B

Each of these was a "why doesn't my output match?" rabbit hole. The final validation: correlation 0.999996 with the Python reference across the full pipeline.

## What it looks like

```bash
# Build
make blas

# Basic usage
./qwen_tts -d qwen3-tts-0.6b --text "Hello, how are you?" -o hello.wav

# Stream to speaker
./qwen_tts -d qwen3-tts-0.6b --text "Hello world" --stdout | \
    play -t raw -r 24000 -e signed -b 16 -c 1 -

# Start HTTP server
./qwen_tts -d qwen3-tts-0.6b --serve 8080
```

The project supports macOS (ARM/x86), Linux (ARM/x86), and Windows via WSL2. NEON and AVX SIMD paths are included. The 0.6B model needs ~3 GB of memory, the 1.7B needs ~8 GB.

The code is on GitHub: [gabriele-mastrapasqua/qwen3-tts](https://github.com/gabriele-mastrapasqua/qwen3-tts)
