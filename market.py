"""预设市场：在线搜索、导入、删除云绘图提示词预设。

市场索引是一个 JSON 文件（默认放在本仓库的 market/presets.json），导入的预设存到
data/plugin_data/astrbot_plugin_comfyui_draw/user_presets.json，插件更新也不会丢。
"""
import json
import re
import time

import aiohttp

from astrbot.api import logger

from . import presets
from .errors import ComfyUIError

DEFAULT_MARKET_URLS = [
    "https://raw.githubusercontent.com/koichinoi/astrbot_plugin_comfyui_draw/main/market/presets.json",
    "https://cdn.jsdelivr.net/gh/koichinoi/astrbot_plugin_comfyui_draw@main/market/presets.json",
]
MARKET_MAX_BYTES = 1024 * 1024
MARKET_CACHE_SECONDS = 600
MARKET_PAGE_SIZE = 15
PRESET_NAME_RE = re.compile(r"^[^\s\-/\\][^\s/\\]{0,11}$")
PRESET_SIZE_RE = re.compile(r"^\d{3,4}x\d{3,4}$")


class PresetMarketMixin:
    # ------------------------------------------------------------------ #
    # 导入预设的持久化与合并
    # ------------------------------------------------------------------ #
    def _user_presets_path(self):
        return self._data_path("user_presets.json")

    def _load_user_presets(self):
        data = self._load_json(self._user_presets_path(), {})
        return data if isinstance(data, dict) else {}

    def _builtin_preset_words(self):
        """内置预设已占用的名字、别名和指令（统一小写），导入时不能撞上。"""
        words = {name.lower() for name in presets.CLOUD_PROMPT_PRESETS}
        words.update(presets.CLOUD_PROMPT_PRESET_ALIASES)
        words.update(flag[2:] for flag in presets.CLOUD_PROMPT_PRESET_FLAGS)
        words.update(flag[2:] for flag in presets.CLOUD_SIZE_PRESETS)
        words.update(flag.lstrip("-") for flag in presets.FLAG_ALIASES)
        return words

    @staticmethod
    def _clean_preset(raw):
        """校验并整理一条预设，返回 dict 或 None（不合规的直接丢弃）。"""
        if not isinstance(raw, dict):
            return None
        name = str(raw.get("name", "") or "").strip()
        prompt = str(raw.get("prompt", "") or "").strip()
        size = str(raw.get("size", "") or "1024x1024").strip().lower()
        if not PRESET_NAME_RE.match(name) or "{subject}" not in prompt or len(prompt) > 4000:
            return None
        if not PRESET_SIZE_RE.match(size):
            size = "1024x1024"
        aliases = []
        for alias in raw.get("aliases") or []:
            alias = str(alias or "").strip()
            if PRESET_NAME_RE.match(alias) and alias.lower() != name.lower() and alias not in aliases:
                aliases.append(alias)
        tags = [str(t).strip() for t in raw.get("tags") or [] if str(t).strip()]
        return {
            "name": name,
            "desc": str(raw.get("desc", "") or "").strip()[:40] or name,
            "size": size,
            "prompt": prompt,
            "icon": str(raw.get("icon", "") or "").strip()[:4] or "📥",
            "aliases": aliases[:6],
            "tags": tags[:12],
        }

    def _refresh_imported_presets(self):
        """把导入的预设合并进实例上的预设表；内置预设优先，撞名的导入项跳过。"""
        table = dict(presets.CLOUD_PROMPT_PRESETS)
        aliases = dict(presets.CLOUD_PROMPT_PRESET_ALIASES)
        flags = dict(presets.CLOUD_PROMPT_PRESET_FLAGS)
        taken = self._builtin_preset_words()
        imported = {}
        for name, raw in self._load_user_presets().items():
            item = self._clean_preset({**(raw if isinstance(raw, dict) else {}), "name": name})
            if not item or name.lower() in taken:
                continue
            taken.add(name.lower())
            table[name] = item
            flags[f"--{name.lower()}"] = name
            for alias in item["aliases"]:
                if alias.lower() in taken:
                    continue
                taken.add(alias.lower())
                aliases[alias.lower()] = name
                flags[f"--{alias.lower()}"] = name
            imported[name] = item
        self.CLOUD_PROMPT_PRESETS = table
        self.CLOUD_PROMPT_PRESET_ALIASES = aliases
        self.CLOUD_PROMPT_PRESET_FLAGS = flags
        self._imported_presets = imported

    def _imported_preset_names(self):
        return list(getattr(self, "_imported_presets", {}) or {})

    # ------------------------------------------------------------------ #
    # 市场索引
    # ------------------------------------------------------------------ #
    def _market_urls(self):
        raw = self.config.get("preset_market_urls", None)
        if isinstance(raw, str):
            raw = raw.replace(",", " ").split()
        urls = [str(u).strip() for u in (raw or []) if str(u).strip().startswith("https://")]
        return urls or list(DEFAULT_MARKET_URLS)

    async def _fetch_market_text(self, url):
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise ComfyUIError(f"HTTP {resp.status}")
                body = await resp.content.read(MARKET_MAX_BYTES + 1)
                if len(body) > MARKET_MAX_BYTES:
                    raise ComfyUIError("索引文件超过 1MB")
                return body.decode("utf-8")

    async def _market_index(self, force=False):
        """拉取市场索引（按顺序尝试各地址，10 分钟内复用缓存），返回整理好的预设列表。"""
        cache = getattr(self, "_market_cache", None)
        if cache and not force and time.time() - cache[0] < MARKET_CACHE_SECONDS:
            return cache[1]
        errors = []
        for url in self._market_urls():
            try:
                data = json.loads(await self._fetch_market_text(url))
            except Exception as e:  # noqa: BLE001
                errors.append(f"{url}：{e}")
                continue
            entries = data.get("presets") if isinstance(data, dict) else data
            items, seen = [], set()
            for raw in entries if isinstance(entries, list) else []:
                item = self._clean_preset(raw)
                if item and item["name"] not in seen:
                    seen.add(item["name"])
                    items.append(item)
            self._market_cache = (time.time(), items)
            return items
        logger.warning("[comfyui_draw] 预设市场拉取失败：" + "；".join(errors))
        raise ComfyUIError("预设市场连不上，请稍后再试，或在插件配置 preset_market_urls 换一个镜像地址。")

    @staticmethod
    def _market_match(items, keyword):
        words = [w.casefold() for w in keyword.split() if w]
        if not words:
            return list(items)
        result = []
        for item in items:
            hay = " ".join([item["name"], item["desc"], *item["aliases"], *item["tags"]]).casefold()
            if all(w in hay for w in words):
                result.append(item)
        return result

    def _market_status(self, item):
        if item["name"] in self._imported_preset_names():
            return "已导入"
        if item["name"].lower() in self._builtin_preset_words():
            return "与内置重名"
        return ""
