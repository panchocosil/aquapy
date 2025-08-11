from __future__ import annotations
import asyncio, ssl, os
import httpx
from typing import List, Optional
from .models import Target, PreflightResult
from .utils import extract_title
from .fingerprints import Fingerprinter

def _url_from_host_port(host: str, port: int) -> str:
    scheme = "https" if port in (443, 8443, 9443, 12443) else "http"
    default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    return f"{scheme}://{host}" if default_port else f"{scheme}://{host}:{port}"

def expand_targets_line(line: str, ports: list[int]) -> List[Target]:
    line = line.strip()
    if not line: return []
    if line.startswith("http://") or line.startswith("https://"):
        return [Target(host=line.split("://",1)[1].split("/",1)[0], url=line)]
    return [Target(host=line, url=_url_from_host_port(line, p)) for p in ports]

def _classify_error(e: Exception) -> str:
    s = str(e).lower()
    if "timed out" in s or "timeout" in s: return "timeout"
    if "dns" in s or "name or service not known" in s or "getaddrinfo failed" in s: return "dns"
    if "ssl" in s or "certificate" in s or "tls" in s: return "tls"
    if "connection refused" in s or "connect" in s or "reset by peer" in s: return "network"
    return "other"

async def _http_get(url: str, headers: dict, timeout_ms: int, proxy: Optional[str], retries: int, follow_redirects: bool) -> httpx.Response:
    last_exc = None
    transport = httpx.AsyncHTTPTransport(retries=0)
    async with httpx.AsyncClient(follow_redirects=follow_redirects, timeout=timeout_ms/1000, verify=True, transport=transport, proxies=proxy) as client:
        for attempt in range(retries+1):
            try:
                r = await client.get(url, headers=headers)
                return r
            except Exception as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(0.25 * (attempt+1))
                else:
                    raise
    raise last_exc

async def probe_target(target: Target, timeout_ms: int, save_body: bool, out_dir: str, debug=False, proxy: Optional[str]=None, retries_http: int = 2, fingerprints_path: Optional[str]=None, follow_redirects: bool = False) -> PreflightResult:
    headers = {"User-Agent":"aquapy/0.5.0"}
    tls_issuer = tls_subject = None
    final_url = None
    body_path = None
    headers_path = None
    try:
        r = await _http_get(target.url, headers=headers, timeout_ms=timeout_ms, proxy=proxy, retries=retries_http, follow_redirects=follow_redirects)
        final_url = str(r.url)
        # TLS peek (best-effort)
        if final_url.startswith("https://"):
            try:
                hostname = r.url.host
                port = r.url.port or 443
                ctx = ssl.create_default_context()
                reader, writer = await asyncio.open_connection(hostname, port, ssl=ctx, server_hostname=hostname)
                cert = writer.get_extra_info("peercert")
                if cert:
                    tls_subject = str(cert.get("subject"))
                    tls_issuer = str(cert.get("issuer"))
                writer.close(); await writer.wait_closed()
            except Exception:
                pass
        title = extract_title(r.text or "") if "text/html" in (r.headers.get("content-type","").lower()) else None
        # Save headers/body
        os.makedirs(os.path.join(out_dir, "headers"), exist_ok=True)
        os.makedirs(os.path.join(out_dir, "html"), exist_ok=True)
        safe = (final_url or target.url).replace("://","_").replace("/","_")
        headers_path = os.path.join(out_dir, "headers", f"{safe}.txt")
        with open(headers_path, "w", encoding="utf-8") as hf:
            for k,v in r.headers.items():
                hf.write(f"{k}: {v}\n")
        if save_body:
            body_path = os.path.join(out_dir, "html", f"{safe}.html")
            try:
                with open(body_path, "wb") as bf:
                    bf.write(r.content)
            except Exception:
                body_path = None
        # Fingerprinting
        techs = []
        try:
            fp = Fingerprinter(fingerprints_path) if fingerprints_path else None
            if fp:
                techs = fp.detect(headers={k:v for k,v in r.headers.items()}, html=(r.text or ""))
        except Exception:
            pass
        return PreflightResult(
            url=target.url, ok=True, status=r.status_code, reason=r.reason_phrase,
            headers={k:v for k,v in r.headers.items()}, title=title, tls_issuer=tls_issuer,
            tls_subject=tls_subject, final_url=final_url, body_path=body_path, headers_path=headers_path,
            technologies=techs
        )
    except Exception as e:
        return PreflightResult(url=target.url, ok=False, reason=str(e), status=None, headers={}, title=None, tls_issuer=None, tls_subject=None, final_url=final_url)
