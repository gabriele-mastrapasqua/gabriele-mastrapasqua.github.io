---
title: "Qwen-TTS: Text-to-Speech inference in pure C"
date: 2026-03-09
description: I built a pure C inference engine for Qwen3-TTS, running text-to-speech on CPU with no Python dependencies
---

![Qwen-TTS cover image](/static/qwen-tts-cover.png)

I've been working on a fun side project: a **pure C inference engine** for [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice), Alibaba's open-source text-to-speech model. The goal was simple — run high-quality TTS on CPU, with zero Python dependencies, inspired by [antirez's](https://github.com/antirez) approach to minimal C implementations.

## Why pure C?

The official Qwen3-TTS runs on PyTorch with the usual stack of transformers, tokenizers, and CUDA. That's fine for a GPU server, but I wanted something that runs anywhere — a single binary, no runtime dependencies, just mmap the model weights and go.

## The architecture

Qwen3-TTS is a three-stage pipeline:

1. **Talker** — a causal Qwen3 LLM (0.6B or 1.7B params) that generates discrete audio tokens from text
2. **Code Predictor** — a smaller transformer that runs 15 sequential passes per audio frame, filling in the remaining codebook entries
3. **Speech Decoder** — a causal ConvNet that upsamples the discrete tokens to 24kHz audio waveforms

Each stage had to be reimplemented from scratch in C: attention with GQA and RoPE, SwiGLU activations, RMS normalization, the full ConvNet decoder with Snake activations and residual blocks.

## BF16 weights, float32 compute

The model weights are stored in bfloat16. Rather than quantizing further, I keep them as bf16 and convert on the fly during computation. On Apple Silicon, the bf16-to-f32 conversion is essentially free (it's just a left shift), and this approach gives bit-identical results to the Python reference.

I did experiment with INT4 quantization, but for the 0.6B model the matrices are too small to be bandwidth-bound — the Q4 unpack overhead actually made it **20% slower**.

## Performance

On Apple Silicon (M-series, 4 threads), the engine runs at about **0.6-0.7x realtime** — meaning a 10-second clip takes roughly 15 seconds to generate. The bottleneck is the Code Predictor at ~55% of total time, since it needs 15 sequential forward passes per frame.

Key optimizations that got me there:

- NEON-optimized bf16 matrix-vector products with multi-row fusion
- Fused gate+up projections for SwiGLU
- Unified QKV dispatch to reduce threading overhead
- im2col + BLAS sgemm for the ConvNet decoder
- 4-thread dispatch_apply (sweet spot — 8 threads hit the memory bandwidth ceiling)

## Bit-identical to Python

One thing I'm particularly happy about: with greedy decoding (temperature=0), the C implementation produces **bit-identical output** to the Python reference. This was verified step by step — embeddings, logits, codebook tokens, and final audio all match exactly.

## What's next

The speech decoder is fully causal, which means **streaming output** is possible — generating audio chunks as frames are decoded, without waiting for the full sequence. That's the next thing I want to tackle.

The code is on GitHub: [gabrielemastrapasqua/qwen-tts](https://github.com/gabrielemastrapasqua/qwen-tts)
