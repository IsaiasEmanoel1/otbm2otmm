import os
import time
import zlib
import struct
from otb_parser import NodeReader

# Constantes extraídas das sources
OTBM_MAP_DATA = 2
OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ITEM = 6
OTBM_HOUSETILE = 14

def safe_read(f, n):
    data = f.read(n)
    if len(data) < n: raise EOFError
    return data

def load_tibia_dat(filename):
    print(f"[*] Lendo {filename} (Versão 8.60 | Seek Mode)...")
    client_colors = {}
    try:
        with open(filename, "rb") as f:
            f.seek(4, 1) # Assinatura
            item_count = struct.unpack('<H', safe_read(f, 2))[0]
            f.seek(6, 1) # Criaturas, Efeitos, Mísseis
            
            for client_id in range(100, item_count + 1):
                minimap_color = 0
                while True:
                    attr = safe_read(f, 1)[0]
                    if attr == 255: break # ThingLastAttr
                    
                    # Conforme thingtype.cpp: Atributos que consomem 2 bytes
                    if attr in (0, 8, 9, 25, 28, 29, 32, 34):
                        val = struct.unpack('<H', safe_read(f, 2))[0]
                        if attr == 28: # ThingAttrMinimapColor
                            minimap_color = val
                    elif attr in (21, 24): # Light e Displacement
                        f.seek(4, 1)
                    elif attr == 33: # Market
                        f.seek(6, 1)
                        length = struct.unpack('<H', safe_read(f, 2))[0]
                        f.seek(length + 4, 1)
                    elif attr == 38: # Bones
                        f.seek(16, 1)

                if minimap_color > 0:
                    client_colors[client_id] = minimap_color & 0xFF
                    
                # Pulo de Sprites Otimizado (Resolve MemoryError bad allocation)
                w, h = safe_read(f, 1)[0], safe_read(f, 1)[0]
                if w > 1 or h > 1: f.seek(1, 1) 
                l, px, py, pz, ph = struct.unpack('<BBBBB', safe_read(f, 5))
                if ph > 1: f.seek(6 + (ph * 8), 1) # Animator
                
                total = w * h * l * px * py * pz * ph
                f.seek(total * 4, 1) # 4 bytes por sprite (8.60)
                
    except EOFError: pass
    print(f"[+] {len(client_colors)} cores extraídas do DAT!")
    return client_colors

def load_items_otb(filename):
    print(f"[*] Lendo {filename}...")
    with open(filename, "rb") as f:
        f.read(4) 
        data = f.read()
    reader = NodeReader(data)
    root_node = reader.get_next_node()
    s2c, o_cols, o_grps = {}, {}, {}
    
    def extract(node):
        if len(node['data']) >= 4:
            d, idx = node['data'], 4
            sid, cid, col = 0, 0, 0
            while idx + 2 <= len(d):
                attr = d[idx]
                idx += 1
                length = d[idx] | (d[idx+1] << 8)
                idx += 2
                if attr == 0x10: 
                    sid = d[idx] | (d[idx+1] << 8)
                    if 20000 < sid < 20100: sid -= 20000 #
                elif attr == 0x11: cid = d[idx] | (d[idx+1] << 8)
                elif attr == 0x21: col = d[idx]
                idx += length
            if sid > 0:
                o_grps[sid] = node['type']
                if cid > 0: s2c[sid] = cid
                if col > 0: o_cols[sid] = col
        for child in node['children']: extract(child)
    
    if root_node: extract(root_node)
    return s2c, o_cols, o_grps

def load_map_otbm(filename, s2c, dat_colors, otb_colors):
    print(f"[*] Analisando estrutura binária do OTBM (Atributo 9)...")
    with open(filename, "rb") as f:
        f.read(4) # OTBM Identifier
        data = f.read()
        
    reader = NodeReader(data)
    root = reader.get_next_node()
    map_node = next((c for c in root['children'] if c['type'] == OTBM_MAP_DATA), None)
    map_pixels = {} 
    
    for area in map_node['children']:
        if area['type'] == OTBM_TILE_AREA:

            bx = area['data'][0] | (area['data'][1] << 8)
            by = area['data'][2] | (area['data'][3] << 8)
            bz = area['data'][4]
            
            for tile in area['children']:
                if tile['type'] in (OTBM_TILE, OTBM_HOUSETILE):
                    d = tile['data']

                    ax, ay = bx + d[0], by + d[1]
                    f_color = 0
                    idx = 2

                    if tile['type'] == OTBM_HOUSETILE:
                        idx += 4
                        
                    while idx < len(d):
                        attr = d[idx]
                        idx += 1
                        if attr == 0 or attr == 255: break
                        
                        if attr == 3:
                            idx += 4 
                        elif attr == 9: # OTBM_ATTR_ITEM (O GROUND!)
                            gid = d[idx] | (d[idx+1] << 8)
                            idx += 2
                            if 20000 < gid < 20100: gid -= 20000
                            cid = s2c.get(gid, 0)
                            f_color = dat_colors.get(cid, 0) or otb_colors.get(gid, 0)
                        else:
                            # Se for um atributo desconhecido (ActionID, etc), ele break.
                            break

                    # --- Itens Filhos (Paredes, bordas, etc) ---
                    for item_node in tile['children']:
                        if item_node['type'] == OTBM_ITEM:
                            sid = item_node['data'][0] | (item_node['data'][1] << 8)
                            if 20000 < sid < 20100: sid -= 20000
                            cid = s2c.get(sid, 0)
                            color = dat_colors.get(cid, 0) or otb_colors.get(sid, 0)
                            if color: f_color = color # Sobrescreve o ground se for um item visível
                    
                    if f_color:
                        map_pixels[(ax, ay, bz)] = f_color
                        
    return map_pixels

def generate_otmm(map_pixels, output):
    print(f"[*] Gerando OTMM (Byte Order corrigido para 8.60)...")
    BLOCK_SIZE, TILE_BYTES = 64, 3
    blocks = {}
    for (x, y, z), color in map_pixels.items():
        bk = ( (x//BLOCK_SIZE)*BLOCK_SIZE, (y//BLOCK_SIZE)*BLOCK_SIZE, z )
        if bk not in blocks: blocks[bk] = bytearray(BLOCK_SIZE * BLOCK_SIZE * TILE_BYTES)
        idx = (((y % BLOCK_SIZE) * BLOCK_SIZE) + (x % BLOCK_SIZE)) * TILE_BYTES
        
        # Ordem de bytes conforme minimap.cpp do seu projeto: [Flags, Cor, Speed]
        blocks[bk][idx] = 1        # Flags (Seen)
        blocks[bk][idx+1] = color  # Cor Real extraída
        blocks[bk][idx+2] = 10     # Speed Default
    
    with open(output, "wb") as f:
        f.write(struct.pack('<IHH I', 0x4D4D544F, 22, 1, 0))
        desc = b"OTMM 1.0"
        f.write(struct.pack('<H', len(desc)) + desc)
        for (bx, by, bz), data in blocks.items():
            comp = zlib.compress(data, 3)
            f.write(struct.pack('<HHB H', bx, by, bz, len(comp)) + comp)
        f.write(struct.pack('<HHB', 0xFFFF, 0xFFFF, 0xFF))
    print(f"[+] minimap.otmm pronto.")

if __name__ == "__main__":
    dat_colors = load_tibia_dat("Tibia.dat")
    s2c, o_cols, o_grps = load_items_otb("items.otb")
    mapa = load_map_otbm("mapadois.otbm", s2c, dat_colors, o_cols)
    generate_otmm(mapa, "minimap.otmm")