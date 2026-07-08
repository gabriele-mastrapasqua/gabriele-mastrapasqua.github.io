---
title: "Emotions on a cloned voice: a 25 MB graft, a steering vector, and mixing feelings like vectors"
date: 2026-07-08
description: How we got sad/happy/angry/fearful speech to work on cloned voices in a pure-C Qwen3-TTS engine — a 25 MB "graft" clone that keeps the emotion levers alive, a steering + fine-tune recipe (trained on the CC-BY Emozionalmente corpus) that keeps the language stable, and — because emotion is a vector — blended "dyad" emotions plus switching emotion mid-sentence from a single prompt.
---

![Emotions on a cloned voice in a pure-C TTS engine](/static/qwen-tts-emotions.png)

*How we added emotion — and then **blended** and **mid-sentence-switchable** emotion — to preset and cloned voices in a pure-C [Qwen3-TTS](https://github.com/gabriele-mastrapasqua/qwen3-tts) engine. Steering vectors, a small fine-tune on real emotional speech, and a lot of dead ends.*

## TL;DR

Qwen3-TTS ships 9 neutral preset speakers. No emotion control, and cloning a voice used to mean a huge file that couldn't emote at all. We changed all of it:

- **Small clones.** A cloned voice is now a **~25 MB `.qvoice` "graft"** — small enough to share, and built so the emotion machinery still works on it.
- **Emotions on *any* voice.** One flag — `--emotion <sad|joy|anger|fear|disgust|surprise>` — works on **presets and cloned voices**, in every supported language.
- **Mixing emotions.** Because emotion is a *direction* you can add, summing two gives a new one: seven **dyads** (`contempt`, `awe`, `nostalgia`, …) fall out for free. And you can **switch emotion mid-sentence from a single prompt** with inline `[emotion]` tags.

It's all pure C, CPU by default. Getting there took an embarrassing number of dead ends — this is the honest map of what failed and what finally worked.

## Why emotion on a clone is hard

The neutral clone is the easy part: feed ~30 seconds of audio, an ECAPA-TDNN encoder extracts a speaker embedding, and the model reproduces the timbre. But that clone is **frozen and flat** — the right voice, no feeling.

Two forces fight you when you add emotion to a clone:

1. **Emotion and timbre live in the same weights.** Push the model toward "angry" and the timbre drifts — you get an angry *stranger*, not an angry *you*.
2. **A cheap clone throws away the levers.** The smallest clone formats (a 4 KB x-vector, a KV-cache prefix) bolt a voice onto the model but lose the internal state the emotion tools need to hook into.

So the clone format and the emotion method are not independent problems. They have to be designed together.

## The 25 MB graft: small *and* emotable

We landed on a **graft** `.qvoice` (`--icl-only`): instead of shipping a whole retrained model, it keeps the CustomVoice transformer weights and stores just the delta that makes it *your* voice. About **25 MB** — the sweet spot:

- Small enough to attach to an email or check into a repo.
- Preserves full prosody (not a lossy 4 KB summary).
- **Keeps the emotion levers alive** — because the CustomVoice weights are still present, the steering and fine-tune hooks have something to grab.

(For reference: a bit-identical clone is ~785 MB, a shareable one ~16 MB, a postcard x-vector ~4 KB — but only the graft keeps the instruct/emotion controls working. Trade-offs, all measured.)

## The graveyard of methods that didn't work

Before the recipe that ships, we tried and abandoned a lot — writing them down so nobody (including future us) re-derives them:

- **τ-vectors / task-arithmetic.** Compute an "emotion direction" by float-space arithmetic between neutral and emotional fine-tunes. Elegant on paper; muddy and timbre-shifting in the ear.
- **x-vector emotion injection.** Bolt an emotion onto the 4 KB speaker vector. Too little state to carry it.
- **Per-language dense fine-tunes.** Full FT of layers 16–26 per language. Big, brittle, and it *averaged* emotions instead of letting you select one.
- **Seed palettes.** Curate "good seeds" per emotion. Fragile and non-portable across voices.

Every one produced audio. None produced *reliable, selectable, timbre-preserving* emotion. They're archived — the useful thing they left behind is the recipe below.

## What actually works: steer for presets, COMBINE for clones

The shipped system is two hooks used together:

1. **Activation steering.** A tiny, speaker- and language-agnostic direction added to the residual stream at **layers 21–25** at inference time. It nudges "emotion" without touching timbre. Each vector is a few KB and committed to the repo.
2. **A small fine-tune on real emotional speech (`.expr`).** A LoRA-style weight-delta on a few layers, trained on the **Emozionalmente** corpus — a crowdsourced Italian emotional-speech dataset (CC-BY 4.0) by *Fabio Catania, Jordan W. Wilke & Franca Garzotto* (Politecnico di Milano), published in *IEEE Transactions on Audio, Speech and Language Processing*, 2025 ([doi:10.1109/TASLPRO.2025.3540662](https://doi.org/10.1109/TASLPRO.2025.3540662)).

A word on that dataset, because it's genuinely cool and it's *why this works*: it's a large, permissively-licensed bank of ordinary people acting the basic emotions in Italian. Real emotional prosody is exactly the *texture* a clone lacks — the steering vector can point at "sad," but without real examples the model doesn't know what sad *sounds like* for this speaker. The fine-tune supplies that. And because it's Italian, the whole Romance family (Spanish, French, Portuguese) transfers from the one pack; languages further away get their own small pack. The `.expr` packs are fetched on demand from Hugging Face ([gabrione/qwen3-tts-italian-expr](https://huggingface.co/gabrione/qwen3-tts-italian-expr), via `download_assets.sh`).

**The one rule:**

- **Preset voice → pure steering.** Clean in every language, nothing else needed.
- **Cloned voice → COMBINE** — the language `.expr` fine-tune **plus** the steering vector **plus** an English instruct prompt, applied *together*.

That "together" is the whole trick, and it's specifically what **keeps the language stable**. Pure steering pushed hard enough to *feel* emotional will, on a clone or a far language, drift the pronunciation off-manifold — anger slides the accent, a Romance vowel starts to sound wrong. The fine-tune pulls it back in-distribution: the steering vector supplies the emotional *direction*, the fine-tune supplies the *texture* and the *language anchor*, and the instruct prompt sets the *strength*. Remove any one and it degrades. Per language we tune which pack does the anchoring (native German/French where trained, the Italian pack as the cross-language stabilizer for the rest) and use the **native preset per language** under the hood (Japanese, Korean, Chinese, Romance, Russian…), so the emotion lands naturally instead of fighting the language.

The result is one flag:

```bash
# preset voice
./qwen_tts --emotion sad -s ryan -l English --text "I can't believe he's gone."

# your own 25 MB cloned voice — same flag
./qwen_tts --load-voice me.qvoice --icl-only --emotion joy -l Italian --text "Ce l'abbiamo fatta!"
```

## Mixing emotions: dyads, and switching mid-sentence

Here's the fun part. If emotion is a *direction* in activation space, then directions **add**. Take the "anger" vector and the "disgust" vector, sum them 50/50, and you get something that is neither — a coherent, recognizable **contempt**. It just works, and seven blends (Plutchik's "dyads") fall out of the six primaries we already had. The full menu:

| `--emotion` | Kind | What it is |
|---|---|---|
| `sad` · `joy` · `anger` · `fear` · `disgust` · `surprise` | primary | the six base emotions (synonyms like `happy` / `angry` work too) |
| `contempt` | dyad | anger + disgust → sneering disdain |
| `awe` | dyad | fear + surprise → hushed wonder |
| `nostalgia` | dyad | joy + sad → bittersweet fondness |
| `disapproval` | dyad | surprise + sad → let-down reproach |
| `remorse` | dyad | sad + disgust → guilty regret |
| `outrage` | dyad | anger + surprise → indignant shock |
| `despair` | dyad | fear + sad → hopeless dread |

No new training, no new capture — just a script that sums two vectors, and seven new `--emotion` values appear. (One thing the ear caught: `joy`-paired blends over-drive on long English sentences, so `nostalgia` ships 40/60 sad-leaning. Vectors add — but the mix ratio still matters.)

Then the demo that makes people lean in: **many emotions from one prompt.** Write `[emotion]` tags inline and the engine switches sentence by sentence, in a single generation, clean at the seams:

```bash
./qwen_tts -s ryan -l English --text \
  "[contempt] Oh, sure, that's a brilliant idea. [nostalgia] We used to spend every summer by the sea. [despair] And now there's nothing left."
```

One file, three emotions, no splicing — the steering vector is simply swapped per sentence while the voice stays the voice. `[neutral]` resets.

**One system, everywhere — which meant deleting our own earlier work.** We'd built an older, weaker per-sentence emotion path on a different mechanism. It's retired. Now the CLI `--emotion` flag, the inline `[emotion]` tags, *and* the HTTP server's `emotion` field all route through the **same** steering recipe — so a dyad you find on the command line behaves identically in a server request, and a REST client can stream `[joy]…[sad]…` markup and get per-sentence emotion for free. One recipe, three surfaces.

## Paralinguistics: inline events — 🧪 work in progress

Emotion is prosody; **paralinguistics** — a laugh, a sigh, a yawn — is an *event*. We ship a handful as inline tags. Each fires **in one generation, in the voice's own timbre** — no splice (a spliced laugh sounds like a *different person* laughing; the tag becomes a validated onomatopoeia *inside* the sentence instead, so it's your clone doing it):

| Tag | Event |
|---|---|
| `[laugh]` | a real chuckle |
| `[sigh]` | a sigh |
| `[yawn]` | a yawn |
| `[wow]` | a "wow!" interjection |
| `[giggle]` | a sly giggle (best on its own — pairing it with `joy` over-drives it) |
| `[scoff]` | a dismissive *tsk* |

```bash
./qwen_tts --text "That's hilarious [laugh] I can't even. [sigh] Okay, back to work."
```

**Fair warning — treat this as alpha.** It's hit-or-miss across voices and languages (laughs and sighs land best), and it's parked for now rather than under active development. But it works often enough to be fun, and it's very much worth a try: if it breaks in an interesting way on your voice or language, that's exactly the kind of bug report that makes it better. Finding a universal onomatopoeia-per-event was its own long hunt, and there's surely more to find.

## Takeaways

- **Clone format and emotion method are one problem.** The 25 MB graft exists specifically so the steering/fine-tune hooks survive.
- **One clean method beats five clever ones.** τ-vectors, x-vector emotion, dense per-language FT, seed palettes — all archived in favor of *steer + fine-tune, together*.
- **On a clone, layer the levers.** Steering *direction* + fine-tune *texture and language anchor* + instruct *strength*. Individually weak, together strong.
- **Real data is the texture.** The steering vector points at an emotion; the CC-BY Emozionalmente corpus is what teaches the model how that emotion actually *sounds*.
- **Emotion is a vector — so it composes.** Directions add (dyads) and swap per sentence (inline switching). Wire every surface — CLI, inline, server — to the *one* recipe and the feature multiplies for free.
- **Keep events in-timbre.** A spliced laugh is a stranger; an inline one is you.

It's all pure C, CPU by default, with the `.expr` packs fetched on demand from Hugging Face. Clone your voice once, then make it *feel* something — and now, feel several things in a row.

*Code: [github.com/gabriele-mastrapasqua/qwen3-tts](https://github.com/gabriele-mastrapasqua/qwen3-tts). Emotion packs: [huggingface.co/gabrione/qwen3-tts-italian-expr](https://huggingface.co/gabrione/qwen3-tts-italian-expr). Dataset: **Emozionalmente** (Catania, Wilke & Garzotto, PoliMi, CC-BY 4.0).*
