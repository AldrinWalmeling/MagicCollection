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

    # Diretório principal do projeto
    pathex=[
        str(PROJECT_DIR),
    ],

    # Binários adicionais
    binaries=[],

    # Arquivos adicionais
    datas=[],

    # Imports que o PyInstaller não encontra automaticamente
    hiddenimports=[],

    # Hooks personalizados
    hookspath=[],

    hooksconfig={},

    runtime_hooks=[],

    # Módulos que queremos excluir
    excludes=[],

    # Mantém o arquivo Python em archive
    noarchive=False,

    # Otimização
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
    name="MagicCollection",

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

    # =====================================================
    # ASSETS
    # =====================================================

    Tree(
        str(ASSETS_DIR),
        prefix="assets",
    ),

    # =====================================================
    # CONFIGURAÇÕES
    # =====================================================

    strip=False,

    upx=True,

    upx_exclude=[],

    # Nome da pasta final
    name="MagicCollection",
)