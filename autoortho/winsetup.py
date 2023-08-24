import os
import sys
from aoconfig import CFG

import logging
log = logging.getLogger(__name__)

from ctypes.util import find_library

def find_win_libs():
    fuse_libs = []

    # Find dokan
    log.info("Looking for Dokan ...")
    _lib_dokan= find_library('dokanfuse2.dll')
    if _lib_dokan:
        log.info(f"Dokan found at {_lib_dokan}")
        fuse_libs.append(("dokan-FUSE", _lib_dokan))
    else:
        log.info("Dokan not found.") 

    log.info("Looking for WinFSP ...")
    # Find WinFSP
    try:
        import _winreg as reg
    except ImportError:
        import winreg as reg
    def Reg32GetValue(rootkey, keyname, valname):
        key, val = None, None
        try:
            key = reg.OpenKey(rootkey, keyname, 0, reg.KEY_READ | reg.KEY_WOW64_32KEY)
            val = str(reg.QueryValueEx(key, valname)[0])
        except WindowsError:
            pass
        finally:
            if key is not None:
                reg.CloseKey(key)
        return val
    _lib_winfsp = Reg32GetValue(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp", r"InstallDir")
    if _lib_winfsp:
        _lib_winfsp += r"bin\winfsp-%s.dll" % ("x64" if sys.maxsize > 0xffffffff else "x86")
        if os.path.exists(_lib_winfsp):
            log.info(f"Found WinFSP at {_lib_winfsp}")
            fuse_libs.append(("winfsp-FUSE", _lib_winfsp))
    else:
        log.info("WinFSP not found.")

    if not fuse_libs:
        log.error(f"No required Windows libs detected!  Please install DokanyV2 or WinFSP.")
        return None, None

    if CFG.windows.prefer_winfsp:
        fuse_libs.reverse()
    
    fusemode, fuselib = fuse_libs[0]
    log.info(f"Will use detected {fusemode} with libs {fuselib}")
    os.environ['FUSE_LIBRARY_PATH'] = fuselib
    return fusemode, fuselib


def setup_winfsp_mount(path):
    if os.path.lexists(path):
        # Windows cannot reliably determine if a directory exists or is empty or not (what a mess) so prompt before doing anything more.
        log.warning(f"Mount point {path} exists.  WinFSP requires mount point does not already exist. Renaming {path} to {path}_bkp")

        os.rename(
            path,
            f"{path}_bkp"
        )


def setup_dokan_mount(path):
    if not os.path.lexists(path):
        log.info(f"Creating mountpoint for Dokan: {path}")
        os.makedirs(path)
