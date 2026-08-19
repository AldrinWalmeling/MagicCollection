# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree


# =========================================================
# CAMINHOS
# =========================================================

PROJECT_DIR = Path.cwd()

ASSETS_DIR = PROJECT_DIR / "assets"


# =========================================================
# ANÁLISE
# =========================================================

a = Analysis(
    [
        "main.py",
    ],

    pathex=[
        str(PROJECT_DIR),
    ],

    binaries=[],

    datas=[
        (
            str(PROJECT_DIR / "ui" / "theme.qss"),
            "ui",
        ),
    ],

    hiddenimports=[],

    hookspath=[],

    hooksconfig={},

    runtime_hooks=[],

    excludes=[],

    noarchive=False,

    optimize=0,
)


# =========================================================
# PYZ
# =========================================================

pyz = PYZ(
    a.pure,
)


# =========================================================
# EXECUTÁVEL
# =========================================================

exe = EXE(
    pyz,

    a.scripts,

    [],

    # Os binários serão colocados pelo COLLECT
    exclude_binaries=True,

    # Nome do executável
    name="Magic Collection",

    # Não mostrar console
    console=False,

    # Debug
    debug=False,

    # Bootloader
    bootloader_ignore_signals=False,

    # Não remover símbolos
    strip=False,

    # UPX
    upx=True,

    # Traceback em aplicações windowed
    disable_windowed_traceback=False,

    # Windows
    argv_emulation=False,

    target_arch=None,

    # Assinatura
    codesign_identity=None,

    entitlements_file=None,

    # Ícone
    icon=str(
        ASSETS_DIR
        / "icons"
        / "icon_app.ico"
    ),
)


# =========================================================
# COLETA FINAL
# =========================================================

coll = COLLECT(
    exe,

    a.binaries,

    a.datas,

    Tree(
        str(ASSETS_DIR),
        prefix="assets",
    ),

    strip=False,

    upx=True,

    upx_exclude=[],

    name="Magic Collection",
)