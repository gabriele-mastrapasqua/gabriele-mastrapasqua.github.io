---
title: Dotfiles 2026 — Ghostty, Zed, and the joy of a modern terminal stack
date: 2026-07-21
description: My dotfiles are on GitHub, and Ghostty + Zed are the fastest, most beautiful tools I use daily.
---

I finally cleaned up my [dotfiles](https://github.com/gabriele-mastrapasqua/dotfiles) and put them on GitHub.

The stack is simple: **Ghostty** auto-starts tmux with full session persistence (resurrect + continuum), **Zed** is my editor, and Neovim lives inside tmux for when I want terminal editing. Everything is configured from a single `setup.sh` — Homebrew packages, symlinks, the works.

## Why Ghostty?

Ghostty is a native terminal emulator written in Zig. It uses the operating system's own GPU APIs directly — Metal on macOS — so rendering is instant, scrolling is buttery, and there's zero lag. It also has first-class Kitty graphics protocol support, which means things like `icat` (display images in the terminal) and Neovim image previews just work. And it supports true color, font ligatures, and custom cursor shapes out of the box. No config file parsing overhead, no Electron runtime eating your RAM. It simply renders pixels as fast as your screen can refresh.

Ghostty also starts tmux automatically with `tmux new-session -A -s main`, so every time I open a terminal window I'm right back where I left off — tmux-resurrect + continuum restore my exact session (tabs, panes, working directories, running processes). Close Ghostty, reopen it, everything is back. It's like your desktop never died.

## Why Zed?

Zed is what happens when you take the editor performance arms race to its logical conclusion. Written in Rust, GPU-accelerated, with a custom UI framework that doesn't go through the DOM. It starts in under 200ms. It loads a 10k-line file instantly. Multi-cursor editing, LSP integration, inline diagnostics, collab features — everything is reactive and instant.

It also has a killer Vim mode that actually feels like Vim (not a half-baked imitation), which is crucial for me since I spend a lot of time in Neovim too. The LSP experience is seamless: add a `Cargo.toml` dependency and Zed picks it up without a reload. The built-in terminal is there if I need it, but I mostly use Ghostty + tmux anyway.

## The combo

The real magic is how they complement each other. Ghostty is the canvas, tmux is the window manager, and Zed (or Neovim) is the tool I write code in. They're all native, all instant, all beautiful. No Electron app taking 2 seconds to cold-start. No 100MB RAM for a terminal. No 500ms between keystroke and character appearing on screen.

These tools made my daily flow genuinely more pleasant. I don't think about them — they just work.

<details>
<summary>Ghostty + tmux: macOS-style keybindings and window titles</summary>

I wanted tmux to feel as natural as macOS Terminal, so I configured Ghostty to send keystrokes that tmux understands:

- **`Cmd + T`** → `prefix + c` (new tmux tab)
- **`Ctrl + Tab`** → `prefix + n` (next tab)
- **`Ctrl + Shift + Tab`** → `prefix + p` (previous tab)

Each tmux window is automatically renamed to the basename of its working directory via a hook on `#{pane_current_path}`, so every tab shows the folder I'm working in — no more guessing.

This setup is part of my dotfiles: Ghostty maps the shortcuts, tmux handles the tab lifecycle, and the result is indistinguishable from the built-in macOS terminal tabs, but with full tmux persistence and session management underneath.

</details>

Check the repo here: [github.com/gabriele-mastrapasqua/dotfiles](https://github.com/gabriele-mastrapasqua/dotfiles)
