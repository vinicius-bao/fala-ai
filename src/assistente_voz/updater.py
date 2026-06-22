"""Verificação de atualização via GitHub Releases (somente stdlib).

``parse_version`` e ``is_newer`` são puros e testáveis. As funções de rede
isolam o acesso ao GitHub.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

_API = "https://api.github.com/repos/{repo}/releases/latest"
_HEADERS = {"User-Agent": "FalaAI-Updater", "Accept": "application/vnd.github+json"}


@dataclass
class Release:
    version: str
    notes: str
    page_url: str
    installer_url: str | None


def parse_version(s: str) -> tuple[int, ...]:
    """'v1.2.3' / '1.2.3-beta' -> (1, 2, 3)."""
    s = s.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts = []
    for chunk in s.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return a > b


def fetch_latest_release(repo: str, timeout: float = 10.0) -> Release | None:
    """Consulta o release mais recente de 'usuario/repo' no GitHub."""
    req = urllib.request.Request(_API.format(repo=repo), headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tag = data.get("tag_name") or data.get("name") or ""
    if not tag:
        return None
    installer = None
    for asset in data.get("assets", []):
        if (asset.get("name") or "").lower().endswith(".exe"):
            installer = asset.get("browser_download_url")
            break
    return Release(
        version=tag,
        notes=(data.get("body") or "").strip(),
        page_url=data.get("html_url") or "",
        installer_url=installer,
    )


def download_file(url: str, dest_path: str, timeout: float = 120.0) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    return dest_path
