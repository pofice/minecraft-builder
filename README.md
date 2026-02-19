# Minecraft Builder

A Claude Code skill for building structures in Minecraft Java Edition saves programmatically.

## Features

- Build houses, skyscrapers, castles, airports, and any custom structure
- Automatically locate player position and build nearby
- Terrain modification (flatten, clear trees)
- Reusable building primitives (walls, floors, roofs, doors, windows, etc.)
- Preset templates for common buildings

## Requirements

```bash
pip3 install amulet-core amulet-nbt nbtlib
```

## Installation as Claude Code Skill

Copy `SKILL.md` and `mc_builder.py` to `~/.claude/skills/minecraft-builder/`:

```bash
mkdir -p ~/.claude/skills/minecraft-builder
cp SKILL.md mc_builder.py ~/.claude/skills/minecraft-builder/
```

Then in Claude Code, ask something like "help me build a castle in my Minecraft world" and the skill will be automatically triggered.

## Usage in Python

```python
import sys
sys.path.insert(0, "/path/to/minecraft-builder")
from mc_builder import *

level = open_world("/path/to/minecraft/saves/world_name")
player = get_player_pos(level)
dim = player["dimension"]
ver = ("java", (1, 21, 0))

# Build a house near the player
build_simple_house(level, player["x"] + 5, player["y"], player["z"], dim, ver)

save_and_close(level)
```

## Available Functions

| Function | Description |
|----------|-------------|
| `open_world(path)` | Open a Minecraft save |
| `get_player_pos(level)` | Get player coordinates and dimension |
| `place_block(...)` | Place a single block |
| `build_box(...)` | Build a solid or hollow box |
| `build_walls(...)` | Build four walls with optional corner material |
| `build_floor(...)` | Build a floor with optional checkerboard pattern |
| `build_pitched_roof(...)` | Build a pitched roof with stairs/slabs |
| `place_door(...)` | Place a two-block door |
| `place_bed(...)` | Place a two-block bed |
| `place_windows(...)` | Place windows along walls |
| `build_simple_house(...)` | Preset: oak cabin with furniture |
| `build_skyscraper(...)` | Preset: glass curtain wall skyscraper |
| `save_and_close(level)` | Save and close the world |

## License

MIT
