---
name: minecraft-builder
description: Use when the user asks to build, construct, or place structures in a Minecraft Java Edition save/world - houses, skyscrapers, castles, pixel art, or any block-based construction
---

# Minecraft Builder

Build structures in Minecraft Java Edition saves by programmatically placing blocks with Python + amulet-core.

## When to Use

- User asks to build/construct anything in a Minecraft world
- User asks to modify terrain or place blocks in a save
- User mentions building a house, tower, castle, farm, etc. in Minecraft

## Prerequisites

```bash
pip3 install amulet-core amulet-nbt nbtlib
```

Default save path on macOS:
```
~/Library/Application Support/minecraft/saves/<world_name>/
```

## Quick Reference

| Helper | Purpose |
|--------|---------|
| `open_world(path)` | Open save, returns level |
| `get_player_pos(level)` | Returns `{x, y, z, dimension}` |
| `place_block(level, x,y,z, dim, ver, name, props)` | Place one block |
| `build_box(…, hollow=True)` | Solid or hollow box |
| `build_walls(…, wall, corner)` | Four walls with optional corner material |
| `build_floor(…, checkerboard=block2)` | Flat floor, optional checkerboard |
| `place_door(…, material, facing)` | Two-block door |
| `place_bed(…, facing, color)` | Two-block bed |
| `build_simple_house(…)` | Preset: oak cabin with furniture |
| `build_skyscraper(…)` | Preset: glass curtain wall tower |
| `save_and_close(level)` | Save and close |

## Core Pattern

```python
import sys
sys.path.insert(0, "/Users/pofice/.claude/skills/minecraft-builder")
from mc_builder import *

save_path = "~/Library/Application Support/minecraft/saves/WORLD_NAME"
level = open_world(os.path.expanduser(save_path))
player = get_player_pos(level)
dim = player["dimension"]
ver = ("java", (1, 21, 0))

# Build near player
bx, by, bz = player["x"] + 5, player["y"], player["z"]

# --- place blocks here ---
place_block(level, bx, by, bz, dim, ver, "stone")
build_box(level, bx, by, bz, bx+10, by+5, bz+10, dim, ver, "oak_planks", hollow=True)

save_and_close(level)
```

## Block Properties

Blocks with state need a properties dict. Common ones:

```python
# Stairs
{"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"}
# Door
{"half": "lower", "facing": "west", "hinge": "left", "open": "false", "powered": "false"}
# Slab
{"type": "top", "waterlogged": "false"}  # or "bottom" or "double"
# Furnace/Chest
{"facing": "west", "lit": "false"}  # furnace
{"facing": "west", "type": "single", "waterlogged": "false"}  # chest
# Bed
{"facing": "east", "part": "foot", "occupied": "false"}  # + "head" for other half
# Axis blocks (logs, pillars)
{"axis": "y"}  # or "x" or "z"
```

## Building Custom Structures

For anything beyond presets, compose with primitives:

1. **Always backup first:** `cp -r saves/world saves/world_backup`
2. **Open world** → **get player pos** → **calculate offsets**
3. **Build bottom-up:** foundation → floor → walls → interior → roof → decoration
4. **Save and close**

When building complex structures, use loops and math:

```python
# Circular tower
import math
radius, height = 5, 20
cx, cz = bx + radius, bz + radius
for y in range(by, by + height):
    for angle in range(360):
        rad = math.radians(angle)
        x = cx + int(radius * math.cos(rad))
        z = cz + int(radius * math.sin(rad))
        place_block(level, x, y, z, dim, ver, "stone_bricks")
```

## Common Mistakes

- **Game open while editing:** Close Minecraft before running. amulet writes to region files directly.
- **Wrong dimension string:** Use `"minecraft:overworld"`, `"minecraft:the_nether"`, `"minecraft:the_end"`.
- **Forgetting save_and_close:** Changes are lost without it.
- **Building at player feet:** Offset by at least 3-5 blocks so the player isn't trapped inside.
- **Block name typos:** Use Minecraft wiki IDs like `"oak_planks"`, not `"oak_plank"`.
