**PyTetris is a complete, from-scratch Tetris implementation in Python and Pygame. It covers two distinct game modes: a classic single-player experience and a real-time split-screen battle against an AI opponent.**
<img width="703" height="683" alt="image" src="https://github.com/user-attachments/assets/f527c18b-1fe7-46c9-82b8-f7487b210aaf" />
- **Classic Mode** implements every standard Tetris mechanic — a 7-bag randomizer to prevent piece starvation, gravity curve tied to level progression, hard and soft drop, ghost piece preview, wall kicks, and a DAS/ARR system for smooth keyboard feel. Visual polish includes per-block glow, particle drop trails, and a surface caching layer that keeps the renderer at a stable 60 FPS by turning repeated draw calls into O(1) dictionary lookups.
<img width="747" height="752" alt="image" src="https://github.com/user-attachments/assets/d7f8a97f-01e4-4756-9514-8a4951f11adc" />

- **Battle Mode** introduces a garbage line system and a heuristic AI bot with three difficulty tiers (Normal, Medium, Hard).
<img width="862" height="451" alt="image" src="https://github.com/user-attachments/assets/a3096fd1-1d4a-4e7a-8707-fd622d906313" />
- The bot uses a brute-force placement search scored against four heuristic terms — lines cleared, holes, aggregate height, and bumpiness — with optional 1-ply lookahead on the next piece. To avoid blocking the main game loop, the search runs entirely in a background daemon thread operating on a lightweight _BoardProxy snapshot, safe under CPython's GIL. A configurable mistake probability makes lower difficulty levels feel genuinely human rather than mechanically suboptimal.

  All tunable parameters — bot delays, heuristic weights, DAS/ARR timings, garbage tables — are centralized in constants.py, so difficulty balancing never requires touching game logic. A Settings singleton propagates user preferences (sound, ghost piece, glow, bot difficulty) across scenes without any explicit save/load mechanism.
<img width="1070" height="748" alt="image" src="https://github.com/user-attachments/assets/9720f32e-3e00-4df9-9615-9490bb0468af" />
