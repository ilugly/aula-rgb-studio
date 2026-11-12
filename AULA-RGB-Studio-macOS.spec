# Build with PyInstaller on macOS.
a = Analysis(
    ["app.py"],
    datas=[("web", "web"), ("assets", "assets")],
    hiddenimports=["pystray._darwin"],
    excludes=["aula_hid"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, exclude_binaries=True, name="AULA-RGB-Studio", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="AULA-RGB-Studio", upx=False)
app = BUNDLE(
    coll,
    name="AULA RGB Studio.app",
    icon="assets/icon.png",
    bundle_identifier="dev.ilugly.aula-rgb-studio",
    info_plist={"LSUIElement": True},
)
