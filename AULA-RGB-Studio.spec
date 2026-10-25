# PyInstaller build: one windowed .exe with the page, fonts and icon inside.  Run build.bat.
a = Analysis(
    ["app.py"],
    datas=[("web", "web"), ("assets/icon.ico", "assets")],
    hiddenimports=["pystray._win32"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name="AULA-RGB-Studio",
    icon="assets/icon.ico",
    console=False,
    upx=False,
)
