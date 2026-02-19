#!/usr/bin/env python3
"""
Minecraft Builder - 通过 amulet-core 在 Java 版存档中建造建筑。

用法:
    python3 mc_builder.py <save_path> <command>
    python3 mc_builder.py <save_name> info          # 按存档名自动查找
    python3 mc_builder.py test house 5              # 在玩家东边5格建木屋
"""

import sys
import os
import math
import shutil
import random
from pathlib import Path
from datetime import datetime

# ============================================
# 常量
# ============================================

SAVES_DIR = os.path.expanduser("~/Library/Application Support/minecraft/saves")

# 常见方块名纠正表 (错误名 -> 正确名)
BLOCK_ALIASES = {
    "tulip_red": "red_tulip", "tulip_orange": "orange_tulip",
    "tulip_pink": "pink_tulip", "tulip_white": "white_tulip",
    "oak_plank": "oak_planks", "spruce_plank": "spruce_planks",
    "birch_plank": "birch_planks", "dark_oak_plank": "dark_oak_planks",
    "stone_brick": "stone_bricks", "cobble": "cobblestone",
    "wood": "oak_planks", "glass": "glass_block",
}

# 常用花卉列表 (正确的方块名)
FLOWERS = [
    "poppy", "dandelion", "blue_orchid", "allium", "azure_bluet",
    "cornflower", "lily_of_the_valley", "oxeye_daisy",
    "red_tulip", "orange_tulip", "pink_tulip", "white_tulip",
]

POTTED_FLOWERS = [
    "potted_poppy", "potted_dandelion", "potted_blue_orchid",
    "potted_allium", "potted_fern", "potted_azure_bluet",
]

# ============================================
# 核心: 存档管理
# ============================================

def ensure_deps():
    """确保 amulet-core 已安装"""
    try:
        import amulet
    except ImportError:
        os.system("pip3 install amulet-core amulet-nbt nbtlib")

def resolve_save_path(name_or_path):
    """解析存档路径: 支持完整路径或存档名"""
    if os.path.isdir(name_or_path):
        return name_or_path
    candidate = os.path.join(SAVES_DIR, name_or_path)
    if os.path.isdir(candidate):
        return candidate
    raise FileNotFoundError(f"找不到存档: {name_or_path} (尝试了 {candidate})")

def open_world(save_path, auto_backup=True):
    """打开 Minecraft 存档, 默认自动备份"""
    ensure_deps()
    import amulet

    save_path = resolve_save_path(save_path)
    if auto_backup:
        backup_path = save_path.rstrip("/") + "_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        if not os.path.exists(backup_path):
            shutil.copytree(save_path, backup_path)
            print(f"已自动备份到: {backup_path}")

    level = amulet.load_level(save_path)
    return level

def save_and_close(level):
    """保存并关闭存档"""
    level.save()
    level.close()

def detect_version(level):
    """从 level.dat 自动检测游戏版本, 返回 amulet 版本元组"""
    import nbtlib
    level_path = os.path.join(level.level_wrapper.path, "level.dat")
    nbt = nbtlib.load(level_path)
    data = nbt["Data"]
    # DataVersion: 1.21=3953, 1.20.4=3700, 1.20=3463, 1.19=3105
    dv = int(data.get("DataVersion", 3953))
    if dv >= 3953:
        return ("java", (1, 21, 0))
    elif dv >= 3463:
        return ("java", (1, 20, 0))
    elif dv >= 3105:
        return ("java", (1, 19, 0))
    elif dv >= 2860:
        return ("java", (1, 18, 0))
    else:
        return ("java", (1, 17, 0))

def get_player_pos(level):
    """从 level.dat 读取玩家位置和维度"""
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

def quick_setup(save_name, auto_backup=True):
    """一键初始化: 打开存档 + 获取玩家位置 + 检测版本
    返回 (level, player, dim, ver)"""
    level = open_world(save_name, auto_backup)
    player = get_player_pos(level)
    ver = detect_version(level)
    dim = player["dimension"]
    print(f"玩家位置: ({player['x']}, {player['y']}, {player['z']}) 维度: {dim} 版本: {ver[1]}")
    return level, player, dim, ver

