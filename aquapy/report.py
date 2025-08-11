from __future__ import annotations
from typing import List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .models import Entry
from collections import defaultdict
import os, json

def render_report(entries: List[Entry], output_dir: str, template_dir: str) -> str:
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html','xml']))
    tpl = env.get_template("report.html.j2")
    def rel(path): return os.path.relpath(path, output_dir)
    grouped = defaultdict(list)
    for e in entries:
        cid = 0
        if e.shot and e.shot.cluster_id:
            cid = e.shot.cluster_id
        grouped[cid].append(e)
    html = tpl.render(entries=entries, grouped=grouped, clusters=[k for k in grouped.keys()], now=datetime.utcnow().isoformat(timespec="seconds")+"Z", rel=rel)
    out = os.path.join(output_dir, "aquapy_report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    dump = os.path.join(output_dir, "aquapy_session.json")
    with open(dump, "w", encoding="utf-8") as f:
        json.dump([e.__dict__ for e in entries], f, default=lambda o: o.__dict__, indent=2)
    return out
