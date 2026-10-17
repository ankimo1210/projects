"""Private physical-storage growth guard; it never reduces financial scope."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from time import monotonic

MAX_STORAGE_BYTES = 30 * 1024**3
_ACTIVE_BUDGET = ContextVar("rbf04_storage_budget", default=None)


class StorageBudget:
    """Count unique allocated file bytes and stop unusually large saved runs.

    The default 30 GiB permits ordinary experiments. A larger study requires
    a deliberate revised storage plan; this administrative limit is not a
    financial cap or an acceptance result. Directory/VHD overhead is separate.
    """

    def __init__(self, directory, *, max_bytes=MAX_STORAGE_BYTES):
        if not isinstance(max_bytes, int) or max_bytes < 1:
            raise ValueError("positive physical storage budget required")
        self.directory = Path(directory).absolute()
        self.max_bytes = max_bytes
        self.used_bytes = 0
        self._inodes = {}
        self._transactions = []
        if any(p.is_symlink() for p in (self.directory, *self.directory.parents)):
            raise ValueError("symlink storage budget directory")
        start = monotonic()
        if self.directory.exists():
            for index, item in enumerate(self.directory.rglob("*")):
                if index >= 150000 or monotonic() - start > 15:
                    raise OSError("storage growth preflight requires a bounded inventory")
                if item.is_symlink():
                    raise ValueError("symlink storage budget entry")
                if item.is_file():
                    self._record(item)
        self._check()

    def _record(self, path):
        stat = path.stat()
        key = (stat.st_dev, stat.st_ino)
        physical = stat.st_blocks * 512
        previous = self._inodes.get(key, 0)
        for transaction in self._transactions:
            transaction.setdefault(key, self._inodes.get(key))
        self.used_bytes += physical - previous
        self._inodes[key] = physical

    def _check(self):
        if self.used_bytes > self.max_bytes:
            raise OSError(
                "storage growth exceeds the physical saved-run budget "
                f"({self.used_bytes} > {self.max_bytes} bytes); "
                "retain existing results and record a larger-storage plan before retrying"
            )

    @contextmanager
    def transaction(self, published_directory=None):
        """Release the accounting of an unpublished write that was removed."""
        journal = {}
        self._transactions.append(journal)
        try:
            yield
        except BaseException:
            # A post-publication cleanup failure must retain the saved bytes'
            # charges; only a writer whose final root is absent is rolled back.
            if published_directory is None or not Path(published_directory).exists():
                for key, previous in journal.items():
                    self.used_bytes -= self._inodes.get(key, 0)
                    if previous is None:
                        self._inodes.pop(key, None)
                    else:
                        self._inodes[key] = previous
                        self.used_bytes += previous
            raise
        finally:
            self._transactions.pop()

    def record_file(self, path):
        """Include one closed manifest in the same physical growth budget."""
        self._record(Path(path))
        self._check()

    def before_write(self):
        """Check the current budget before another immutable artifact starts."""
        self._check()

    def after_page(self, directory):
        """Check one closed shared page before its artifact is published.

        Only this writer's new page is inspected. A temporary page can exceed
        the bound by at most the existing protocol chunk limit before refusal;
        the transport then removes its own unpublished staging directory.
        """
        for filename in ("metadata.json", "arrays.npz", "receipt.json"):
            item = Path(directory) / filename
            if item.is_symlink() or not item.is_file():
                raise ValueError("invalid storage budget page")
            self._record(item)
        self._check()


def current_budget():
    """Return the current inclusive execution budget or None."""
    return _ACTIVE_BUDGET.get()


@contextmanager
def storage_scope(budget):
    """Restore the caller's storage scope even when writing fails."""
    token = _ACTIVE_BUDGET.set(budget)
    try:
        yield budget
    finally:
        _ACTIVE_BUDGET.reset(token)


def bounded_execution(function):
    """Apply one inclusive physical-storage budget to an experiment invocation."""

    @wraps(function)
    def execute(directory, *args, **kwargs):
        with storage_scope(StorageBudget(directory)):
            return function(directory, *args, **kwargs)

    return execute


def atomic_write(function):
    """Scope one immutable writer and undo only its removed temporary charges."""

    @wraps(function)
    def save(directory, *args, **kwargs):
        budget = current_budget() or StorageBudget(directory)
        budget.before_write()
        with storage_scope(budget), budget.transaction(directory):
            return function(directory, *args, **kwargs)

    return save