# ============================================
# 核心: 方块放置
# ============================================

def _fix_block_name(name):
    """自动纠正常见方块名错误"""
    return BLOCK_ALIASES.get(name, name)

def place_block(level, x, y, z, dimension, game_version, block_name, properties=None):
    """放置单个方块"""
    import amulet
    from amulet.api.block import Block

    block_name = _fix_block_name(block_name)
    props = {}
    if properties:
        for k, v in properties.items():
            props[k] = amulet.StringTag(str(v))
    block = Block("minecraft", block_name, props)
    level.set_version_block(x, y, z, dimension, game_version, block)

def get_block(level, x, y, z, dimension, game_version):
    """读取指定位置的方块, 返回 (namespace, base_name)"""
    block, _ = level.get_version_block(x, y, z, dimension, game_version)
    return f"{block.namespace}:{block.base_name}"

# ============================================
# 地形工具
# ============================================

def scan_terrain(level, cx, cz, dim, ver, radius=80, base_y=64):
    """扫描以(cx,cz)为中心的地形, 返回 height_map: {(x,z): y}"""
    height_map = {}
    for x in range(cx - radius, cx + radius):
        for z in range(cz - radius, cz + radius):
            for y in range(base_y + 40, base_y - 40, -1):
                bid = get_block(level, x, y, z, dim, ver)
                if bid != "minecraft:air":
                    if bid != "minecraft:water":
                        height_map[(x, z)] = y
                    break
    return height_map

def get_terrain_bounds(height_map):
    """从 height_map 获取地形边界, 返回 (min_x, max_x, min_z, max_z, min_y, max_y)"""
    if not height_map:
        return (0, 0, 0, 0, 0, 0)
    xs = [k[0] for k in height_map]
    zs = [k[1] for k in height_map]
    ys = list(height_map.values())
    return (min(xs), max(xs), min(zs), max(zs), min(ys), max(ys))

def flatten_area(level, x1, z1, x2, z2, target_y, dim, ver,
                 surface="grass_block", underground="dirt", clear_above=20):
    """平整一块区域到指定高度
    - 高于 target_y 的方块清除
    - 低于 target_y 的方块填充
    - surface: 地表方块
    - underground: 地下填充方块
    """
    surface_props = {"snowy": "false"} if surface == "grass_block" else None
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for z in range(min(z1, z2), max(z1, z2) + 1):
            place_block(level, x, target_y, z, dim, ver, surface, surface_props)
            for dy in range(1, clear_above + 1):
                place_block(level, x, target_y + dy, z, dim, ver, "air")
            for dy in range(1, 4):
                place_block(level, x, target_y - dy, z, dim, ver, underground)

def clear_vegetation(level, x1, z1, x2, z2, y_base, dim, ver, height=25):
    """清除地面以上的植被(树木、花草等), 保留地面"""
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for z in range(min(z1, z2), max(z1, z2) + 1):
            for y in range(y_base + 1, y_base + height):
                place_block(level, x, y, z, dim, ver, "air")

# ============================================
# 基础建筑原语
# ============================================

def build_box(level, x1, y1, z1, x2, y2, z2, dim, ver, block, props=None, hollow=False):
    """建造方块盒子(实心或空心)"""
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
    """建造四面墙壁(不含地板和天花板), 可指定角柱材料"""
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
    """建造地板, 可选棋盘格花纹"""
    for x in range(min(x1,x2), max(x1,x2)+1):
        for z in range(min(z1,z2), max(z1,z2)+1):
            if checkerboard and (x + z) % 2 == 1:
                place_block(level, x, y1, z, dim, ver, checkerboard)
            else:
                place_block(level, x, y1, z, dim, ver, block, props)

def build_circle(level, cx, y, cz, radius, dim, ver, block, props=None, fill=False):
    """在水平面上建造一个圆形(环或实心圆盘)"""
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            dist_sq = dx*dx + dz*dz
            if fill:
                if dist_sq <= radius * radius:
                    place_block(level, cx + dx, y, cz + dz, dim, ver, block, props)
            else:
                if dist_sq <= radius * radius and dist_sq > (radius - 1) * (radius - 1):
                    place_block(level, cx + dx, y, cz + dz, dim, ver, block, props)

