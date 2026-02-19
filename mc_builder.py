#!/usr/bin/env python3
"""
Minecraft Builder - 通过 amulet-core 在 Java 版存档中建造建筑。

用法:
    python3 mc_builder.py <save_path> <blueprint_json>

blueprint_json 格式见 SKILL.md
"""

import sys
import json
import os

def ensure_deps():
    """确保 amulet-core 已安装"""
    try:
        import amulet
        return True
    except ImportError:
        os.system("pip3 install amulet-core amulet-nbt")
        return True

def get_player_pos(level):
    """从 level.dat 读取玩家位置和维度"""
    import amulet_nbt
    import nbtlib

    level_path = os.path.join(level.level_wrapper.path, "level.dat")
    nbt = nbtlib.load(level_path)
    player = nbt["Data"]["Player"]
    pos = player["Pos"]
    dim = str(player.get("Dimension", "minecraft:overworld"))
    return {
        "x": int(float(pos[0])),
        "y": int(float(pos[1])),
        "z": int(float(pos[2])),
        "dimension": dim,
    }

def place_block(level, x, y, z, dimension, game_version, block_name, properties=None):
    """放置单个方块"""
    import amulet
    from amulet.api.block import Block

    props = {}
    if properties:
        for k, v in properties.items():
            props[k] = amulet.StringTag(str(v))
    block = Block("minecraft", block_name, props)
    level.set_version_block(x, y, z, dimension, game_version, block)

def build_box(level, x1, y1, z1, x2, y2, z2, dim, ver, block, props=None, hollow=False):
    """建造一个方块盒子(实心或空心)"""
    for x in range(min(x1,x2), max(x1,x2)+1):
        for y in range(min(y1,y2), max(y1,y2)+1):
            for z in range(min(z1,z2), max(z1,z2)+1):
                if hollow:
                    is_edge_x = (x == min(x1,x2) or x == max(x1,x2))
                    is_edge_y = (y == min(y1,y2) or y == max(y1,y2))
                    is_edge_z = (z == min(z1,z2) or z == max(z1,z2))
                    if not (is_edge_x or is_edge_y or is_edge_z):
                        place_block(level, x, y, z, dim, ver, "air")
                        continue
                place_block(level, x, y, z, dim, ver, block, props)

def build_walls(level, x1, y1, z1, x2, y2, z2, dim, ver, wall_block, corner_block=None, props=None):
    """只建造四面墙壁(不含地板和天花板)"""
    corner = corner_block or wall_block
    for y in range(min(y1,y2), max(y1,y2)+1):
        for x in range(min(x1,x2), max(x1,x2)+1):
            for z in range(min(z1,z2), max(z1,z2)+1):
                is_edge_x = (x == min(x1,x2) or x == max(x1,x2))
                is_edge_z = (z == min(z1,z2) or z == max(z1,z2))
                if is_edge_x and is_edge_z:
                    place_block(level, x, y, z, dim, ver, corner, props)
                elif is_edge_x or is_edge_z:
                    place_block(level, x, y, z, dim, ver, wall_block, props)

def build_floor(level, x1, y1, z1, x2, z2, dim, ver, block, props=None, checkerboard=None):
    """建造地板,可选棋盘格花纹"""
    for x in range(min(x1,x2), max(x1,x2)+1):
        for z in range(min(z1,z2), max(z1,z2)+1):
            if checkerboard and (x + z) % 2 == 1:
                place_block(level, x, y1, z, dim, ver, checkerboard)
            else:
                place_block(level, x, y1, z, dim, ver, block, props)

