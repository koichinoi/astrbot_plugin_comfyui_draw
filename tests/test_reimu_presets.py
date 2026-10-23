"""Offline checks for the Reimu-themed cloud presets and the /云绘图预设 card."""
import sys
import unittest

from test_info_cards import CardEvent, carded, html_of
from test_cloud_profiles import run, with_message

templates = sys.modules["comfyui_draw_plugin.templates"]
presets = sys.modules["comfyui_draw_plugin.presets"]

REIMU = ("巫女", "参拜", "御守", "符卡")


class ReimuPresetTests(unittest.TestCase):
    def test_reimu_presets_are_complete(self):
        self.assertEqual(tuple(presets.REIMU_PRESET_THUMBS), REIMU)
        for name in REIMU:
            item = presets.CLOUD_PROMPT_PRESETS[name]
            self.assertIn("{subject}", item["prompt"])
            self.assertIn(name, presets.CLOUD_PRESET_ICONS)
            self.assertEqual(presets.CLOUD_PROMPT_PRESET_FLAGS[f"--{name}"], name)

    def test_aliases_and_flags_resolve(self):
        obj, _ = carded()
        for flag, name in [("--灵梦", "巫女"), ("--神社", "参拜"), ("--绘马", "御守"), ("--弹幕", "符卡")]:
            _prompt, opts = obj._parse_args(f"银发少女 {flag}", cloud=True)
            self.assertEqual(opts["preset"], name)
        prompt, name, size = obj._apply_cloud_prompt_preset("银发少女", "灵梦")
        self.assertEqual((name, size), ("巫女", "1024x1536"))
        self.assertIn("银发少女", prompt)

    def test_existing_presets_untouched(self):
        self.assertIn("Subject: {subject}", presets.CLOUD_PROMPT_PRESETS["手办"]["prompt"])
        self.assertNotIn("Hakurei", presets.CLOUD_PROMPT_PRESETS["手办"]["prompt"])


class PresetCardTests(unittest.IsolatedAsyncioTestCase):
    async def test_card_groups_reimu_presets_first(self):
        obj, rendered = carded()
        result = await run(obj.cloud_draw_presets(with_message(CardEvent, "/云绘图预设")))
        self.assertEqual(result, [("image", "card.png")])
        self.assertIs(rendered["template"], templates.CLOUD_PRESET_CARD_TMPL)
        data = rendered["data"]
        self.assertEqual([i["name"] for i in data["reimu_items"]], list(REIMU))
        self.assertNotIn("巫女", [i["name"] for i in data["items"]])
        html = html_of(rendered)
        self.assertIn("博丽神社限定", html)
        self.assertIn("--手办", html)
        self.assertNotIn("Rabbit House", html)

    async def test_card_renders_without_thumbnails(self):
        obj, rendered = carded()
        obj._asset_data_uri = lambda _name: ""
        await run(obj.cloud_draw_presets(with_message(CardEvent, "/云绘图预设")))
        html = html_of(rendered)
        self.assertIn('class="thumb icon"', html)
        self.assertNotIn('class="illust"', html)

    async def test_text_fallback_lists_groups(self):
        obj, _ = carded(render_ok=False)
        result = await run(obj.cloud_draw_presets(with_message(CardEvent, "/云绘图预设")))
        text = result[0][1]
        self.assertLess(text.index("博丽神社限定"), text.index("--巫女"))
        self.assertLess(text.index("--符卡"), text.index("通用画风"))
        self.assertLess(text.index("通用画风"), text.index("--手办"))


if __name__ == "__main__":
    unittest.main()
