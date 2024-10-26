# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['autoortho/autoortho.py'],
    pathex=[],
    binaries=[
            ('autoortho/lib/darwin_universal/libispc_texcomp.dylib', '.'),  # Adjust destination path if needed
            ('autoortho/aoimage/aoimage.dylib', '.'),
            ('autoortho/imgs/splash.png', 'imgs'),
            ('autoortho/imgs/banner1.png', 'imgs'),
        ],
    datas=[],
    hiddenimports=['socketio', 'flask_socketio','engineio.async_threading', 'socketio.async_threading','engineio.async_eventlet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='autoortho',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
