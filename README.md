ChaosDefense

A minimalist yet engaging Tower Defense game built with Python and the Arcade library. The core innovation is an adaptive enemy AI that learns from player strategies and procedurally generated levels with distinct environmental styles.
Core Concept

"ChaosDefense" is a single-player Tower Defense game where players build defenses to protect their base from waves of enemies. The key differentiator is the enemy AI, which dynamically adjusts its pathfinding and wave composition based on the player's defensive setup and the outcomes of previous waves within the current game session.
Key Features

    Adaptive Enemy AI: Enemies employ a heuristic-based system to evaluate path effectiveness after each wave, adjusting future waves to exploit weaknesses.

    Procedural Level Generation: Levels are generated programmatically at the start of each game, adhering to specific stylistic themes (e.g., "Forest", "Rocky").

    Dynamic Economy & Upgrades: Earn resources by defeating enemies to build, upgrade towers, and purchase game-wide enhancements.

    Minimalist Aesthetics: Focus on clean, functional, and clear geometric visuals over high-fidelity art.

    Clean Architecture: A strict separation between game logic (headless) and rendering (Arcade).

Project Structure

.
├── assets/
│   ├── fonts/
│   ├── sounds/
│   └── sprites/
├── config/
│   ├── enemy_types.json
│   ├── game_settings.json
│   ├── level_styles.json
│   ├── tower_types.json
│   └── upgrade_definitions.json
├── game_ai/
├── game_logic/
│   ├── entities/
│   └── pathfinding/
├── level_generation/
├── rendering/
└── main.py
