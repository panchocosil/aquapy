from __future__ import annotations
from typing import List, Dict, Tuple

def _hex_to_bits(h: str) -> int:
    return int(h, 16)

def hamming(a_hex: str, b_hex: str) -> int:
    try:
        return (_hex_to_bits(a_hex) ^ _hex_to_bits(b_hex)).bit_count()
    except Exception:
        return 64

def cluster_phashes(items: List[Tuple[int, str]], threshold: int = 10) -> Dict[int, int]:
    parent = {i:i for i,_ in items}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a,b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            ei, hi = items[i]; ej, hj = items[j]
            if hi and hj and hamming(hi, hj) <= threshold:
                union(ei, ej)
    roots = {}; next_id = 1; out = {}
    for idx,_ in items:
        r = find(idx)
        if r not in roots:
            roots[r] = next_id; next_id += 1
        out[idx] = roots[r]
    return out
