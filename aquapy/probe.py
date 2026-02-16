from __future__ import annotations
import asyncio, contextlib, ssl, os
import httpx
from typing import List, Optional
from .models import Target, PreflightResult
from .utils import extract_title, debug_log
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

def _no_verify_ssl_context() -> ssl.SSLContext:
    """Context that skips cert verification; does not load system CAs (avoids 'unable to get local issuer')."""
    proto = getattr(ssl, "PROTOCOL_TLS_CLIENT", ssl.PROTOCOL_TLS)
    ctx = ssl.SSLContext(proto)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def _ssl_verify_for_httpx(verify: bool | str) -> bool | str | ssl.SSLContext:
    """Value for httpx verify: True, CA path (str), or SSL context that skips verification."""
    if verify is True:
        return True
    if isinstance(verify, str) and verify:
        return verify
    return _no_verify_ssl_context()

@contextlib.contextmanager
def _no_verify_env():
    """Temporarily unset CA-related env vars so nothing in the stack (ssl, certifi, httpcore) can use them."""
    saved = {}
    for key in ("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "REQUESTS_CA_BUNDLE_PATH"):
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        yield
    finally:
        os.environ.update(saved)

async def _http_get(url: str, headers: dict, timeout_ms: int, proxy: Optional[str], retries: int, follow_redirects: bool, verify=True) -> httpx.Response:
    last_exc = None
    verify_val = _ssl_verify_for_httpx(verify)
    transport = httpx.AsyncHTTPTransport(retries=0)
    trust_env = verify is True or (isinstance(verify, str) and bool(verify))
    # When -ssl: also temporarily unset CA env vars so no layer can override our no-verify context
    no_verify_env = not trust_env
    for attempt in range(retries+1):
        try:
            with (_no_verify_env() if no_verify_env else contextlib.nullcontext()):
                async with httpx.AsyncClient(follow_redirects=follow_redirects, timeout=timeout_ms/1000, verify=verify_val, transport=transport, proxies=proxy, trust_env=trust_env) as client:
                    r = await client.get(url, headers=headers)
                    return r
        except Exception as e:
            last_exc = e
            if attempt < retries:
                await asyncio.sleep(0.25 * (attempt+1))
            else:
                raise
    raise last_exc

async def probe_target(target: Target, timeout_ms: int, save_body: bool, out_dir: str, debug=False, proxy: Optional[str]=None, retries_http: int = 2, fingerprints_path: Optional[str]=None, follow_redirects: bool = False, ca_bundle_path: Optional[str]=None, verify_ssl: bool = True) -> PreflightResult:
    headers = {"User-Agent":"aquapy/0.5.0"}
    tls_issuer = tls_subject = None
    final_url = None
    body_path = None
    headers_path = None
    verify = False if not verify_ssl else (ca_bundle_path if ca_bundle_path else True)
    debug_log(debug, f"probe GET {target.url} verify={verify!r}")
    try:
        r = await _http_get(target.url, headers=headers, timeout_ms=timeout_ms, proxy=proxy, retries=retries_http, follow_redirects=follow_redirects, verify=verify)
        final_url = str(r.url)
        debug_log(debug, f"probe {target.url} -> status={r.status_code} final_url={final_url}")
        if final_url != target.url:
            debug_log(debug, f"probe redirect: {target.url} -> {final_url}")
        # TLS peek (best-effort)
        if final_url.startswith("https://"):
            try:
                hostname = r.url.host
                port = r.url.port or 443
                if verify_ssl:
                    ctx = ssl.create_default_context()
                    if ca_bundle_path:
                        ctx.load_verify_locations(cafile=ca_bundle_path)
                else:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                reader, writer = await asyncio.open_connection(hostname, port, ssl=ctx, server_hostname=hostname)
                cert = writer.get_extra_info("peercert")
                if cert:
                    tls_subject = str(cert.get("subject"))
                    tls_issuer = str(cert.get("issuer"))
                writer.close(); await writer.wait_closed()
                debug_log(debug, f"probe TLS issuer={tls_issuer!r} subject={tls_subject!r}")
            except Exception as te:
                debug_log(debug, f"probe TLS peek failed: {te}")
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
        except Exception as fe:
            debug_log(debug, f"probe fingerprint error: {fe}")
        debug_log(debug, f"probe saved headers={headers_path} body={body_path} techs={len(techs)}")
        return PreflightResult(
            url=target.url, ok=True, status=r.status_code, reason=r.reason_phrase,
            headers={k:v for k,v in r.headers.items()}, title=title, tls_issuer=tls_issuer,
            tls_subject=tls_subject, final_url=final_url, body_path=body_path, headers_path=headers_path,
            technologies=techs
        )
    except Exception as e:
        debug_log(debug, f"probe FAIL {target.url}: {e}")
        return PreflightResult(url=target.url, ok=False, reason=str(e), status=None, headers={}, title=None, tls_issuer=None, tls_subject=None, final_url=final_url)