def build_cylinder(level, cx, cz, y1, y2, radius, dim, ver, block, props=None, hollow=True):
    """建造圆柱体(实心或空心)"""
    for y in range(min(y1, y2), max(y1, y2) + 1):
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                dist_sq = dx*dx + dz*dz
                if dist_sq <= radius * radius:
                    if hollow and dist_sq < (radius - 1) * (radius - 1):
                        place_block(level, cx + dx, y, cz + dz, dim, ver, "air")
                    else:
                        place_block(level, cx + dx, y, cz + dz, dim, ver, block, props)

def build_arch(level, x, y_base, z1, z2, height, dim, ver, block, props=None):
    """在x固定的平面上建造一个拱门(沿z轴)"""
    span = abs(z2 - z1)
    mid_z = (z1 + z2) / 2.0
    half = span / 2.0

    # 两侧柱子
    for y in range(y_base, y_base + height):
        place_block(level, x, y, min(z1, z2), dim, ver, block, props)
        place_block(level, x, y, max(z1, z2), dim, ver, block, props)

    # 拱形顶部 (半椭圆)
    for z in range(min(z1, z2), max(z1, z2) + 1):
        dz = abs(z - mid_z)
        if half > 0:
            arch_y = y_base + height + int((height * 0.5) * math.sqrt(max(0, 1 - (dz / half) ** 2)))
        else:
            arch_y = y_base + height
        place_block(level, x, arch_y, z, dim, ver, block, props)
        # 填充柱子到拱顶之间
        for y in range(y_base + height, arch_y):
            place_block(level, x, y, z, dim, ver, block, props)

