from __future__ import annotations
from typing import Dict, List
import json

class Fingerprinter:
    def __init__(self, fingerprints_path: str):
        self.db = {"technologies": []}
        try:
            with open(fingerprints_path, "r", encoding="utf-8") as f:
                self.db = json.load(f)
        except Exception:
            pass

    def detect(self, headers: Dict[str,str], html: str) -> List[dict]:
        techs = []
        hdrs = { (k or '').lower(): (v or '').lower() for k,v in (headers or {}).items() }
        body = (html or "").lower()
        for t in self.db.get("technologies", []):
            score = 0; matched = False
            for hk, hv in (t.get("headers") or {}).items():
                hv = hv.lower()
                if hk.lower() in hdrs and hv in hdrs[hk.lower()]:
                    score += 2; matched = True
            for frag in (t.get("html") or []):
                if frag.lower() in body:
                    score += 1; matched = True
            if matched:
                techs.append({
                    "name": t.get("name"),
                    "slug": t.get("slug"),
                    "categories": t.get("categories", []),
                    "score": score
                })
        techs.sort(key=lambda x: (-x["score"], x["name"] or ""))
        return techs
