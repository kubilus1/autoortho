import os
import re
import sys
import time
import traceback

from functools import wraps, lru_cache
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
from winfspy.plumbing import ffi, NTStatusError, lib, NTSTATUS
from winfspy.operations import _STRING_ENCODING, configure_file_info, _catch_unhandled_exceptions



class OperationsShim(BaseFileSystemOperations):
    @_catch_unhandled_exceptions
    def ll_open(
        self, file_name, create_options, granted_access, p_file_context, file_info
    ) -> NTSTATUS:
        """
        Open a file or directory.
        """
        cooked_file_name = ffi.string(file_name)

        try:
            cooked_file_context = self.open(cooked_file_name, create_options, granted_access)

        except NTStatusError as exc:
            return exc.value

        file_context = ffi.new_handle(cooked_file_context)
        p_file_context[0] = file_context
        # Prevent GC on obj and it handle
        self._opened_objs[file_context] = cooked_file_context

        return self.ll_get_file_info(file_context, file_info)

    @_catch_unhandled_exceptions
    def ll_close(self, file_context) -> None:
        """
        Close a file.
        """
        cooked_file_context = ffi.from_handle(file_context)
        try:
            self.close(cooked_file_context)

        except NTStatusError as exc:
            return exc.value

        del self._opened_objs[file_context]

    @_catch_unhandled_exceptions
    def ll_read(self, file_context, buffer, offset, length, p_bytes_transferred) -> NTSTATUS:
        """
        Read a file.
        """
        cooked_file_context = ffi.from_handle(file_context)
        try:
            data = self.read(cooked_file_context, offset, length)

        except NTStatusError as exc:
            return exc.value

        ffi.memmove(buffer, data, len(data))
        p_bytes_transferred[0] = len(data)

        return NTSTATUS.STATUS_SUCCESS
