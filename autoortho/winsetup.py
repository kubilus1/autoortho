import os
import sys
from aoconfig import CFG

import logging
log = logging.getLogger(__name__)

from ctypes.util import find_library

def find_win_libs():

    if CFG.fuse.winfuse:
        log.info("WinFUSE requested, First looking for Dokan ...")
        _libfuse_path = find_library('dokanfuse2.dll')
        if _libfuse_path:
            log.info(f"Dokan found at {_libfuse_path}")
            return "dokan-FUSE", _libfuse_path

        log.info("Dokan not found, looking for WinFSP ...")


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
    _libfuse_path = Reg32GetValue(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp", r"InstallDir")
    if _libfuse_path:
        _libfuse_path += r"bin\winfsp-%s.dll" % ("x64" if sys.maxsize > 0xffffffff else "x86")
  
    if os.path.exists(_libfuse_path):
        log.info(f"Found WinFSP at {_libfuse_path}")
        if CFG.fuse.winfuse:
            log.info(f"WinFSP-FUSE mode.")
            return "winfsp-FUSE", _libfuse_path
        else:
            log.info(f"WinFSP Raw mode.")
            return "winfsp-raw", _libfuse_path

    log.warning(f"No required Windows libs detected.  Please install DokanyV2 or WinFSP.")
    return None, None


def setup_winfsp_mount(path):
    if os.path.lexists(path):
        # Windows cannot reliably determine if a directory exists or is empty or not (what a mess) so prompt before doing anything more.
        log.warning(f"Mount point {path} exists.  WinFSP requires mount point does not already exist.  Do you wish to remove it (y/n)?")
        clean = input(f"Removing existing mount point before proceeding? (y/n)")

        if clean.lower() == 'y':
            os.rmdir(path)
        else:
            log.error(f"Cannot proceed with clashing directory {path}.  Exiting.")
            input("Press any key to continue")
            sys.exit(1)


def setup_dokan_mount(path):
    if not os.path.lexists(path):
        log.info(f"Creating mountpoint for Dokan: {path}")
        os.makedirs(path)
