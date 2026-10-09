"""Windows compatibility shim for the gltest direct runner.

``gltest.direct.loader._inject_message_to_fd0`` writes the transaction message
to a temp file, ``dup2``s it onto stdin (fd 0), then deletes the temp file.
That delete succeeds on POSIX, where an open file can be unlinked, but fails on
Windows with ``PermissionError`` because fd 0 still holds the file open.

The delete is not needed for the test to run: the file is released when the
process exits. We therefore downgrade that single ``os.unlink`` failure to a
no-op on Windows so the direct runner can load contracts there too.

The second shim makes ``direct_vm.warp()`` drive the contract's view of time.
Contracts read the transaction timestamp from ``gl.message_raw['datetime']``,
which the runner decodes from stdin once at import. ``warp`` updates the VM's
internal clock but not that decoded dict, so a contract that reads the raw
message would never see the warped time. We sync it so timeout logic is
testable.
"""

import os
import sys

if sys.platform == "win32":
    _real_unlink = os.unlink

    def _tolerant_unlink(path, *args, **kwargs):
        try:
            return _real_unlink(path, *args, **kwargs)
        except PermissionError:
            # The injected stdin temp file is still open; it will be reclaimed
            # by the OS when the process exits.
            return None

    os.unlink = _tolerant_unlink


try:
    from gltest.direct.vm import VMContext as _VMContext
except ImportError:  # pragma: no cover - runner not installed
    _VMContext = None

if _VMContext is not None:
    _original_warp = _VMContext.warp

    def _warp(self, timestamp):
        _original_warp(self, timestamp)
        module = sys.modules.get("genlayer.gl")
        if module is None:
            return
        raw = getattr(module, "message_raw", None)
        if isinstance(raw, dict):
            raw["datetime"] = timestamp

    _VMContext.warp = _warp
