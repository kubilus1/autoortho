"""
A virtual file system that serves .dds files from a tile cache
"""

import os
import re
import sys
import time
import logging
import argparse
import threading
import traceback
from functools import wraps, lru_cache, cache, cached_property
from pathlib import Path, PureWindowsPath

from winfspy import (
    FileSystem,
    BaseFileSystemOperations,
    enable_debug_log,
    FILE_ATTRIBUTE,
    CREATE_FILE_CREATE_OPTIONS,
    NTStatusObjectNameNotFound,
    NTStatusDirectoryNotEmpty,
    NTStatusNotADirectory,
    NTStatusObjectNameCollision,
    NTStatusAccessDenied,
    NTStatusEndOfFile,
    NTStatusMediaWriteProtected,
)
from winfspy.plumbing.win32_filetime import filetime_now
from winfspy.plumbing.security_descriptor import SecurityDescriptor

import getortho
from aoconfig import CFG

def operation(fn):
    """Decorator for file system operations.

    Provides both logging and thread-safety
    """
    name = fn.__name__

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        head = args[0] if args else None
        tail = args[1:] if args else ()
        try:
            if self.biglock:
                with self._thread_lock:
                    result = fn(self, *args, **kwargs)
            else:
                result = fn(self, *args, **kwargs)
        except Exception as exc:
            traceback.print_exc()
            logging.info(f" NOK | {name:20} | {head!r:20} | {tail!r:20} | {exc!r}")
            raise
        else:
            logging.info(f" OK! | {name:20} | {head!r:20} | {tail!r:20} | {result!r}")
            return result

    return wrapper


class BaseFileObj:

    @property
    def name(self):
        """File name, without the path"""
        return self.path.name

    @property
    def file_name(self):
        """File name, including the path"""
        return str(self.path)

    def __init__(self, path, attributes, security_descriptor):
        self.path = path
        self.attributes = attributes
        self.security_descriptor = security_descriptor
        now = filetime_now()
        self.creation_time = now
        self.last_access_time = now
        self.last_write_time = now
        self.change_time = now
        self.index_number = 0
        self.file_size = 0
        self.allocation_size = 0

    def get_file_info(self):
        return {
            "file_attributes": self.attributes,
            "allocation_size": self.allocation_size,
            "file_size": self.file_size,
            "creation_time": self.creation_time,
            "last_access_time": self.last_access_time,
            "last_write_time": self.last_write_time,
            "change_time": self.change_time,
            "index_number": self.index_number,
        }

    def __repr__(self):
        return f"{type(self).__name__}:{self.file_name}"


class FileObj(BaseFileObj):
    def __init__(self, path, attributes, security_descriptor, allocation_size=0):
        super().__init__(path, attributes, security_descriptor)
        self.attributes |= FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE
        assert not self.attributes & FILE_ATTRIBUTE.FILE_ATTRIBUTE_DIRECTORY

class OpenedTileObj:
    tile = None
    fh = None

    def __init__(self, file_obj, row, col, maptype, zoom, fsops):
        self.file_obj = file_obj
        self.row = row
        self.col = col
        self.maptype = maptype
        self.zoom = zoom
        self.fsops = fsops

    def __repr__(self):
        return f"{type(self).__name__}:{self.file_obj.file_name}"

    def close(self):
        if self.tile != None:
            self.fsops.tc._close_tile(self.row, self.col, self.maptype, self.zoom)
            self.tile = None

        if self.fh != None:
            self.fh.close()
            self.fh = None

    def read(self, offset, length):
        self.fsops.read_tile_cnt += 1
        if offset == 0 and length < 40000:
            self.fsops.read_tile_short_cnt += 1

        # delayed open to make get_size cheap
        if self.fh == None and self.tile == None:
            dds_name = self.fsops.cache_dir + self.file_obj.file_name
            if os.path.exists(dds_name):
                print(f"DIRECT ACCESS: {dds_name}")
                self.fh = open(dds_name, "rb")
                self.fsops.open_tile_direct_cnt += 1

        if self.fh == None and self.tile == None:
            self.tile = self.fsops.tc._get_tile(self.row, self.col, self.maptype, self.zoom)
            #print(f"Open: {self.tile}")
            self.fsops.open_tile_cache_cnt += 1

        if self.fh != None:
            self.fh.seek(offset)
            return self.fh.read(length)

        if self.tile != None:
            return self.tile.read_dds_bytes(offset, length)

    def get_size(self):
        self.fsops.get_size_tile_cnt += 1
        return 22369744

