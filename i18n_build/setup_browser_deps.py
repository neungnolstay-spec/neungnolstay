#!/usr/bin/env python3
"""Playwright용 chromium 실행에 필요한 시스템 라이브러리를 사용자 공간에 내려받는다.

root/apt 없이 Debian 패키지(.deb)를 워크스페이스에 풀어 LD_LIBRARY_PATH로 연결한다.
ldd 로 부족한 라이브러리를 반복 확인하며 필요한 패키지만 추가한다.

    python3 i18n_build/setup_browser_deps.py
    LD_LIBRARY_PATH=$PWD/.cache/chromedeps/usr/lib/x86_64-linux-gnu python3 i18n_build/check.py
"""
from __future__ import annotations

import io
import lzma
import os
import re
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
DEST = CACHE / "chromedeps"
DEBCACHE = CACHE / "debs"
INDEX = "https://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages.xz"
LIBDIR = DEST / "usr" / "lib" / "x86_64-linux-gnu"

CHROME = Path.home() / ".cache/ms-playwright/chromium_headless_shell-1255/chrome-headless-shell-linux64/chrome-headless-shell"

# soname → Debian package
SONAME_PKG = {
    "libnspr4.so": "libnspr4",
    "libnss3.so": "libnss3",
    "libnssutil3.so": "libnss3",
    "libsmime3.so": "libnss3",
    "libssl3.so": "libnss3",
    "libXcomposite.so.1": "libxcomposite1",
    "libXdamage.so.1": "libxdamage1",
    "libXfixes.so.3": "libxfixes3",
    "libXrandr.so.2": "libxrandr2",
    "libXrender.so.1": "libxrender1",
    "libX11.so.6": "libx11-6",
    "libX11-xcb.so.1": "libx11-xcb1",
    "libXext.so.6": "libxext6",
    "libXau.so.6": "libxau6",
    "libXdmcp.so.6": "libxdmcp6",
    "libXi.so.6": "libxi6",
    "libXtst.so.6": "libxtst6",
    "libXss.so.1": "libxss1",
    "libxcb.so.1": "libxcb1",
    "libxcb-render.so.0": "libxcb-render0",
    "libxcb-shm.so.0": "libxcb-shm0",
    "libxcb-randr.so.0": "libxcb-randr0",
    "libxcb-xfixes.so.0": "libxcb-xfixes0",
    "libxcb-shape.so.0": "libxcb-shape0",
    "libxcb-glx.so.0": "libxcb-glx0",
    "libxcb-icccm.so.4": "libxcb-icccm4",
    "libxcb-image.so.0": "libxcb-image0",
    "libxcb-keysyms.so.1": "libxcb-keysyms1",
    "libxcb-util.so.1": "libxcb-util1",
    "libxcb-xkb.so.1": "libxcb-xkb1",
    "libxcb-sync.so.1": "libxcb-sync1",
    "libxcb-xinerama.so.0": "libxcb-xinerama0",
    "libxshmfence.so.1": "libxshmfence1",
    "libxkbcommon.so.0": "libxkbcommon0",
    "libxkbcommon-x11.so.0": "libxkbcommon-x11-0",
    "libasound.so.2": "libasound2",
    "libatk-1.0.so.0": "libatk1.0-0",
    "libatk-bridge-2.0.so.0": "libatk-bridge2.0-0",
    "libatspi.so.0": "libatspi2.0-0",
    "libdbus-1.so.3": "libdbus-1-3",
    "libglib-2.0.so.0": "libglib2.0-0",
    "libgobject-2.0.so.0": "libglib2.0-0",
    "libgio-2.0.so.0": "libglib2.0-0",
    "libgmodule-2.0.so.0": "libglib2.0-0",
    "libpcre2-8.so.0": "libpcre2-8-0",
    "libffi.so.8": "libffi8",
    "libpng16.so.16": "libpng16-16",
    "libjpeg.so.62": "libjpeg62-turbo",
    "libfreetype.so.6": "libfreetype6",
    "libfontconfig.so.1": "libfontconfig1",
    "libexpat.so.1": "libexpat1",
    "libuuid.so.1": "libuuid1",
    "libz.so.1": "zlib1g",
    "libbz2.so.1.0": "libbz2-1.0",
    "liblzma.so.5": "liblzma5",
    "libzstd.so.1": "libzstd1",
    "libsqlite3.so.0": "libsqlite3-0",
    "libcups.so.2": "libcups2",
    "libdrm.so.2": "libdrm2",
    "libgbm.so.1": "libgbm1",
    "libpango-1.0.so.0": "libpango-1.0-0",
    "libcairo.so.2": "libcairo2",
    "libharfbuzz.so.0": "libharfbuzz0b",
    "libpixman-1.so.0": "libpixman-1-0",
}


