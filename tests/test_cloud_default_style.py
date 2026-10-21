"""Offline checks for the default art style added to plain cloud text-to-image prompts."""
import unittest

from test_optimized_plugin import Event, plugin
from test_sub2api_antigravity import PNG

DEFAULT_STYLE = "日系二次元动漫插画"


def cloud(**config):
    obj = plugin({"show_progress": False, **config})
    calls = []

    async def fake_generate(prompt, size=None, n=1, quality=None, style=None):
        calls.append(("generate", prompt, style))
        return [(PNG, "gemini_0.png")]

    async def fake_edit(prompt, sources, size=None, n=1, quality=None):
        calls.append(("edit", prompt, None))
        return [(PNG, "gemini_0.png")]

    async def no_images(_event, limit=1):
        return obj.source_images

    obj.source_images = []
    obj._run_openai_image = fake_generate
    obj._run_openai_image_edit = fake_edit
    obj._collect_input_images = no_images
    obj._sweep_temp = lambda: None
    return obj, calls


async def render(obj, prompt, **opts):
    return [item async for item in obj._render_openai(Event(), prompt, opts)]


class DefaultStyleTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_prompt_gets_default_anime_style(self):
        obj, calls = cloud()
        output = await render(obj, "博丽灵梦")
        self.assertEqual(output[-1][0], "chain")
        kind, prompt, _ = calls[0]
        self.assertEqual(kind, "generate")
        self.assertTrue(prompt.startswith("博丽灵梦\n"))
        self.assertIn(DEFAULT_STYLE, prompt)
        self.assertIn("以描述为准", prompt)

    async def test_presets_style_flag_and_edits_are_untouched(self):
        obj, calls = cloud()
        await render(obj, "银发少女", preset="手办")
        await render(obj, "银发少女", style="watercolor")
        obj.source_images = [PNG]
        await render(obj, "让她笑一下")
        for kind, prompt, _ in calls:
            self.assertNotIn("画风要求", prompt, kind)
        self.assertEqual([kind for kind, _, _ in calls], ["generate", "generate", "edit"])

    async def test_config_can_change_or_disable_style(self):
        obj, calls = cloud(cloud_default_art_style="厚涂奇幻插画")
        await render(obj, "城堡")
        self.assertIn("画风要求：厚涂奇幻插画", calls[0][1])

        obj, calls = cloud(cloud_default_art_style="")
        await render(obj, "城堡")
        self.assertEqual(calls[0][1], "城堡")

    async def test_daily_me_cloud_prompt_is_unchanged(self):
        obj, calls = cloud(daily_me_backend="cloud", daily_me_result_card=False)
        output = [item async for item in obj.daily_me(Event())]
        self.assertEqual(output[-1][0], "chain")
        self.assertNotIn("画风要求", calls[0][1])
        self.assertIn("anime-style", calls[0][1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
