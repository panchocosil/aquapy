from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class Target:
    host: str
    url: str

@dataclass
class PreflightResult:
    url: str
    ok: bool
    status: Optional[int] = None
    reason: Optional[str] = None
    headers: Dict[str,str] = field(default_factory=dict)
    title: Optional[str] = None
    tls_issuer: Optional[str] = None
    tls_subject: Optional[str] = None
    final_url: Optional[str] = None
    body_path: Optional[str] = None
    headers_path: Optional[str] = None
    technologies: List[dict] = field(default_factory=list)

@dataclass
class ShotResult:
    url: str
    path: Optional[str]
    width: int
    height: int
    phash: Optional[str] = None
    error: Optional[str] = None
    cluster_id: Optional[int] = None

@dataclass
class Entry:
    preflight: PreflightResult
    shot: Optional[ShotResult] = None