def ar_extract(path: Path, dest: Path) -> None:
    with path.open("rb") as f:
        assert f.read(8) == b"!<arch>\n"
        while True:
            hdr = f.read(60)
            if len(hdr) < 60:
                break
            name = hdr[:16].decode().strip().rstrip("/")
            size = int(hdr[48:58].decode().strip())
            data = f.read(size)
            if size % 2:
                f.read(1)
            if name.startswith("data.tar"):
                with tarfile.open(fileobj=io.BytesIO(data)) as tf:
                    tf.extractall(dest, filter="data")


def load_index() -> dict[str, dict]:
    cache = CACHE / "Packages.txt"
    if not cache.exists():
        print("index download…", flush=True)
        raw = urllib.request.urlopen(INDEX, timeout=240).read()
        cache.write_text(lzma.decompress(raw).decode("utf-8", "replace"))
    out: dict[str, dict] = {}
    for stanza in cache.read_text().split("\n\n"):
        if not stanza.strip():
            continue
        d = {}
        for line in stanza.split("\n"):
            if line.startswith(" ") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip()
        if d.get("Package"):
            out[d["Package"]] = d
    return out


def find_pkg(index: dict[str, dict], name: str) -> dict | None:
    for cand in (name, name + "t64"):
        if cand in index:
            return index[cand]
    return None


def missing_libs() -> set[str]:
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(LIBDIR)
    out = subprocess.run(["ldd", str(CHROME)], capture_output=True, text=True, env=env).stdout
    return set(re.findall(r"(\S+) => not found", out))


def main() -> None:
    for p in (DEST, DEBCACHE):
        p.mkdir(parents=True, exist_ok=True)
    index = load_index()
    fetched: set[str] = set()

    for round_no in range(8):
        missing = missing_libs()
        if not missing:
            print("all shared libraries resolved")
            break
        # 아직 못 받은 것 중 이름을 아는 것만
        todo = {}
        for so in sorted(missing):
            pkg = SONAME_PKG.get(so)
            if pkg and pkg not in fetched:
                todo[so] = pkg
        if not todo:
            print("⚠ unresolved without mapping:", sorted(missing))
            break
        print(f"round {round_no + 1}: {len(todo)} lib(s)", flush=True)
        for so, pkgname in todo.items():
            d = find_pkg(index, pkgname)
            if not d:
                print("  ! package not found:", pkgname)
                fetched.add(pkgname)
                continue
            deb = DEBCACHE / os.path.basename(d["Filename"])
            if not deb.exists():
                print("  fetch", pkgname, d["Version"], flush=True)
                urllib.request.urlretrieve("https://deb.debian.org/debian/" + d["Filename"], deb)
            ar_extract(deb, DEST)
            fetched.add(pkgname)

    print("deps ready:", LIBDIR, len(list(LIBDIR.glob("*.so*"))), "libs")
    print(f'LD_LIBRARY_PATH="{LIBDIR}"')


if __name__ == "__main__":
    main()
