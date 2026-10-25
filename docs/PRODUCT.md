# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Owners of an AULA F75 / F75 Pro keyboard on Windows, connected through the 2.4G dongle. First the author themself, then friends and other AULA owners it gets shared with. They are not developers: they installed a keyboard, found the official software's lighting limited (single-color effects only), and want their own multi-color animations. The primary job is tinkering: picking and tuning effects, colors, speed and size until the keyboard looks right, then leaving it running.

## Product Purpose
AULA RGB Studio drives the keyboard's lighting from the computer: it streams per-key animations the firmware cannot do on its own (any number of colors, particles, typing-reactive effects), and edits what is stored in the keyboard's memory (built-in effects, their 7-color palettes, a static per-key picture). Success: a non-technical owner gets a beautiful, smooth animation on their keyboard within a minute, and can shape it to their taste without fear of breaking anything.

## Positioning
An unofficial, reverse-engineered alternative to AULA's own software that does what the official app cannot: multi-color live animations, scenes, per-key pictures, and per-effect palettes, with a live preview that shows exactly what the keyboard displays.

## Operating Context
- Runs as a small local Python program (`server.py`, started by `AULA RGB Studio.bat`, optionally with Windows autostart); the page is served from it at http://127.0.0.1:8777/ and talks to it over a local API.
- Animations keep playing with the browser closed; the page is opened to choose and tune, then closed.
- Keyboard limits that shape the UI: about 11 distinct colors per frame, ~14 frames/s, the keyboard sleeps after an idle timeout, live frames are lost ~2 s after the program stops.

## Capabilities and Constraints
- Live: 19 effects (fields, particles, fire, typing-reactive), 16 color themes, editable custom colors (2–6), speed, pattern size, brightness, particle amount, direction, 16 one-click scenes (effect + theme + settings).
- Keyboard memory: read current mode, battery, sleep timer; edit each of 16 firmware effects (brightness 0–9, speed 0–4, one of 7 palette colors or multi); write a per-key static picture; automatic backup, download/restore.
- Diagnostics: connection test, log.
- UI language: Russian.
- Windows only; F75 over the 2.4G dongle only (wired and Bluetooth not supported).

## Brand Commitments
Name: "AULA RGB Studio". Unofficial; must not use AULA's logo or imply it is official software.

## Evidence on Hand
No screenshots, testimonials or user counts exist; do not invent any. The keyboard is a black body with a gradient to grey.

## Product Principles
1. The keyboard is the hero: the preview mirrors the real keyboard, and every choice shows on it immediately.
2. Safe to tinker: writes to keyboard memory are reversible (backup first) and clearly separated from live play.
3. Plain words over protocol words: no packets, frames or hex in the main flow; diagnostics live apart.
4. Shareable: a stranger with the same keyboard can start without instructions from the author.