class OpenedFileObj:
    def __init__(self, file_obj, handle, fsops):
        self.file_obj = file_obj
        self.handle = handle
        self.fsops = fsops

    def __repr__(self):
        return f"{type(self).__name__}:{self.file_obj.file_name}"

    def close(self):
        if self.handle != None:
            #print(f"Closing {self}  FH: {self.handle}")
            self.handle.close()
            self.handle = None

    def read(self, offset, length):
        self.fsops.read_file_cnt += 1
        #print(f"Read {self}  FH: {self.handle}")
        self.handle.seek(offset)
        return self.handle.read(length)

    def get_size(self):
        self.fsops.get_size_file_cnt += 1
        #print(f"Size {self}  FH: {self.handle}")
        self.handle.seek(0, 2)
        return self.handle.tell()

class AutoorthoOperations(BaseFileSystemOperations):
    open_tile_cache_cnt = 0
    open_tile_direct_cnt = 0
    open_file_cnt = 0
    read_tile_cnt = 0
    read_tile_short_cnt = 0
    read_file_cnt = 0
    get_size_file_cnt = 0
    get_size_tile_cnt = 0

    def __init__(self, root, volume_label, tile_cache, read_only=False):
        super().__init__()
        if len(volume_label) > 31:
            raise ValueError("`volume_label` must be 31 characters long max")

        max_file_nodes = 1024
        max_file_size = 16 * 1024 * 1024
        file_nodes = 1

        self._volume_info = {
            "total_size": max_file_nodes * max_file_size,
            "free_size": (max_file_nodes - file_nodes) * max_file_size,
            "volume_label": volume_label,
        }

        self.read_only = read_only
        self.root = root
        self._root_path = PureWindowsPath("/")
        self.root_security_descr = SecurityDescriptor.from_string("O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;WD)")

        self._thread_lock = threading.RLock()
        self.dds_re = re.compile(".*\\\(\d+)[-_](\d+)[-_]((?!ZL)\S*)(\d{2}).dds")
        self.tc = tile_cache
        self.cache_dir = CFG.paths.cache_dir

        # Do lots of locking
        self.biglock = False

    # Winfsp operations

    @cache
    def get_volume_info(self):
        return self._volume_info

    #@operation
    def set_volume_label(self, volume_label):
        self._volume_info["volume_label"] = volume_label

    #@operation
    def get_security_by_name(self, file_name):
        #print(f"GET_SECURITY_BY_NAME: {file_name}")
        file_name = PureWindowsPath(file_name)
        file_obj = FileObj(file_name, FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE,
                               self.root_security_descr)
        return (
            file_obj.attributes,
            file_obj.security_descriptor.handle,
            file_obj.security_descriptor.size,
        )

    #@operation
    @cache
    def get_security(self, file_context):
        #print(file_context.file_obj.security_descriptor)
        return file_context.file_obj.security_descriptor

    #@operation
    def open(self, file_name, create_options, granted_access):
        #print(f"OPEN: {file_name} {create_options} {granted_access}")
        file_name = PureWindowsPath(file_name)

        path = str(file_name)

        m = self.dds_re.match(path)
        if m:
            #print(f"MATCH! {path}")
            row, col, maptype, zoom = m.groups()
            row = int(row)
            col = int(col)
            zoom = int(zoom)
            file_obj = FileObj(file_name, FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE,
                               self.root_security_descr)
            return OpenedTileObj(file_obj, row, col, maptype, zoom, self)

        full_path = self._full_path(path)
        exists = os.path.exists(full_path)

        if not exists:
             raise NTStatusObjectNameNotFound()
        else:
            #print(f"OPEN: {file_name} {full_path}")
            #file_obj = self.add_obj(path, self._root_path, False)
            file_obj = FileObj(file_name, FILE_ATTRIBUTE.FILE_ATTRIBUTE_ARCHIVE,
                               self.root_security_descr)
            self.open_file_cnt += 1
            return OpenedFileObj(file_obj, open(full_path, "rb"), self)

        # what now? the directory stuff is currently unsupported
        return None

    #@operation
    def close(self, file_context):
        #print(f"CLOSE: {file_context}")
        file_context.close()

    #@operation
    def get_file_info(self, file_context):
        #print(f"GET_FILE_INFO: {file_context}")
        file_context.file_obj.file_size = file_context.get_size()
        return file_context.file_obj.get_file_info()

    def _full_path(self, partial):
        #print(f"_FULL_PATH: {partial}")
        if partial.startswith("\\"):
            partial = partial[1:]
        path = os.path.abspath(os.path.join(self.root, partial))
        return path

    #@operation
    def read(self, file_context, offset, length):
        #print(f"READ: P:{file_context.file_obj.path} O:{offset} L:{length}")
        return file_context.read(offset, length)

    #@operation
    def cleanup(self, file_context, file_name, flags) -> None:
        #print(f"CLEANUP: {file_context} {file_name} {flags}")
        return

    #@operation
    def flush(self, file_context) -> None:
        pass

    def show_stats(self):
        print("Tile:")
        print(f" open_cache\t{self.open_tile_cache_cnt}")
        print(f" open_direct\t{self.open_tile_direct_cnt}")
        print(f" read\t\t{self.read_tile_cnt}")
        print(f" read_short\t{self.read_tile_short_cnt}")
        print(f" get_size\t{self.get_size_tile_cnt}\n")
        print("File:")
        print(f" open\t\t{self.open_file_cnt}")
        print(f" read\t\t{self.read_file_cnt}")
        print(f" get_size\t{self.get_size_file_cnt}")

        method_list = [method for method in dir(AutoorthoOperations) if
                method.startswith('_') is False]

        #self.tc.show_stats()
        for m_name in method_list:
            m = getattr(self, m_name)
            if hasattr(m, 'cache_info'):
                print(f"{m_name}: {m.cache_info()}")

