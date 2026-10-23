"""Offline checks for the preset market: /预设搜索, /预设导入, /预设删除 and merging."""
import json
import os
import sys
import tempfile
import unittest

from test_info_cards import carded, html_of
from test_cloud_profiles import run
from test_queue_and_history import UserEvent

market = sys.modules["comfyui_draw_plugin.market"]
presets = sys.modules["comfyui_draw_plugin.presets"]
templates = sys.modules["comfyui_draw_plugin.templates"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "market", "presets.json"), encoding="utf-8") as f:
    MARKET_TEXT = f.read()


class AdminEvent(UserEvent):
    def __init__(self, text, admin=True, uid="u1"):
        super().__init__(uid=uid, text=text, admin=admin)

    @staticmethod
    def image_result(path):
        return ("image", path)


def market_plugin(index_text=MARKET_TEXT, fail=False, **config):
    obj, rendered = carded(text_as_card=False, **config)
    tmp = tempfile.mkdtemp()
    obj._data_path = lambda name: os.path.join(tmp, name)
    calls = []

    async def fake_fetch(url):
        calls.append(url)
        if fail:
            raise RuntimeError("offline")
        return index_text

    obj._fetch_market_text = fake_fetch
    obj._refresh_imported_presets()
    return obj, rendered, calls


def plain(output):
    return "\n".join(item[1] for item in output if item[0] == "plain")


class MarketIndexTests(unittest.TestCase):
    def test_bundled_index_is_valid_and_has_no_builtin_clashes(self):
        data = json.loads(MARKET_TEXT)
        obj, _, _ = market_plugin()
        taken = obj._builtin_preset_words()
        names = set()
        for raw in data["presets"]:
            item = obj._clean_preset(raw)
            self.assertIsNotNone(item, raw.get("name"))
            self.assertNotIn(item["name"].lower(), taken)
            for alias in item["aliases"]:
                self.assertNotIn(alias.lower(), taken)
            self.assertNotIn(item["name"], names)
            names.add(item["name"])
        self.assertGreaterEqual(len(names), 10)

    def test_clean_preset_rejects_bad_entries(self):
        obj, _, _ = market_plugin()
        good = {"name": "测试", "prompt": "draw {subject}", "size": "1024x1536"}
        self.assertEqual(obj._clean_preset(good)["size"], "1024x1536")
        self.assertIsNone(obj._clean_preset({**good, "prompt": "no placeholder"}))
        self.assertIsNone(obj._clean_preset({**good, "name": "有 空格"}))
        self.assertIsNone(obj._clean_preset({**good, "name": "--坏"}))
        self.assertEqual(obj._clean_preset({**good, "size": "huge"})["size"], "1024x1024")

    def test_market_urls_only_https_with_fallback(self):
        obj, _, _ = market_plugin(preset_market_urls=["http://bad.example/p.json", "https://ok.example/p.json"])
        self.assertEqual(obj._market_urls(), ["https://ok.example/p.json"])
        obj, _, _ = market_plugin(preset_market_urls=[])
        self.assertEqual(obj._market_urls(), market.DEFAULT_MARKET_URLS)


class MarketCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_admin_is_refused(self):
        obj, _, calls = market_plugin()
        for handler, text in [(obj.preset_search, "/预设搜索 Q版"), (obj.preset_import, "/预设导入 1"),
                              (obj.preset_delete, "/预设删除 Q版")]:
            out = plain(await run(handler(AdminEvent(text, admin=False))))
            self.assertIn("只有管理员", out)
        self.assertEqual(calls, [])

    async def test_search_lists_matches_and_caches_index(self):
        obj, rendered, calls = market_plugin()
        out = await run(obj.preset_search(AdminEvent("/预设搜索 复古")))
        self.assertEqual(out, [("image", "card.png")])
        rows = rendered["data"]["sections"][0]["rows"]
        self.assertTrue(rows)
        self.assertTrue(all("复古" in r["desc"] or r["name"] for r in rows))
        self.assertIn("赛璐璐", " ".join(r["name"] for r in rows))
        await run(obj.preset_search(AdminEvent("/预设搜索")))
        self.assertEqual(len(calls), 1)

    async def test_search_no_match_and_offline(self):
        obj, _, _ = market_plugin()
        out = plain(await run(obj.preset_search(AdminEvent("/预设搜索 不存在的关键词xyz"))))
        self.assertIn("没有找到", out)
        obj, _, calls = market_plugin(fail=True)
        out = plain(await run(obj.preset_search(AdminEvent("/预设搜索"))))
        self.assertIn("预设市场连不上", out)
        self.assertEqual(len(calls), len(market.DEFAULT_MARKET_URLS))

    async def test_import_by_number_then_use_and_show_on_card(self):
        obj, rendered, _ = market_plugin()
        await run(obj.preset_search(AdminEvent("/预设搜索 浮世绘")))
        out = plain(await run(obj.preset_import(AdminEvent("/预设导入 1"))))
        self.assertIn("已导入：--浮世绘", out)
        with open(obj._data_path("user_presets.json"), encoding="utf-8") as f:
            self.assertIn("浮世绘", json.load(f))

        _prompt, opts = obj._parse_args("富士山下的少女 --浮世绘", cloud=True)
        self.assertEqual(opts["preset"], "浮世绘")
        _prompt, opts = obj._parse_args("富士山下的少女 --ukiyoe", cloud=True)
        self.assertEqual(opts["preset"], "浮世绘")
        prompt, name, size = obj._apply_cloud_prompt_preset("富士山下的少女", "浮世绘")
        self.assertEqual((name, size), ("浮世绘", "1536x1024"))
        self.assertIn("富士山下的少女", prompt)

        await run(obj.cloud_draw_presets(AdminEvent("/云绘图预设")))
        data = rendered["data"]
        self.assertEqual([i["name"] for i in data["imported_items"]], ["浮世绘"])
        self.assertNotIn("浮世绘", [i["name"] for i in data["items"]])
        self.assertIn("已导入", html_of(rendered))

    async def test_import_by_name_and_reports_failures(self):
        obj, _, _ = market_plugin()
        out = plain(await run(obj.preset_import(AdminEvent("/预设导入 Q版 不存在"))))
        self.assertIn("已导入：--Q版", out)
        self.assertIn("没有导入：不存在", out)

    async def test_builtin_name_cannot_be_imported(self):
        index = json.dumps({"presets": [{"name": "手办", "prompt": "evil {subject}"}]})
        obj, _, _ = market_plugin(index_text=index)
        out = plain(await run(obj.preset_import(AdminEvent("/预设导入 手办"))))
        self.assertIn("和内置预设重名", out)
        self.assertNotIn("evil", obj.CLOUD_PROMPT_PRESETS["手办"]["prompt"])

    async def test_imported_presets_survive_reload_and_can_be_deleted(self):
        obj, _, _ = market_plugin()
        await run(obj.preset_import(AdminEvent("/预设导入 剪纸 素描")))
        obj._refresh_imported_presets()
        self.assertEqual(obj._imported_preset_names(), ["剪纸", "素描"])
        out = plain(await run(obj.preset_delete(AdminEvent("/预设删除 papercut 手办"))))
        self.assertIn("已删除：剪纸", out)
        self.assertIn("内置预设不能删除", out)
        self.assertEqual(obj._imported_preset_names(), ["素描"])
        self.assertNotIn("--剪纸", obj.CLOUD_PROMPT_PRESET_FLAGS)
        self.assertIn("手办", obj.CLOUD_PROMPT_PRESETS)

    async def test_text_fallback_lists_imported_group(self):
        obj, _, _ = market_plugin()
        await run(obj.preset_import(AdminEvent("/预设导入 写真")))
        text = obj._cloud_preset_text()
        self.assertLess(text.index("通用画风"), text.index("【已导入】"))
        self.assertLess(text.index("【已导入】"), text.index("--写真"))

    def test_class_presets_untouched(self):
        self.assertNotIn("浮世绘", presets.CLOUD_PROMPT_PRESETS)


if __name__ == "__main__":
    unittest.main()
