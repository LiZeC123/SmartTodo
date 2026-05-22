import threading
import time
from typing import Any


class MemoryCache:
    """
    基于内存的缓存工具
    支持存储任意类型的 value 支持过期时间 线程安全
    """

    def __init__(self) -> None:
        """初始化缓存容器和线程锁"""
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.RLock()

    def _is_expired(self, expire_at: float | None) -> bool:
        """检查给定的过期时间戳是否已过期"""
        if expire_at is None:
            return False
        return time.time() > expire_at

    def set(self, key: str, value: Any, ex: int | None = None) -> None:
        """
        设置键值对 可选过期时间（秒）
        :param key: 键
        :param value: 值（任意类型）
        :param ex: 过期秒数 None 表示永不过期
        """
        expire_at: float | None = None
        if ex is not None:
            expire_at = time.time() + ex
        with self._lock:
            self._store[key] = (value, expire_at)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键对应的值 如果键不存在或已过期则返回 default
        """
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return default
            value, expire_at = item
            if self._is_expired(expire_at):
                # 过期则删除并返回默认值
                del self._store[key]
                return default
            return value

    def delete(self, *keys: str) -> int:
        """
        删除一个或多个键 返回成功删除的数量
        """
        if not keys:
            return 0
        deleted = 0
        with self._lock:
            for key in keys:
                if key in self._store:
                    del self._store[key]
                    deleted += 1
        return deleted

    def exists(self, key: str) -> bool:
        """
        判断键是否存在且未过期
        """
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return False
            _, expire_at = item
            if self._is_expired(expire_at):
                del self._store[key]
                return False
            return True

    def expire(self, key: str, seconds: int) -> bool:
        """
        为已存在的键设置过期时间（秒） 成功返回 True 键不存在或已过期返回 False
        """
        if seconds <= 0:
            return self.delete(key) > 0
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return False
            value, old_expire = item
            if self._is_expired(old_expire):
                del self._store[key]
                return False
            new_expire_at = time.time() + seconds
            self._store[key] = (value, new_expire_at)
            return True

    def ttl(self, key: str) -> int:
        """
        返回键剩余的过期秒数
        -2 表示键不存在或已过期
        -1 表示永不过期
        """
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return -2
            _, expire_at = item
            if self._is_expired(expire_at):
                del self._store[key]
                return -2
            if expire_at is None:
                return -1
            remaining = int(expire_at - time.time())
            return max(0, remaining)  # 避免负数

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._store.clear()

    def keys(self) -> list:
        """
        返回所有未过期的键列表（注意：会主动清理过期键）
        """
        with self._lock:
            valid_keys = []
            for key, (_, expire_at) in list(self._store.items()):
                if self._is_expired(expire_at):
                    del self._store[key]
                else:
                    valid_keys.append(key)
            return valid_keys

    def __len__(self) -> int:
        """返回当前未过期的键数量"""
        return len(self.keys())

    def __contains__(self, key: str) -> bool:
        """支持 `key in cache` 语法"""
        return self.exists(key)
