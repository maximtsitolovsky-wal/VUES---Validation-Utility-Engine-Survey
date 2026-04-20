"""instance_lock.py — Single-instance coordination for VUES.

Prevents duplicate polling when multiple instances try to run against
the same Airtable base. Uses a lock file with heartbeat mechanism.

Enterprise deployment patterns:
1. Single machine: Lock file prevents duplicate instances
2. Multi-machine: Use INSTANCE_LOCK_TYPE=airtable (requires schema change)
3. Kubernetes: Use leader election sidecar

The lock file contains:
- Instance ID (unique per process)
- PID
- Start time
- Last heartbeat
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def generate_instance_id() -> str:
    """Generate a unique instance ID for this process.
    
    Format: hostname-pid-uuid[:8]
    Example: DESKTOP-ABC-12345-a1b2c3d4
    """
    hostname = socket.gethostname()[:20]
    pid = os.getpid()
    short_uuid = uuid.uuid4().hex[:8]
    return f"{hostname}-{pid}-{short_uuid}"


class InstanceLock:
    """File-based lock to ensure single-instance operation.
    
    Usage:
        lock = InstanceLock(lock_dir)
        if not lock.acquire():
            print(f"Another instance is running: {lock.owner_info()}")
            sys.exit(1)
        # ... run application ...
        # Lock is auto-released on exit via atexit
    
    The lock includes a heartbeat mechanism. If the owning process dies
    without releasing the lock, a new instance can claim it after the
    heartbeat timeout (default: 2 minutes).
    """
    
    LOCK_FILE = "vues.lock"
    HEARTBEAT_INTERVAL = 30  # seconds
    HEARTBEAT_TIMEOUT = 120  # seconds — lock is stale after this
    
    def __init__(self, lock_dir: Path | str) -> None:
        self.lock_dir = Path(lock_dir)
        self.lock_file = self.lock_dir / self.LOCK_FILE
        self.instance_id = generate_instance_id()
        self._heartbeat_thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._acquired = False
    
    def acquire(self, force: bool = False) -> bool:
        """Attempt to acquire the instance lock.
        
        Args:
            force: If True, steal the lock even if another instance owns it.
                   Use with caution — may cause duplicate processing.
        
        Returns:
            True if lock acquired, False if another instance holds it.
        """
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for existing lock
        if self.lock_file.exists() and not force:
            existing = self._read_lock()
            if existing and not self._is_stale(existing):
                log.warning(
                    "Lock held by another instance: %s (pid=%s, started=%s)",
                    existing.get("instance_id"),
                    existing.get("pid"),
                    existing.get("started_at"),
                )
                return False
            elif existing:
                log.info(
                    "Stale lock detected (last heartbeat: %s). Claiming...",
                    existing.get("last_heartbeat"),
                )
        
        # Write our lock
        self._write_lock()
        self._acquired = True
        
        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="instance-heartbeat",
        )
        self._heartbeat_thread.start()
        
        # Register cleanup
        atexit.register(self.release)
        
        log.info(
            "Instance lock acquired: %s (lock_file=%s)",
            self.instance_id,
            self.lock_file,
        )
        return True
    
    def release(self) -> None:
        """Release the instance lock."""
        if not self._acquired:
            return
        
        self._shutdown.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)
        
        try:
            if self.lock_file.exists():
                # Only delete if we own it
                existing = self._read_lock()
                if existing and existing.get("instance_id") == self.instance_id:
                    self.lock_file.unlink()
                    log.info("Instance lock released: %s", self.instance_id)
        except Exception as exc:
            log.warning("Could not release lock file: %s", exc)
        
        self._acquired = False
    
    def owner_info(self) -> dict[str, Any] | None:
        """Return info about the current lock owner, or None if unlocked."""
        if not self.lock_file.exists():
            return None
        return self._read_lock()
    
    def _write_lock(self) -> None:
        """Write lock file with current instance info."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "instance_id": self.instance_id,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "started_at": now,
            "last_heartbeat": now,
            "version": "7.0.0",
        }
        self.lock_file.write_text(json.dumps(data, indent=2))
    
    def _read_lock(self) -> dict[str, Any] | None:
        """Read and parse lock file."""
        try:
            return json.loads(self.lock_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            return None
    
    def _is_stale(self, lock_data: dict[str, Any]) -> bool:
        """Check if lock is stale (heartbeat timeout exceeded)."""
        last_hb = lock_data.get("last_heartbeat")
        if not last_hb:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - last_time).total_seconds()
            return age > self.HEARTBEAT_TIMEOUT
        except (ValueError, TypeError):
            return True
    
    def _heartbeat_loop(self) -> None:
        """Background thread that updates the lock file heartbeat."""
        while not self._shutdown.wait(timeout=self.HEARTBEAT_INTERVAL):
            try:
                existing = self._read_lock()
                if existing and existing.get("instance_id") == self.instance_id:
                    existing["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                    self.lock_file.write_text(json.dumps(existing, indent=2))
            except Exception as exc:
                log.debug("Heartbeat update failed: %s", exc)


def check_single_instance(lock_dir: Path | str) -> InstanceLock:
    """Convenience function to acquire lock or exit.
    
    Usage in main.py:
        from siteowlqa.instance_lock import check_single_instance
        lock = check_single_instance(cfg.log_dir)
        # If we get here, we own the lock
    """
    lock = InstanceLock(lock_dir)
    if not lock.acquire():
        owner = lock.owner_info()
        print(
            f"\n❌ Another VUES instance is already running!\n"
            f"   Instance: {owner.get('instance_id') if owner else 'unknown'}\n"
            f"   PID:      {owner.get('pid') if owner else 'unknown'}\n"
            f"   Started:  {owner.get('started_at') if owner else 'unknown'}\n"
            f"\n"
            f"   To force takeover (dangerous): set VUES_FORCE_LOCK=1\n"
            f"   Lock file: {lock.lock_file}\n"
        )
        import sys
        sys.exit(1)
    return lock
