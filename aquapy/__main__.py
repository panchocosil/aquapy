from __future__ import annotations
import argparse, asyncio, sys, os, json, multiprocessing
from pathlib import Path
from typing import List
from .config import Settings, PORT_ALIASES
from .models import Entry, PreflightResult, ShotResult
from .probe import expand_targets_line, probe_target
from .screenshot import screenshot_url
from .report import render_report
from .utils import extract_targets_from_text
from .nmap_masscan import parse_open_ports
from .cluster import cluster_phashes

VERSION = "0.5.0"

async def worker(q: asyncio.Queue, settings: Settings, out_dir: str, entries: list[Entry], fingerprints_path: str):
    shots_dir = os.path.join(out_dir, "screenshots"); os.makedirs(shots_dir, exist_ok=True)
    while True:
        item = await q.get()
        if item is None:
            q.task_done(); break
        target = item
        pre = await probe_target(target, timeout_ms=settings.http_timeout_ms, save_body=settings.save_body, out_dir=out_dir, debug=settings.debug, proxy=settings.proxy, retries_http=settings.retries_http, fingerprints_path=fingerprints_path, follow_redirects=settings.follow_redirects)
        shot = None
        if pre.ok:
            fname = (pre.final_url or target.url).replace("://","_").replace("/","_") + ".png"
            path = os.path.join(shots_dir, fname)
            shot = await screenshot_url(pre.final_url or target.url, path, settings.resolution[0], settings.resolution[1], settings.user_agent, timeout_ms=settings.screenshot_timeout_ms, proxy=settings.proxy, chrome_path=settings.chrome_path, full_page=settings.full_page, profile=settings.profile, retries=settings.retries_shot)
        entries.append(Entry(preflight=pre, shot=shot))
        if not settings.silent and pre.ok:
            print(pre.final_url or pre.url)
        q.task_done()

def parse_ports(arg: str) -> List[int]:
    if arg in PORT_ALIASES:
        return PORT_ALIASES[arg]
    try:
        ports = [int(x.strip()) for x in arg.split(",") if x.strip()]
        return ports
    except Exception:
        raise SystemExit(f"Invalid -ports value: {arg}")

def env_default_out() -> str:
    return os.path.expanduser(os.environ.get("AQUATONE_OUT_PATH","."))

async def run(args):
    ports = parse_ports(args.ports)
    conc = args.threads if args.threads else (multiprocessing.cpu_count() or 8)
    res_w, res_h = (int(x) for x in args.resolution.split(",",1))
    settings = Settings(
        concurrency=conc,
        http_timeout_ms=args.http_timeout,
        screenshot_timeout_ms=args.screenshot_timeout,
        scan_timeout_ms=args.scan_timeout,
        ports=ports,
        resolution=(res_w, res_h),
        proxy=args.proxy,
        chrome_path=args.chrome_path,
        save_body=args.save_body,
        template_path=args.template_path,
        debug=args.debug,
        silent=args.silent,
        full_page=args.full_page,
        profile=args.profile,
        retries_http=args.retries_http,
        retries_shot=args.retries_shot,
        phash_threshold=args.phash_threshold,
        follow_redirects=args.redirect
    )
    out_dir = os.path.expanduser(args.out or env_default_out())
    os.makedirs(out_dir, exist_ok=True)

    fingerprints_path = args.fingerprints or str(Path(__file__).with_name("assets") / "wappalyzer_min.json")

    if args.session:
        with open(args.session, "r", encoding="utf-8") as f:
            raw = json.load(f)
        entries = []
        for item in raw:
            pre = item.get("preflight") if "preflight" in item else item
            shot = item.get("shot")
            pre_obj = PreflightResult(**pre)
            shot_obj = ShotResult(**shot) if shot else None
            entries.append(Entry(preflight=pre_obj, shot=shot_obj))
        _assign_clusters(entries, settings.phash_threshold)
        report_path = render_report(entries, out_dir, args.template_path or str(Path(__file__).with_name("templates")))
        print(report_path)
        return

    lines: List[str] = []
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        data = sys.stdin.read()
        lines = data.splitlines()

    targets = []
    if args.nmap:
        if args.input and os.path.exists(args.input):
            sources = [args.input]
        else:
            text = "\n".join(lines).strip()
            if text.startswith("<?xml") or "<nmaprun" in text or "<masscan" in text:
                sources = [text]
            else:
                sources = [ln.strip() for ln in lines if ln.strip()]
        for src in sources:
            mapping = parse_open_ports(src)
            for host, open_ports in mapping.items():
                for p in open_ports:
                    targets.extend(expand_targets_line(host, [p]))
    else:
        extracted = []
        for line in lines:
            extracted.extend(extract_targets_from_text(line))
        if not extracted:
            extracted = [l for l in lines if l.strip()]
        for item in extracted:
            targets.extend(expand_targets_line(item, ports))

    q: asyncio.Queue = asyncio.Queue()
    for t in targets:
        await q.put(t)
    for _ in range(settings.concurrency):
        await q.put(None)
    entries: list[Entry] = []
    tasks = [asyncio.create_task(worker(q, settings, out_dir, entries, fingerprints_path)) for _ in range(settings.concurrency)]
    await q.join()
    for t in tasks: await t

    _assign_clusters(entries, settings.phash_threshold)

    urls_path = os.path.join(out_dir, "aquatone_urls.txt")
    with open(urls_path, "w", encoding="utf-8") as uf:
        for e in entries:
            if e.preflight.ok:
                uf.write(f"{e.preflight.final_url or e.preflight.url}\n")

    report_path = render_report(entries, out_dir, args.template_path or str(Path(__file__).with_name("templates")))
    if not settings.silent:
        print(report_path)
    session_path = os.path.join(out_dir, "aquatone_session.json")
    with open(session_path, "w", encoding="utf-8") as sf:
        json.dump([e.__dict__ for e in entries], sf, default=lambda o: o.__dict__, indent=2)