def build_pitched_roof(level, x1, y1, z1, x2, z2, dim, ver, stair_block, slab_block, axis="z"):
    """建造斜屋顶"""
    min_x, max_x = min(x1,x2), max(x1,x2)
    min_z, max_z = min(z1,z2), max(z1,z2)

    if axis == "z":
        half_w = (max_x - min_x) // 2
        for i in range(half_w + 1):
            y = y1 + i
            for z in range(min_z, max_z + 1):
                if i == half_w and (max_x - min_x) % 2 == 0:
                    place_block(level, min_x + i, y, z, dim, ver, slab_block, {"type": "top", "waterlogged": "false"})
                else:
                    place_block(level, min_x + i, y, z, dim, ver, stair_block, {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"})
                    place_block(level, max_x - i, y, z, dim, ver, stair_block, {"facing": "west", "half": "bottom", "shape": "straight", "waterlogged": "false"})
    else:
        half_d = (max_z - min_z) // 2
        for i in range(half_d + 1):
            y = y1 + i
            for x in range(min_x, max_x + 1):
                if i == half_d and (max_z - min_z) % 2 == 0:
                    place_block(level, x, y, z, dim, ver, slab_block, {"type": "top", "waterlogged": "false"})
                else:
                    place_block(level, x, y, min_z + i, dim, ver, stair_block, {"facing": "south", "half": "bottom", "shape": "straight", "waterlogged": "false"})
                    place_block(level, x, y, max_z - i, dim, ver, stair_block, {"facing": "north", "half": "bottom", "shape": "straight", "waterlogged": "false"})

def place_door(level, x, y, z, dim, ver, material="oak", facing="west"):
    """放置一扇门(上下两格)"""
    place_block(level, x, y, z, dim, ver, f"{material}_door",
                {"half": "lower", "facing": facing, "hinge": "left", "open": "false", "powered": "false"})
    place_block(level, x, y+1, z, dim, ver, f"{material}_door",
                {"half": "upper", "facing": facing, "hinge": "left", "open": "false", "powered": "false"})

def place_bed(level, x, y, z, dim, ver, facing="east", color="red"):
    """放置一张床(两格,从foot到head)"""
    dx, dz = {"east": (1,0), "west": (-1,0), "north": (0,-1), "south": (0,1)}[facing]
    place_block(level, x, y, z, dim, ver, f"{color}_bed",
                {"facing": facing, "part": "foot", "occupied": "false"})
    place_block(level, x+dx, y, z+dz, dim, ver, f"{color}_bed",
                {"facing": facing, "part": "head", "occupied": "false"})

def place_windows(level, x1, y1, z1, x2, y2, z2, dim, ver, spacing=3):
    """在墙壁上按间距放置玻璃板窗户"""
    min_x, max_x = min(x1,x2), max(x1,x2)
    min_z, max_z = min(z1,z2), max(z1,z2)

    for y in range(min(y1,y2), max(y1,y2)+1):
        # X方向的墙(固定z)
        for x in range(min_x+1, max_x):
            if (x - min_x) % spacing == 0:
                place_block(level, x, y, min_z, dim, ver, "glass_pane")
                place_block(level, x, y, max_z, dim, ver, "glass_pane")
        # Z方向的墙(固定x)
        for z in range(min_z+1, max_z):
            if (z - min_z) % spacing == 0:
                place_block(level, min_x, y, z, dim, ver, "glass_pane")
                place_block(level, max_x, y, z, dim, ver, "glass_pane")

def open_world(save_path):
    """打开一个 Minecraft 存档"""
    ensure_deps()
    import amulet
    return amulet.load_level(save_path)

def save_and_close(level):
    """保存并关闭存档"""
    level.save()
    level.close()

# === 预设建筑模板 ===

def build_simple_house(level, bx, by, bz, dim, ver, w=7, h=5, d=7):
    """建造一个简易木屋"""
    # 地基
    build_floor(level, bx, by-1, bz, bx+w-1, bz+d-1, dim, ver, "cobblestone")
    # 地板
    build_floor(level, bx, by, bz, bx+w-1, bz+d-1, dim, ver, "oak_planks")
    # 墙壁
    build_walls(level, bx, by+1, bz, bx+w-1, by+h-1, bz+d-1, dim, ver, "oak_planks", "oak_log")
    # 清空内部
    build_box(level, bx+1, by+1, bz+1, bx+w-2, by+h-1, bz+d-2, dim, ver, "air")
    # 屋顶
    for x in range(bx, bx+w):
        for z in range(bz, bz+d):
            place_block(level, x, by+h, z, dim, ver, "oak_slab", {"type": "top", "waterlogged": "false"})
    # 门
    dz = bz + d // 2
    place_door(level, bx, by+1, dz, dim, ver, "oak", "west")
    # 窗户
    mid_x, mid_z = bx + w//2, bz + d//2
    for wy in [by+2, by+3]:
        place_block(level, bx, wy, mid_z+1, dim, ver, "glass_pane")
        place_block(level, bx, wy, mid_z-1, dim, ver, "glass_pane")
        place_block(level, bx+w-1, wy, mid_z, dim, ver, "glass_pane")
        place_block(level, mid_x, wy, bz, dim, ver, "glass_pane")
        place_block(level, mid_x, wy, bz+d-1, dim, ver, "glass_pane")
    # 家具
    place_block(level, bx+w-2, by+1, bz+1, dim, ver, "crafting_table")
    place_block(level, bx+w-2, by+1, bz+2, dim, ver, "furnace", {"facing": "west", "lit": "false"})
    place_block(level, bx+w-2, by+1, bz+d-2, dim, ver, "chest", {"facing": "west", "type": "single", "waterlogged": "false"})
    place_bed(level, bx+1, by+1, bz+d-2, dim, ver, "east", "red")
    place_block(level, bx+w//2, by+h-1, bz+d//2, dim, ver, "glowstone")
    # 门口台阶
    place_block(level, bx-1, by, dz, dim, ver, "oak_stairs", {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"})
    print(f"木屋建造完成: ({bx},{by},{bz}) 大小 {w}x{h}x{d}")

def build_skyscraper(level, bx, by, bz, dim, ver, w=15, d=15, floors=12, floor_h=5):
    """建造一栋玻璃幕墙摩天大楼"""
    H = floors * floor_h
    glass_colors = ["light_blue_stained_glass", "white_stained_glass", "light_gray_stained_glass", "cyan_stained_glass"]

    # 地基
    for x in range(bx-1, bx+w+1):
        for z in range(bz-1, bz+d+1):
            for y in range(by-3, by):
                place_block(level, x, y, z, dim, ver, "deepslate_bricks")

    for fl in range(floors):
        fy = by + fl * floor_h
        print(f"  第 {fl+1}/{floors} 层 (y={fy})")
        for y in range(fy, fy + floor_h):
            for x in range(bx, bx+w):
                for z in range(bz, bz+d):
                    is_ex = (x == bx or x == bx+w-1)
                    is_ez = (z == bz or z == bz+d-1)
                    is_corner = is_ex and is_ez
                    is_wall = is_ex or is_ez
                    ry = y - fy

                    if not is_wall:
                        if ry == 0:
                            if (x+z) % 2 == 0:
                                place_block(level, x, y, z, dim, ver, "polished_diorite")
                            else:
                                place_block(level, x, y, z, dim, ver, "polished_andesite")
                        elif ry == floor_h - 1:
                            place_block(level, x, y, z, dim, ver, "smooth_stone")
                        else:
                            place_block(level, x, y, z, dim, ver, "air")
                    elif is_corner:
                        place_block(level, x, y, z, dim, ver, "iron_block")
                    elif ry == 0 or ry == floor_h - 1:
                        place_block(level, x, y, z, dim, ver, "smooth_stone")
                    elif ry in [1,2,3]:
                        pos = (z - bz) if is_ex else (x - bx)
                        if pos % 4 == 0:
                            place_block(level, x, y, z, dim, ver, "iron_block")
                        else:
                            place_block(level, x, y, z, dim, ver, glass_colors[fl % len(glass_colors)])
                    else:
                        place_block(level, x, y, z, dim, ver, "smooth_stone")
        # 照明
        for lx in [bx+3, bx+w-4]:
            for lz in [bz+3, bz+d-4]:
                place_block(level, lx, fy+floor_h-1, lz, dim, ver, "sea_lantern")

    # 入口
    dcz = bz + d // 2
    for dz_off in range(-2, 3):
        z = dcz + dz_off
        for y in range(by+1, by+4):
            place_block(level, bx, y, z, dim, ver, "air")
        place_block(level, bx, by, z, dim, ver, "polished_blackstone")
    for dz_off in [-3, 3]:
        z = dcz + dz_off
        for y in range(by, by+5):
            place_block(level, bx-1, y, z, dim, ver, "quartz_pillar", {"axis": "y"})
        place_block(level, bx-1, by+5, z, dim, ver, "sea_lantern")
    for dz_off in range(-3, 4):
        place_block(level, bx-1, by+4, dcz+dz_off, dim, ver, "polished_blackstone")
    for dz_off in range(-2, 3):
        place_block(level, bx-1, by, dcz+dz_off, dim, ver, "polished_blackstone_stairs", {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"})

    # 楼顶
    top_y = by + H
    for x in range(bx-1, bx+w+1):
        for z in range(bz-1, bz+d+1):
            place_block(level, x, top_y, z, dim, ver, "smooth_stone_slab", {"type": "top", "waterlogged": "false"})
    for x in range(bx, bx+w):
        for z in [bz, bz+d-1]:
            place_block(level, x, top_y+1, z, dim, ver, "stone_brick_wall", {"up": "true", "north": "none", "south": "none", "east": "none", "west": "none", "waterlogged": "false"})
    for z in range(bz, bz+d):
        for x in [bx, bx+w-1]:
            place_block(level, x, top_y+1, z, dim, ver, "stone_brick_wall", {"up": "true", "north": "none", "south": "none", "east": "none", "west": "none", "waterlogged": "false"})

    bcx, bcz = bx + w//2, bz + d//2
    for y in range(top_y+1, top_y+8):
        place_block(level, bcx, y, bcz, dim, ver, "iron_block")
    place_block(level, bcx, top_y+8, bcz, dim, ver, "sea_lantern")
    place_block(level, bcx, top_y+9, bcz, dim, ver, "lightning_rod")

    print(f"摩天大楼建造完成: ({bx},{by},{bz}) {w}x{H}x{d} ({floors}层)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 mc_builder.py <save_path> <command>")
        print("命令: info | house | skyscraper")
        sys.exit(1)

    save_path = sys.argv[1]
    cmd = sys.argv[2]

    level = open_world(save_path)
    player = get_player_pos(level)
    dim = player["dimension"]
    ver = ("java", (1, 21, 0))

    print(f"玩家位置: ({player['x']}, {player['y']}, {player['z']}) 维度: {dim}")

    if cmd == "info":
        pass
    elif cmd == "house":
        ox = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        build_simple_house(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    elif cmd == "skyscraper":
        ox = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        build_skyscraper(level, player["x"]+ox, player["y"], player["z"], dim, ver)

    save_and_close(level)
