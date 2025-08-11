# aquapy — Aquatone-style flyovers (Chromium) — v0.5.0

Python re-implementation of Aquatone’s workflow with Chromium (Playwright): async HTTP preflight, screenshots, pHash clustering, basic Wappalyzer-like tech detection, and an interactive HTML report.

## Quick start (Python 3.12 recommended)
```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Examples
```bash
# Simple (no redirects by default)
cat hosts.txt | python -m aquapy -out out

# Follow redirects explicitly
cat hosts.txt | python -m aquapy -out out -redirect

# Nmap/Masscan
python -m aquapy -nmap -i scan.xml -out out
cat scan.xml | python -m aquapy -nmap -out out
```


## Installation (detailed)

### macOS (Apple Silicon / Intel)
```bash
# 1) Install Python 3.12 (recommended)
brew install python@3.12

# 2) Create and activate virtualenv
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate

# 3) Install Python deps + Chromium (Playwright)
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### Linux (Debian/Ubuntu-like)
```bash
# 1) Ensure Python 3.12 is available (use your distro or pyenv)
# sudo apt-get install -y python3.12 python3.12-venv  # if available on your distro
python3.12 -m venv .venv
source .venv/bin/activate

# 2) Install Python deps + Chromium (Playwright will fetch a compatible build)
python -m pip install -r requirements.txt
python -m playwright install chromium
```

> Tip: Si usas otra versión de Python y algo falla (p.ej. wheels), vuelve a 3.12.

### One-liners con Makefile
```bash
make setup-3.12 install
cat hosts.txt | make run ARGS='-out out -profile mobile -full-page'
make run INPUT=hosts.txt ARGS='-out out -redirect -ports large'
make run-nmap INPUT=scan.xml ARGS='-out out'
```

---

## CLI options

| Opción | Tipo / Default | Descripción |
|---|---|---|
| `-version` | flag | Imprime versión y sale |
| `-chrome-path` | string | Ruta a ejecutable de Chrome/Chromium (si no usas el de Playwright) |
| `-debug` | flag | Log adicional |
| `-http-timeout` | int, **3000** | Timeout (ms) para preflight HTTP |
| `-nmap` | flag | Interpreta la entrada como XML de Nmap/Masscan (ruta/s o contenido por STDIN) |
| `-out` | string, **"."**/`$AQUATONE_OUT_PATH` | Directorio de salida |
| `-ports` | lista o alias (**medium**) | Ej: `80,443,3000` o `small|medium|large|xlarge` |
| `-proxy` | string | Proxy HTTP(S) p.ej. `http://127.0.0.1:8080` |
| `-resolution` | `WxH`, **1440,900** | Tamaño del viewport si no usas perfiles |
| `-save-body` / `-no-save-body` | flag, **true** | Guardar HTML de respuesta |
| `-scan-timeout` | int, **100** | Placeholder (para futuros escaneos de puertos) |
| `-screenshot-timeout` | int, **30000** | Timeout (ms) de screenshots |
| `-session` | path | Cargar `aquatone_session.json` y generar reporte |
| `-silent` | flag | Suprimir salida (excepto errores) |
| `-template-path` | path | Ruta a templates HTML (por defecto, integrada) |
| `-threads` | int | Concurrencia. Default = CPUs lógicos |
| `-i`, `--input` | path | Archivo de entrada (si omites, lee de STDIN) |
| `-full-page` | flag | Captura full-page |
| `-profile` | `desktop`/`mobile`, **desktop** | Perfil de captura (viewport + UA) |
| `-retries-http` | int, **2** | Reintentos de preflight HTTP por error |
| `-retries-shot` | int, **1** | Reintentos de screenshot |
| `-phash-threshold` | int, **10** | Umbral Hamming para cluster por pHash |
| `-fingerprints` | path | JSON de Wappalyzer (si omites, usa el mínimo integrado) |
| `-redirect` | flag, **off** | **Seguir redirects**. Si no lo pasas, NO sigue redirects |

**Variables de entorno**:
- `AQUATONE_OUT_PATH`: directorio por defecto para `-out` cuando no se especifica.

### Nmap / Masscan
- Puedes pasar **ruta/s** al XML por `-i` o **contenido** por `STDIN`.
- Ejemplos:
  ```bash
  python -m aquapy -nmap -i scan.xml -out out
  printf '%s\n' scan1.xml scan2.xml | python -m aquapy -nmap -out out
  cat scan.xml | python -m aquapy -nmap -out out
  ```

---

## Reporte interactivo
- **Resumen global**: total, % por 2xx/3xx/4xx/5xx, top hosts y techs (tags clicables).
- **Filtros / búsqueda**: por texto (`/` para enfocar), status, tech y host.
- **Paginación**: tamaño configurable (All/100/200/500) + “Load more”.
- **Acciones por cluster**: Collapse/Expand, Open all, Copy URLs.
- **Tarjetas**: overlay con Open/HTML/Headers/Copy/Zoom, lightbox de capturas, badges de status y 🔒 HTTPS.
- **Export/Copy** de URLs filtradas, **dark mode** y vista compacta.

