"""OS layer + system memory metrics.

We keep the original simulated allocator (OSLayer) used by the demo,
and add a safe way to read *system* RAM usage (no raw RAM access).
"""

from __future__ import annotations

from dataclasses import dataclass


class OSLayer:
    def __init__(self, total_memory: int = 1024):
        self.total_memory = total_memory
        self.allocated: dict[str, int] = {}

    def allocate(self, process_id: str, memory: int) -> bool:
        if memory <= self.total_memory:
            self.allocated[process_id] = memory
            return True
        return False

    def deallocate(self, process_id: str) -> None:
        if process_id in self.allocated:
            del self.allocated[process_id]


@dataclass(frozen=True)
class SystemMemorySnapshot:
    time: int  # epoch seconds
    used_mb: int
    total_mb: int
    percent: float


def get_system_memory_snapshot(now: int) -> SystemMemorySnapshot:
    """Return OS-reported system RAM metrics via psutil."""
    import psutil

    vm = psutil.virtual_memory()
    total_mb = int(vm.total / (1024 * 1024))
    used_mb = int(vm.used / (1024 * 1024))
    return SystemMemorySnapshot(time=now, used_mb=used_mb, total_mb=total_mb, percent=float(vm.percent))