def _assign_clusters(entries: List[Entry], threshold: int):
    items = []
    for idx, e in enumerate(entries):
        ph = e.shot.phash if (e.shot and e.shot.phash) else None
        if ph:
            items.append((idx, ph))
    mapping = cluster_phashes(items, threshold=threshold) if items else {}
    for idx, cid in mapping.items():
        if entries[idx].shot:
            entries[idx].shot.cluster_id = cid

def main():
    ap = argparse.ArgumentParser(prog="aquapy", description="Aquatone-style site flyovers (Chromium)")
    ap.add_argument("-version", action="store_true", help="Print current version")
    ap.add_argument("-chrome-path", dest="chrome_path", help="Full path to Chrome/Chromium executable")
    ap.add_argument("-debug", action="store_true", help="Print debugging information")
    ap.add_argument("-http-timeout", type=int, default=3000, help="Timeout ms for HTTP requests (default 3000)")
    ap.add_argument("-nmap", action="store_true", help="Parse input as Nmap/Masscan XML")
    ap.add_argument("-out", default=None, help='Directory to write files to (default "." or AQUATONE_OUT_PATH)')
    ap.add_argument("-ports", default="medium", help='Ports to scan: list "80,443,..." or alias small|medium|large|xlarge (default "medium")')
    ap.add_argument("-proxy", default=None, help="Proxy to use for HTTP requests (e.g. http://127.0.0.1:8080)")
    ap.add_argument("-resolution", default="1440,900", help='Screenshot resolution (default "1440,900")')
    ap.add_argument("-save-body", dest="save_body", action=argparse.BooleanOptionalAction, default=True, help="Save response bodies (default true)")
    ap.add_argument("-scan-timeout", type=int, default=100, help="Timeout ms for port scans (placeholder, default 100)")
    ap.add_argument("-screenshot-timeout", type=int, default=30000, help="Timeout ms for screenshots (default 30000)")
    ap.add_argument("-session", help="Load aquatone session JSON and generate HTML report")
    ap.add_argument("-silent", action="store_true", help="Suppress all output except errors")
    ap.add_argument("-template-path", help="Path to HTML template to use for report")
    ap.add_argument("-threads", type=int, default=None, help="Number of concurrent threads (default logical CPUs)")
    ap.add_argument("-i","--input", dest="input", help="File with input lines (if omitted, read STDIN)")
    # extras
    ap.add_argument("-full-page", action="store_true", help="Take full-page screenshots (default viewport only)")
    ap.add_argument("-profile", choices=["desktop","mobile"], default="desktop", help="Screenshot profile (desktop|mobile)")
    ap.add_argument("-retries-http", type=int, default=2, help="HTTP preflight retry attempts on errors (default 2)")
    ap.add_argument("-retries-shot", type=int, default=1, help="Screenshot retry attempts (default 1)")
    ap.add_argument("-phash-threshold", type=int, default=10, help="Hamming distance for clustering pHash (default 10)")
    ap.add_argument("-fingerprints", help="Path to Wappalyzer JSON (defaults to built-in minimal database)")
    ap.add_argument("-redirect", action="store_true", help="Follow HTTP redirects (default: do not follow)")

    args = ap.parse_args()
    if args.version:
        print(VERSION)
        return
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
