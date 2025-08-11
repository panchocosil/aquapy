from dataclasses import dataclass, field
from typing import List, Optional

DEFAULT_PORTS: List[int] = [80, 443, 8000, 8080, 8443]

PORT_ALIASES = {
    "small": [80, 443],
    "medium": [80, 443, 8000, 8080, 8443],
    "large": [80, 81, 443, 591, 2082, 2087, 2095, 2096, 3000, 8000, 8001, 8008, 8080, 8083, 8443, 8834, 8888],
    "xlarge": [80, 81, 300, 443, 591, 593, 832, 981, 1010, 1311, 2082, 2087, 2095, 2096, 2480, 3000, 3128, 3333, 4243, 4567, 4711, 4712, 4993, 5000, 5104, 5108, 5800, 6543, 7000, 7396, 7474, 8000, 8001, 8008, 8014, 8042, 8069, 8080, 8081, 8088, 8090, 8091, 8118, 8123, 8172, 8222, 8243, 8280, 8281, 8333, 8443, 8500, 8834, 8880, 8888, 8983, 9000, 9043, 9060, 9080, 9090, 9091, 9200, 9443, 9800, 9981, 12443, 16080, 18091, 18092, 20720, 28017],
}

@dataclass
class Settings:
    concurrency: int = 8
    http_timeout_ms: int = 3000
    screenshot_timeout_ms: int = 30000
    scan_timeout_ms: int = 100
    ports: List[int] = field(default_factory=lambda: DEFAULT_PORTS.copy())
    resolution: tuple[int,int] = (1440, 900)
    user_agent: str = "aquapy/0.5.0 (Chromium via Playwright)"
    proxy: Optional[str] = None
    chrome_path: Optional[str] = None
    save_body: bool = True
    template_path: Optional[str] = None
    debug: bool = False
    silent: bool = False
    # extras
    full_page: bool = False
    profile: str = "desktop"
    retries_http: int = 2
    retries_shot: int = 1
    phash_threshold: int = 10
    follow_redirects: bool = False
