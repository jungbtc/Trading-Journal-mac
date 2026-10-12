"""Build one standalone universal Mac app and a drag-to-Applications DMG."""
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
DIST = ROOT / "dist"
RUNTIMES = {
    "arm64": ("aarch64", "81a359f1cfadd4da11766534c5913791cea55f26e1bb902cacd2a531bb1e4b2b"),
    "x86_64": ("x86_64", "65b195c9cedc1fef6767f044f9822069adbd1bd9204d424ece4628776fdc04bb"),
}
VERSION = "1.0.1"


def run(*args):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def runtime(arch, target, digest):
    archive = BUILD / f"python-{arch}.tar.gz"
    if not archive.exists():
        cached = Path(f"/private/tmp/tj-python-{arch}.tar.gz")
        if cached.exists():
            shutil.copyfile(cached, archive)
        else:
            url = ("https://github.com/astral-sh/python-build-standalone/releases/download/20260901/"
                   f"cpython-3.12.14%2B20260901-{target}-apple-darwin-install_only_stripped.tar.gz")
            urllib.request.urlretrieve(url, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Runtime checksum failed: {archive}. Delete it and rebuild.")
    destination = BUILD / f"runtime-{arch}"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    run("tar", "-xzf", archive, "--strip-components=1", "-C", destination)
    return destination


def main():
    BUILD.mkdir(exist_ok=True)
    DIST.mkdir(exist_ok=True)
    app = DIST / "Trading Journal.app"
    if app.exists():
        shutil.rmtree(app)
    contents = app / "Contents"
    resources = contents / "Resources"
    executables = contents / "MacOS"
    executables.mkdir(parents=True)
    resources.mkdir()
    code = resources / "app"
    code.mkdir()
    for name in ("src", "web", "seed", "tools"):
        shutil.copytree(ROOT / name, code / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    for name in ("VERSION", "config.example.json", ".env.example", "LICENSE"):
        shutil.copyfile(ROOT / name, code / name)
    shutil.copyfile(ROOT / "macos/desktop.py", resources / "desktop.py")
    shutil.copyfile(ROOT / "macos/READ ME.txt", resources / "READ ME.txt")
    shutil.copytree(ROOT / "macos/licenses", resources / "licenses")
    for arch, (target, digest) in RUNTIMES.items():
        shutil.copytree(runtime(arch, target, digest), resources / f"runtime-{arch}", symlinks=True)
        run("swiftc", "-O", "-target", f"{arch}-apple-macosx12.0", "-module-cache-path", BUILD / "swift-cache",
            ROOT / "macos/TradingJournal.swift", "-o", BUILD / f"TradingJournal-{arch}")
    run("lipo", "-create", BUILD / "TradingJournal-arm64", BUILD / "TradingJournal-x86_64",
        "-output", executables / "TradingJournal")
    run("swiftc", "-O", "-module-cache-path", BUILD / "swift-cache", ROOT / "macos/icon.swift", "-o", BUILD / "draw-icon")
    run(BUILD / "draw-icon", BUILD / "AppIcon.png")
    iconset = BUILD / "AppIcon.iconset"
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            run("sips", "-z", str(size * scale), str(size * scale), BUILD / "AppIcon.png", "--out",
                iconset / f"icon_{size}x{size}{suffix}.png")
    run("iconutil", "-c", "icns", iconset, "-o", resources / "AppIcon.icns")
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump({
            "CFBundleName": "Trading Journal", "CFBundleDisplayName": "Trading Journal",
            "CFBundleIdentifier": "com.jungbtc.tradingjournal", "CFBundleExecutable": "TradingJournal",
            "CFBundlePackageType": "APPL", "CFBundleShortVersionString": VERSION, "CFBundleVersion": "2",
            "CFBundleIconFile": "AppIcon", "LSMinimumSystemVersion": "12.0", "NSHighResolutionCapable": True,
            "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
            "NSHumanReadableCopyright": "Original project © 2026 tj-bot contributors. Mac packaging © 2026 jungbtc. MIT License.",
        }, f)
    identity = os.environ.get("CODE_SIGN_IDENTITY", "-")
    signing_options = [] if identity == "-" else ["--options", "runtime", "--timestamp"]
    # Sign inside out: never re-sign a nested binary after the bundle has been sealed.
    for path in sorted(resources.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as f:
            magic = f.read(4)
        if magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"):
            entitlements = ["--entitlements", ROOT / "macos/python.entitlements.plist"] if path.name == "python3.12" else []
            run("codesign", "--force", "--sign", identity, *signing_options, *entitlements, path)
    run("codesign", "--force", "--sign", identity, *signing_options, app)
    run("codesign", "--verify", "--deep", "--strict", app)
    stage = BUILD / "dmg"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copytree(app, stage / app.name, symlinks=True)
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    shutil.copyfile(ROOT / "macos/READ ME.txt", stage / "READ ME.txt")
    dmg = DIST / f"Trading-Journal-{VERSION}-universal.dmg"
    run("hdiutil", "create", "-volname", "Trading Journal", "-srcfolder", stage, "-format", "UDZO", "-ov", dmg)
    run("codesign", "--force", "--sign", identity, "--identifier", "com.jungbtc.tradingjournal.dmg",
        *([] if identity == "-" else ["--timestamp"]), dmg)
    run("codesign", "--verify", "--strict", dmg)
    run("hdiutil", "verify", dmg)
    checksum = hashlib.sha256(dmg.read_bytes()).hexdigest()
    dmg.with_suffix(".dmg.sha256").write_text(f"{checksum}  {dmg.name}\n")
    print(f"\nReady to share: {dmg}")


if __name__ == "__main__":
    main()
