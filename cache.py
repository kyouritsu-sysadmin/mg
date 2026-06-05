# cache.py
import hashlib
import json
import time
from pathlib import Path
from typing import Any

class ImageCache:

    def __init__(self, cache_dir: Path, ttl_days: int = 7):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_days * 86400
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Key generation ────────────────────────────────────────────

    def _content_key(self, image_path: Path, task_id: str) -> str:
        """
        Key = first 16 chars of SHA256(image bytes) + task_id.
        Same image + same task always hits. Different task = different entry.
        """
        image_hash = hashlib.sha256(
            image_path.read_bytes()
        ).hexdigest()[:16]
        return f"{task_id}_{image_hash}"

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    # ── Core operations ───────────────────────────────────────────

    def get(self, image_path: Path, task_id: str) -> dict | None:
        """Return cached result or None if missing or expired."""
        path = self._cache_path(self._content_key(image_path, task_id))
        if not path.exists():
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - entry["cached_at"] > self.ttl_seconds:
            path.unlink(missing_ok=True)   # expired
            return None
        return entry["result"]

    def set(self, image_path: Path, task_id: str, result: dict) -> None:
        """Write result atomically — safe for parallel tasks."""
        key  = self._content_key(image_path, task_id)
        path = self._cache_path(key)
        entry = {
            "key":       key,
            "source":    image_path.name,   # human-readable, not used as key
            "task_id":   task_id,
            "cached_at": time.time(),
            "result":    result,
        }
        # Atomic write: write to .tmp then rename
        # rename() is atomic on Linux/macOS — parallel tasks won't corrupt
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(entry, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        tmp.rename(path)

    def exists(self, image_path: Path, task_id: str) -> bool:
        """Quick existence check without loading the full result."""
        path = self._cache_path(self._content_key(image_path, task_id))
        if not path.exists():
            return False
        entry = json.loads(path.read_text(encoding="utf-8"))
        return time.time() - entry["cached_at"] <= self.ttl_seconds

    def invalidate(self, image_path: Path, task_id: str) -> None:
        """Force re-processing of a specific image + task combination."""
        path = self._cache_path(self._content_key(image_path, task_id))
        path.unlink(missing_ok=True)

    def clear(self) -> None:
        """Wipe the entire cache — use when drawings change."""
        for f in self.cache_dir.glob("*.json"):
            f.unlink()