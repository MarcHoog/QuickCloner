from textual.app import App
from typing import Optional

class _LogStream:
    """A lightweight stream that forwards print output to the app's Log widget.

    - Buffers partial writes until a newline, then emits a line to the Log.
    - Optionally masks a secret (PAT) using a provided mask function.
    - Optionally tees output to the original stream (so console still shows text).
    """

    def __init__(self, app: "App", mask_fn=None, secret: Optional[str] = None, tee=None) -> None:
        self.app = app
        self.mask_fn = mask_fn
        self.secret = secret
        self.tee = tee
        self._buffer: str = ""

        if not hasattr(app, "_log_line") or not callable(getattr(app, "_log_line", None)):
            raise AttributeError("App must have a callable '_log_line' method")

    def write(self, data: str) -> int:
        try:
            if self.tee is not None:
                self.tee.write(data)
        except Exception:
            pass

        if not isinstance(data, str):
            data = str(data)
        self._buffer += data
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line != "":
                self._emit(line)
        return len(data)

    def flush(self) -> None:
        try:
            if self.tee is not None and hasattr(self.tee, "flush"):
                self.tee.flush()
        except Exception:
            pass
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""

    def _emit(self, line: str) -> None:
        try:
            if self.secret and self.mask_fn:
                line = self.mask_fn(line, self.secret)
            self.app._log_line(line) # type: ignore | We validate this in the init if the call back exists
        except Exception:
            pass

    def isatty(self) -> bool:
        return False

    def fileno(self):
        try:
            return self.tee.fileno() if self.tee is not None else -1
        except Exception:
            return -1
