"""
Simple in-memory cache utility
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable
from functools import wraps


class SimpleCache:
    """
    简单的内存缓存实现
    
    特点:
    - 支持过期时间
    - 线程安全 (使用 asyncio.Lock)
    - 自动清理过期条目
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry["expires_at"] < datetime.utcnow():
                # 已过期，删除并返回 None
                del self._cache[key]
                return None
            
            return entry["value"]
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 过期时间（秒），默认1小时
        """
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds)
            }
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有缓存
        
        Args:
            pattern: 键前缀，如 "family:1:" 会删除所有以此开头的键
        
        Returns:
            删除的条目数量
        """
        async with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
    
    async def clear(self) -> None:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """清理所有过期的缓存条目"""
        async with self._lock:
            now = datetime.utcnow()
            keys_to_delete = [
                k for k, v in self._cache.items() 
                if v["expires_at"] < now
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)


# 全局缓存实例
cache = SimpleCache()


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


async def invalidate_family_expense_cache(family_id: int) -> None:
    """
    当支出数据变更时，清除该家庭的支出相关缓存
    
    应在以下场景调用:
    - 新增支出
    - 更新支出
    - 删除支出
    """
    await cache.delete_pattern(f"expense:trend:family:{family_id}")
    await cache.delete_pattern(f"expense:stats:family:{family_id}")