def build_pitched_roof(level, x1, y1, z1, x2, z2, dim, ver, stair_block, slab_block, axis="z"):
    """建造斜屋顶 (axis='z'沿z轴升高, 'x'沿x轴升高)"""
    min_x, max_x = min(x1,x2), max(x1,x2)
    min_z, max_z = min(z1,z2), max(z1,z2)

    if axis == "z":
        half_d = (max_z - min_z) // 2
        for i in range(half_d + 1):
            y = y1 + i
            if min_z + i >= max_z - i:
                for x in range(min_x, max_x + 1):
                    place_block(level, x, y, min_z + i, dim, ver, slab_block,
                                {"type": "top", "waterlogged": "false"})
                break
            for x in range(min_x, max_x + 1):
                place_block(level, x, y, min_z + i, dim, ver, stair_block,
                            {"facing": "south", "half": "bottom", "shape": "straight", "waterlogged": "false"})
                place_block(level, x, y, max_z - i, dim, ver, stair_block,
                            {"facing": "north", "half": "bottom", "shape": "straight", "waterlogged": "false"})
    else:
        half_w = (max_x - min_x) // 2
        for i in range(half_w + 1):
            y = y1 + i
            if min_x + i >= max_x - i:
                for z in range(min_z, max_z + 1):
                    place_block(level, min_x + i, y, z, dim, ver, slab_block,
                                {"type": "top", "waterlogged": "false"})
                break
            for z in range(min_z, max_z + 1):
                place_block(level, min_x + i, y, z, dim, ver, stair_block,
                            {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"})
                place_block(level, max_x - i, y, z, dim, ver, stair_block,
                            {"facing": "west", "half": "bottom", "shape": "straight", "waterlogged": "false"})

def build_cone(level, cx, cz, y_base, radius, height, dim, ver, block, props=None):
    """建造圆锥体/锥形屋顶"""
    for i in range(height):
        r = radius * (1 - i / height)
        if r < 0.5:
            place_block(level, cx, y_base + i, cz, dim, ver, block, props)
            break
        build_circle(level, cx, y_base + i, cz, int(r), dim, ver, block, props, fill=True)

# ============================================
# 家具与装饰
# ============================================

def place_door(level, x, y, z, dim, ver, material="oak", facing="west"):
    """放置一扇门(上下两格)"""
    place_block(level, x, y, z, dim, ver, f"{material}_door",
                {"half": "lower", "facing": facing, "hinge": "left", "open": "false", "powered": "false"})
    place_block(level, x, y+1, z, dim, ver, f"{material}_door",
                {"half": "upper", "facing": facing, "hinge": "left", "open": "false", "powered": "false"})

def place_bed(level, x, y, z, dim, ver, facing="east", color="red"):
    """放置一张床(两格, foot在(x,z), head在facing方向)"""
    dx, dz = {"east": (1,0), "west": (-1,0), "north": (0,-1), "south": (0,1)}[facing]
    place_block(level, x, y, z, dim, ver, f"{color}_bed",
                {"facing": facing, "part": "foot", "occupied": "false"})
    place_block(level, x+dx, y, z+dz, dim, ver, f"{color}_bed",
                {"facing": facing, "part": "head", "occupied": "false"})

def place_windows(level, x1, y1, z1, x2, y2, z2, dim, ver, spacing=3, glass="glass_pane"):
    """在墙壁上按间距放置窗户"""
    min_x, max_x = min(x1,x2), max(x1,x2)
    min_z, max_z = min(z1,z2), max(z1,z2)

    for y in range(min(y1,y2), max(y1,y2)+1):
        for x in range(min_x+1, max_x):
            if (x - min_x) % spacing == 0:
                place_block(level, x, y, min_z, dim, ver, glass)
                place_block(level, x, y, max_z, dim, ver, glass)
        for z in range(min_z+1, max_z):
            if (z - min_z) % spacing == 0:
                place_block(level, min_x, y, z, dim, ver, glass)
                place_block(level, max_x, y, z, dim, ver, glass)

def place_lantern_post(level, x, y, z, dim, ver, height=3):
    """放置路灯 (栅栏柱+灯笼)"""
    for dy in range(1, height + 1):
        place_block(level, x, y + dy, z, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
    place_block(level, x, y + height + 1, z, dim, ver, "lantern",
                {"hanging": "false", "waterlogged": "false"})

def place_tree(level, x, y, z, dim, ver, trunk="oak_log", leaves="oak_leaves", trunk_h=None):
    """种一棵简易树"""
    if trunk_h is None:
        trunk_h = random.randint(4, 6)
    for ty in range(y + 1, y + 1 + trunk_h):
        place_block(level, x, ty, z, dim, ver, trunk, {"axis": "y"})
    top_y = y + 1 + trunk_h
    for dy in range(-1, 2):
        r = 3 if dy < 1 else 2
        for ddx in range(-r, r + 1):
            for ddz in range(-r, r + 1):
                if ddx*ddx + ddz*ddz <= r*r:
                    place_block(level, x + ddx, top_y + dy, z + ddz, dim, ver, leaves,
                                {"distance": "1", "persistent": "true", "waterlogged": "false"})

def build_path(level, x1, z1, x2, z2, y, dim, ver, width=1, block="dirt_path"):
    """建造一条从(x1,z1)到(x2,z2)的小路"""
    dx = 1 if x2 > x1 else (-1 if x2 < x1 else 0)
    dz = 1 if z2 > z1 else (-1 if z2 < z1 else 0)
    x, z = x1, z1
    while x != x2 or z != z2:
        for ox in range(-width, width + 1):
            for oz in range(-width, width + 1):
                if random.random() < 0.75:
                    place_block(level, x + ox, y, z + oz, dim, ver, block)
        if x != x2 and (z == z2 or random.random() < 0.5):
            x += dx
        elif z != z2:
            z += dz

# ============================================
# 预设建筑模板
# ============================================

def build_simple_house(level, bx, by, bz, dim, ver, w=7, h=5, d=7):
    """建造简易木屋 (含家具)"""
    build_floor(level, bx, by-1, bz, bx+w-1, bz+d-1, dim, ver, "cobblestone")
    build_floor(level, bx, by, bz, bx+w-1, bz+d-1, dim, ver, "oak_planks")
    build_walls(level, bx, by+1, bz, bx+w-1, by+h-1, bz+d-1, dim, ver, "oak_planks", "oak_log")
    build_box(level, bx+1, by+1, bz+1, bx+w-2, by+h-1, bz+d-2, dim, ver, "air")
    for x in range(bx, bx+w):
        for z in range(bz, bz+d):
            place_block(level, x, by+h, z, dim, ver, "oak_slab", {"type": "top", "waterlogged": "false"})
    dz = bz + d // 2
    place_door(level, bx, by+1, dz, dim, ver, "oak", "west")
    mid_x, mid_z = bx + w//2, bz + d//2
    for wy in [by+2, by+3]:
        place_block(level, bx, wy, mid_z+1, dim, ver, "glass_pane")
        place_block(level, bx, wy, mid_z-1, dim, ver, "glass_pane")
        place_block(level, bx+w-1, wy, mid_z, dim, ver, "glass_pane")
        place_block(level, mid_x, wy, bz, dim, ver, "glass_pane")
        place_block(level, mid_x, wy, bz+d-1, dim, ver, "glass_pane")
    place_block(level, bx+w-2, by+1, bz+1, dim, ver, "crafting_table")
    place_block(level, bx+w-2, by+1, bz+2, dim, ver, "furnace", {"facing": "west", "lit": "false"})
    place_block(level, bx+w-2, by+1, bz+d-2, dim, ver, "chest", {"facing": "west", "type": "single", "waterlogged": "false"})
    place_bed(level, bx+1, by+1, bz+d-2, dim, ver, "east", "red")
    place_block(level, bx+w//2, by+h-1, bz+d//2, dim, ver, "lantern", {"hanging": "true", "waterlogged": "false"})
    place_block(level, bx-1, by, dz, dim, ver, "oak_stairs", {"facing": "east", "half": "bottom", "shape": "straight", "waterlogged": "false"})
    print(f"木屋建造完成: ({bx},{by},{bz}) 大小 {w}x{h}x{d}")

def build_skyscraper(level, bx, by, bz, dim, ver, w=15, d=15, floors=12, floor_h=5):
    """建造玻璃幕墙摩天大楼"""
    H = floors * floor_h
    glass_colors = ["light_blue_stained_glass", "white_stained_glass", "light_gray_stained_glass", "cyan_stained_glass"]

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
                            place_block(level, x, y, z, dim, ver, "polished_diorite" if (x+z)%2==0 else "polished_andesite")
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
        for lx in [bx+3, bx+w-4]:
            for lz in [bz+3, bz+d-4]:
                place_block(level, lx, fy+floor_h-1, lz, dim, ver, "sea_lantern")

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

def build_cottage(level, bx, by, bz, dim, ver, w=8, d=7, h=4,
                  wall="oak_planks", roof_stair="dark_oak_stairs", roof_slab="dark_oak_slab",
                  log="oak_log", facing="south", name="小屋"):
    """建造田园风格小屋 (含烟囱、窗户、屋顶)"""
    print(f"  建造{name} ({bx},{bz}) {w}x{d}...")
    flatten_area(level, bx - 1, bz - 1, bx + w, bz + d, by, dim, ver)

    for x in range(bx - 1, bx + w + 1):
        for z in range(bz - 1, bz + d + 1):
            place_block(level, x, by, z, dim, ver, "cobblestone")
    for x in range(bx, bx + w):
        for z in range(bz, bz + d):
            place_block(level, x, by, z, dim, ver, "spruce_planks" if (x+z)%3 != 0 else "oak_planks")

    for y in range(by + 1, by + h + 1):
        for x in range(bx, bx + w):
            for z in range(bz, bz + d):
                is_ex = (x == bx or x == bx + w - 1)
                is_ez = (z == bz or z == bz + d - 1)
                if not (is_ex or is_ez):
                    place_block(level, x, y, z, dim, ver, "air")
                elif is_ex and is_ez:
                    place_block(level, x, y, z, dim, ver, log, {"axis": "y"})
                elif y == by + h:
                    place_block(level, x, y, z, dim, ver, log, {"axis": "x" if is_ex else "z"})
                else:
                    place_block(level, x, y, z, dim, ver, wall)

    mid_x, mid_z = bx + w // 2, bz + d // 2
    for wy in [by + 2, by + 3] if h >= 4 else [by + 2]:
        for wz in ([mid_z - 1, mid_z, mid_z + 1] if d > 5 else [mid_z]):
            place_block(level, bx, wy, wz, dim, ver, "glass_pane")
            place_block(level, bx + w - 1, wy, wz, dim, ver, "glass_pane")
        for wx in ([mid_x - 1, mid_x, mid_x + 1] if w > 5 else [mid_x]):
            place_block(level, wx, wy, bz, dim, ver, "glass_pane")
            place_block(level, wx, wy, bz + d - 1, dim, ver, "glass_pane")

    for i in range((d // 2) + 2):
        ry = by + h + 1 + i
        r_z1 = bz - 1 + i
        r_z2 = bz + d - i
        if r_z1 >= r_z2:
            for x in range(bx - 1, bx + w + 1):
                place_block(level, x, ry, r_z1, dim, ver, roof_slab, {"type": "top", "waterlogged": "false"})
            break
        for x in range(bx - 1, bx + w + 1):
            place_block(level, x, ry, r_z1, dim, ver, roof_stair, {"facing": "south", "half": "bottom", "shape": "straight", "waterlogged": "false"})
            place_block(level, x, ry, r_z2, dim, ver, roof_stair, {"facing": "north", "half": "bottom", "shape": "straight", "waterlogged": "false"})
            for z in range(r_z1 + 1, r_z2):
                place_block(level, x, ry, z, dim, ver, "air")

    if facing == "south":
        place_door(level, mid_x, by + 1, bz + d - 1, dim, ver, "oak", "south")
    elif facing == "north":
        place_door(level, mid_x, by + 1, bz, dim, ver, "oak", "north")
    elif facing == "west":
        place_door(level, bx, by + 1, mid_z, dim, ver, "oak", "west")
    elif facing == "east":
        place_door(level, bx + w - 1, by + 1, mid_z, dim, ver, "oak", "east")

    place_block(level, mid_x, by + h, mid_z, dim, ver, "lantern", {"hanging": "true", "waterlogged": "false"})
    cx = bx + w - 2
    cz = bz + 1
    for cy in range(by + h, by + h + 5):
        place_block(level, cx, cy, cz, dim, ver, "cobblestone")
    place_block(level, cx, by + 1, cz, dim, ver, "campfire", {"facing": "north", "lit": "true", "signal_fire": "false", "waterlogged": "false"})

    print(f"  {name}完成!")
    return (mid_x, mid_z)

def build_windmill(level, cx, by, cz, dim, ver, height=15, radius=3):
    """建造风车"""
    flatten_area(level, cx - radius - 2, cz - radius - 2, cx + radius + 2, cz + radius + 2, by, dim, ver)

    for y in range(by, by + height):
        r = radius if y < by + height - 3 else max(1, radius - (y - (by + height - 3)))
        build_circle(level, cx, y, cz, r, dim, ver,
                     "cobblestone" if y < by + 3 else "white_concrete", fill=True)
        if r > 1:
            for dx in range(-r + 1, r):
                for dz in range(-r + 1, r):
                    if dx*dx + dz*dz < (r-1) * (r-1):
                        place_block(level, cx + dx, y, cz + dz, dim, ver, "air")

    place_door(level, cx, by + 1, cz + radius, dim, ver, "oak", "south")

    blade_y = by + height - 3
    blade_z = cz + radius + 1
    for i in range(1, 7):
        for dx, dy, wool_dx, wool_dy in [(i, 0, i, 1), (-i, 0, -i, -1), (0, i, 1, i), (0, -i, -1, -i)]:
            place_block(level, cx + dx, blade_y + dy, blade_z, dim, ver, "oak_fence",
                        {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
            place_block(level, cx + wool_dx, blade_y + wool_dy, blade_z, dim, ver, "white_wool")

    for dx in range(-radius - 1, radius + 2):
        for dz in range(-radius - 1, radius + 2):
            if dx*dx + dz*dz <= (radius + 1) ** 2:
                place_block(level, cx + dx, by + height, cz + dz, dim, ver, "dark_oak_planks")
    place_block(level, cx, by + height + 1, cz, dim, ver, "dark_oak_planks")
    print(f"风车建造完成: ({cx},{by},{cz})")

def build_farm(level, bx, by, bz, dim, ver, w=20, d=16, crops=None):
    """建造围栏农田 (自动灌溉水渠)"""
    if crops is None:
        crops = ["wheat", "carrots", "potatoes", "beetroots"]

    flatten_area(level, bx - 1, bz - 1, bx + w, bz + d, by, dim, ver)

    # 围栏
    for x in range(bx - 1, bx + w + 1):
        place_block(level, x, by + 1, bz - 1, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
        place_block(level, x, by + 1, bz + d, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
    for z in range(bz - 1, bz + d + 1):
        place_block(level, bx - 1, by + 1, z, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
        place_block(level, bx + w, by + 1, z, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
    place_block(level, bx + w // 2, by + 1, bz + d, dim, ver, "oak_fence_gate",
                {"facing": "south", "in_wall": "false", "open": "false", "powered": "false"})

    # 田地 (每块9x7, 中间水渠)
    cols = min(len(crops), w // 10)
    rows = max(1, len(crops) // cols)
    for ci, crop in enumerate(crops):
        bx_off = (ci % cols) * (w // cols)
        bz_off = (ci // cols) * (d // rows)
        pw = w // cols - 1
        pd = d // rows - 1
        for x in range(bx + bx_off, bx + bx_off + pw):
            for z in range(bz + bz_off, bz + bz_off + pd):
                if (x - bx - bx_off) == pw // 2:
                    place_block(level, x, by - 1, z, dim, ver, "water")
                    place_block(level, x, by, z, dim, ver, "air")
                else:
                    place_block(level, x, by, z, dim, ver, "farmland", {"moisture": "7"})
                    age = str(random.randint(4, 7))
                    place_block(level, x, by + 1, z, dim, ver, crop, {"age": age})

    print(f"农田建造完成: ({bx},{by},{bz}) {w}x{d}")

def build_dock(level, bx, by, bz, dim, ver, length=18, width=5):
    """建造木码头 (延伸入水)"""
    half_w = width // 2
    for z in range(bz, bz + length):
        for dx in range(-half_w, half_w + 1):
            x = bx + dx
            if z % 4 == 0 and abs(dx) == half_w:
                for ply in range(by - 5, by + 1):
                    place_block(level, x, ply, z, dim, ver, "oak_log", {"axis": "y"})
            place_block(level, x, by, z, dim, ver, "spruce_planks")
        place_block(level, bx - half_w, by + 1, z, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})
        place_block(level, bx + half_w, by + 1, z, dim, ver, "oak_fence",
                    {"north": "false", "south": "false", "east": "false", "west": "false", "waterlogged": "false"})

    for dx in [-half_w, half_w]:
        place_lantern_post(level, bx + dx, by, bz + length - 1, dim, ver, height=3)

    print(f"码头建造完成: ({bx},{by},{bz}) 长{length}")

# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 mc_builder.py <save_name_or_path> <command> [args...]")
        print("命令: info | house | skyscraper | cottage | windmill | farm | dock")
        sys.exit(1)

    level, player, dim, ver = quick_setup(sys.argv[1])
    cmd = sys.argv[2]
    ox = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    if cmd == "info":
        pass
    elif cmd == "house":
        build_simple_house(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    elif cmd == "skyscraper":
        build_skyscraper(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    elif cmd == "cottage":
        build_cottage(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    elif cmd == "windmill":
        build_windmill(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    elif cmd == "farm":
        build_farm(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    elif cmd == "dock":
        build_dock(level, player["x"]+ox, player["y"], player["z"], dim, ver)
    else:
        print(f"未知命令: {cmd}")

    save_and_close(level)
