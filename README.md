# Minecraft Builder

A Claude Code skill for building structures in Minecraft Java Edition saves programmatically.

## Features

- **One-line setup**: `quick_setup("world_name")` handles save path resolution, auto backup, version detection, and player position
- **Terrain tools**: Flatten areas, clear vegetation, scan terrain heights
- **Building primitives**: Box, walls, floor, circle, cylinder, cone, arch, pitched roof
- **Furniture & decoration**: Doors, beds, windows, lantern posts, trees, paths
- **Preset buildings**: House, skyscraper, cottage, windmill, farm, dock
- **Block name auto-correction**: Common typos like `tulip_red` → `red_tulip` are fixed automatically

## Requirements

```bash
pip3 install amulet-core amulet-nbt nbtlib
```

## Installation as Claude Code Skill

```bash
mkdir -p ~/.claude/skills/minecraft-builder
cp SKILL.md mc_builder.py ~/.claude/skills/minecraft-builder/
```

Then ask Claude Code something like "help me build a castle in my Minecraft world".

## Quick Start

```python
import sys
sys.path.insert(0, "/path/to/minecraft-builder")
from mc_builder import *

# One-line setup: open world + player pos + auto version detect + auto backup
level, player, dim, ver = quick_setup("my_world")
bx, by, bz = player["x"] + 5, player["y"], player["z"]

# Use a preset
build_cottage(level, bx, by, bz, dim, ver, name="My Cottage")

# Or build custom
flatten_area(level, bx, bz, bx+20, bz+20, by, dim, ver)
build_cylinder(level, bx+10, bz+10, by, by+15, 5, dim, ver, "stone_bricks")
build_cone(level, bx+10, bz+10, by+16, 6, 5, dim, ver, "spruce_planks")

save_and_close(level)
```

## API Overview

### Setup & Save
| Function | Description |
|----------|-------------|
| `quick_setup(name)` | One-line init → `(level, player, dim, ver)` |
| `open_world(path, auto_backup=True)` | Open save with auto backup |
| `save_and_close(level)` | Save and close |
| `detect_version(level)` | Auto-detect game version |
| `get_player_pos(level)` | Get player `{x, y, z, dimension}` |

### Terrain Tools
| Function | Description |
|----------|-------------|
| `flatten_area(…)` | Flatten + fill underground + clear above |
| `clear_vegetation(…)` | Remove trees/plants |
| `scan_terrain(…)` | Height map `{(x,z): y}` |
| `get_terrain_bounds(map)` | Bounding box from height map |

### Building Primitives
| Function | Description |
|----------|-------------|
| `place_block(…)` | Place one block (auto name correction) |
| `get_block(…)` | Read block at position |
| `build_box(…, hollow)` | Solid or hollow box |
| `build_walls(…, wall, corner)` | Four walls |
| `build_floor(…, checkerboard)` | Floor with optional pattern |
| `build_circle(…, fill)` | Horizontal circle/disk |
| `build_cylinder(…, hollow)` | Vertical cylinder |
| `build_cone(…)` | Conical shape |
| `build_arch(…)` | Arch gate |
| `build_pitched_roof(…, axis)` | Sloped roof |

### Furniture & Decoration
| Function | Description |
|----------|-------------|
| `place_door(…)` | Two-block door |
| `place_bed(…)` | Two-block bed |
| `place_windows(…)` | Windows on walls |
| `place_lantern_post(…)` | Fence + lantern |
| `place_tree(…)` | Simple tree |
| `build_path(…)` | Dirt path |

### Preset Buildings
| Function | Description |
|----------|-------------|
| `build_simple_house(…)` | Oak cabin with furniture |
| `build_skyscraper(…)` | Glass curtain wall tower |
| `build_cottage(…)` | Cottage with chimney |
| `build_windmill(…)` | Windmill with blades |
| `build_farm(…)` | Fenced farmland |
| `build_dock(…)` | Wooden pier |

## CLI Usage

```bash
python3 mc_builder.py <save_name> <command> [offset]
python3 mc_builder.py test info
python3 mc_builder.py test house 5
python3 mc_builder.py test skyscraper 10
python3 mc_builder.py test cottage
python3 mc_builder.py test windmill
python3 mc_builder.py test farm
python3 mc_builder.py test dock
```

## License

MIT