def create_file_system(
    root, mountpoint, label="autoortho", prefix="", verbose=True, debug=False, testing=False):
    if debug:
        enable_debug_log()

    if verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    # The avast workaround is not necessary with drives
    # Also, it is not compatible with winfsp-tests
    root = Path(root)
    mountpoint = Path(mountpoint)
    is_drive = mountpoint.parent == mountpoint
    reject_irp_prior_to_transact0 = not is_drive and not testing
    tc = getortho.TileCacher(".cache")

    operations = AutoorthoOperations(str(root), label, tc)
    fs = FileSystem(
        str(mountpoint),
        operations,
        sector_size=512,
        sectors_per_allocation_unit=1,
        volume_creation_time=filetime_now(),
        volume_serial_number=0,
        file_info_timeout=1000,
        case_sensitive_search=1,
        case_preserved_names=1,
        unicode_on_disk=1,
        persistent_acls=1,
        #post_cleanup_when_modified_only=1,
        um_file_context_is_user_context2=1,
        flush_and_purge_on_cleanup=1,
        file_system_name=str(mountpoint),
        prefix=prefix,
        debug=debug,
        reject_irp_prior_to_transact0=reject_irp_prior_to_transact0,
        # security_timeout_valid=1,
        # security_timeout=10000,
    )
    return fs


def main(root, mountpoint, label="autoorotho", prefix="", verbose=False, debug=False):
    debug=False
    fs = create_file_system(root, mountpoint, label, prefix, verbose, debug)
    try:
        print("Starting FS")
        fs.start()
        print("FS started, keep it running forever")
        while True:
            result = input("AO> ").lower()
            if result == "s":
                fs.operations.show_stats()
            elif result == "q":
                break

    finally:
        print("Stopping FS")
        fs.stop()
        print("FS stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("mountpoint")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-l", "--label", type=str, default="memfs")
    parser.add_argument("-p", "--prefix", type=str, default="")
    args = parser.parse_args()
    main(args.root, args.mountpoint, args.label, args.prefix, args.verbose, args.debug)
