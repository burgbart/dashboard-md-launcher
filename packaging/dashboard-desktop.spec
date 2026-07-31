# PyInstaller spec for the single-file dashboard-desktop executable.
# Build from the repo root:
#   pyinstaller packaging/dashboard-desktop.spec
# Output: dist/dashboard-desktop (dist/dashboard-desktop.exe on Windows)
# On macOS it additionally produces an installable dist/dashboard-desktop.app
# bundle (drag it into /Applications).

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH is set by PyInstaller

a = Analysis(
    [str(ROOT / "packaging" / "desktop_main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=["webview"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dashboard-desktop",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Dashboard Hub.app",
        bundle_identifier="com.dashboardhub.desktop",
        info_plist={
            "CFBundleName": "Dashboard Hub",
            "CFBundleDisplayName": "Dashboard Hub",
            "NSHighResolutionCapable": True,
        },
    )
