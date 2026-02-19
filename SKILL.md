---
name: minecraft-builder
description: Use when the user asks to build, construct, or place structures in a Minecraft Java Edition save/world - houses, skyscrapers, castles, airports, villages, pixel art, terrain modification, or any block-based construction
---

# Minecraft Builder

Build structures in Minecraft Java Edition saves by programmatically placing blocks with Python + amulet-core.

## When to Use

- User asks to build/construct anything in a Minecraft world
- User asks to modify terrain, clear trees, flatten land
- User mentions building a house, tower, castle, farm, village, airport, etc.

## Prerequisites

```bash
pip3 install amulet-core amulet-nbt nbtlib
```

## Quick Start

```python
import sys
sys.path.insert(0, "/Users/pofice/.claude/skills/minecraft-builder")
from mc_builder import *

# One-line setup: open world + player pos + auto version detect + auto backup
level, player, dim, ver = quick_setup("WORLD_NAME")
bx, by, bz = player["x"] + 5, player["y"], player["z"]

# ... build here ...

save_and_close(level)
```

`quick_setup(name)` handles: resolve save path by name, auto backup, detect game version, get player position. No more hardcoding `("java", (1, 21, 0))` or full save paths.

## API Reference

### Setup & Save

| Function | Purpose |
|----------|---------|
| `quick_setup(save_name)` | One-line init: returns `(level, player, dim, ver)` |
| `open_world(path, auto_backup=True)` | Open save with auto backup |
| `save_and_close(level)` | Save and close |
| `detect_version(level)` | Auto-detect game version from level.dat |
| `get_player_pos(level)` | Returns `{x, y, z, dimension}` |

### Terrain Tools

| Function | Purpose |
|----------|---------|
| `flatten_area(level, x1,z1, x2,z2, y, dim, ver)` | Flatten area to height, fill underground, clear above |
| `clear_vegetation(level, x1,z1, x2,z2, y_base, dim, ver)` | Remove trees/plants above ground |
| `scan_terrain(level, cx,cz, dim, ver, radius)` | Scan terrain heights, returns `{(x,z): y}` |
| `get_terrain_bounds(height_map)` | Get `(min_x, max_x, min_z, max_z, min_y, max_y)` |

### Building Primitives

| Function | Purpose |
|----------|---------|
| `place_block(…, block_name, props)` | Place one block (auto-corrects common name typos) |
| `get_block(level, x,y,z, dim, ver)` | Read block at position |
| `build_box(…, hollow=False)` | Solid or hollow box |
| `build_walls(…, wall, corner)` | Four walls with corner material |
| `build_floor(…, checkerboard=block2)` | Floor with optional checkerboard |
| `build_circle(…, radius, fill=False)` | Horizontal circle (ring or disk) |
| `build_cylinder(…, radius, hollow=True)` | Vertical cylinder |
| `build_cone(…, radius, height)` | Cone / conical roof |
| `build_arch(…, z1, z2, height)` | Arch gate along z-axis |
| `build_pitched_roof(…, axis)` | Sloped stair/slab roof |

### Furniture & Decoration

| Function | Purpose |
|----------|---------|
| `place_door(…, material, facing)` | Two-block door |
| `place_bed(…, facing, color)` | Two-block bed |
| `place_windows(…, spacing, glass)` | Windows along walls |
| `place_lantern_post(…, height)` | Fence post + lantern |
| `place_tree(…, trunk, leaves)` | Simple tree |
| `build_path(…, width, block)` | Dirt path between two points |

### Preset Buildings

| Function | Purpose |
|----------|---------|
| `build_simple_house(…)` | Oak cabin with furniture |
| `build_skyscraper(…, floors)` | Glass curtain wall tower |
| `build_cottage(…, wall, roof, facing)` | Cottage with chimney, customizable materials |
| `build_windmill(…, height, radius)` | Windmill with blades |
| `build_farm(…, crops)` | Fenced farmland with water channels |
| `build_dock(…, length, width)` | Wooden pier extending over water |

## Block Name Auto-Correction

Common mistakes are auto-fixed: `tulip_red`→`red_tulip`, `oak_plank`→`oak_planks`, etc. See `BLOCK_ALIASES` dict in mc_builder.py.

Constants available: `FLOWERS` (list of valid flower names), `POTTED_FLOWERS`.

## Block Properties Cheatsheet

```python
# Stairs
{"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"}
# Door
{"half": "lower", "facing": "west", "hinge": "left", "open": "false", "powered": "false"}
# Slab
{"type": "top", "waterlogged": "false"}
# Fence
{"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"}
# Axis blocks (logs, pillars)
{"axis": "y"}
# Campfire
{"facing": "north", "lit": "true", "signal_fire": "false", "waterlogged": "false"}
```

## Building Workflow

1. `quick_setup()` — auto backup + player pos + version
2. `scan_terrain()` / `flatten_area()` — understand and prepare terrain
3. Build bottom-up: foundation → floor → walls → interior → roof → decoration
4. `level.save()` periodically for large builds
5. `save_and_close(level)` when done

## Common Mistakes

- **Game open while editing:** Close Minecraft first. amulet writes to region files directly.
- **Wrong dimension string:** Use `"minecraft:overworld"`, `"minecraft:the_nether"`, `"minecraft:the_end"`.
- **Forgetting save_and_close:** Changes are lost.
- **Building at player feet:** Offset by 3-5+ blocks.
- **Large builds without periodic save:** Call `level.save()` every few thousand blocks to avoid data loss on error.
