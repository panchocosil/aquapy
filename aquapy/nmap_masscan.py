from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from typing import List, Dict

def _parse_root(source: str):
    if os.path.exists(source):
        tree = ET.parse(source)
        return tree.getroot()
    return ET.fromstring(source)

def parse_open_ports(source: str) -> Dict[str, List[int]]:
    res: Dict[str, List[int]] = {}
    root = _parse_root(source)
    for host in root.findall(".//host"):
        addresses = [a.get("addr") for a in host.findall("address") if a.get("addr")]
        hostnames = [h.get("name") for h in host.findall(".//hostname") if h.get("name")]
        name = hostnames[0] if hostnames else (addresses[0] if addresses else None)
        if not name:
            continue
        ports = []
        for p in host.findall(".//port"):
            state = p.find("state")
            if state is not None and state.get("state") == "open":
                try: ports.append(int(p.get("portid")))
                except Exception: pass
        if ports:
            res.setdefault(name, [])
            for prt in sorted(set(ports)):
                if prt not in res[name]:
                    res[name].append(prt)
    return res
