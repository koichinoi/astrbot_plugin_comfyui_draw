"""Offline checks for the Reimu-style info cards and their text fallbacks."""
import sys
import unittest

import jinja2

from test_optimized_plugin import Event, plugin
from test_cloud_profiles import Config, run, with_message

templates = sys.modules["comfyui_draw_plugin.templates"]


class CardEvent(Event):
    @staticmethod
    def image_result(path):
        return ("image", path)


def carded(render_ok=True, **config):
    obj = plugin(config)
    obj.config = Config(obj.config)
    rendered = {}

    async def fake_render(template, data, **_kwargs):
        if not render_ok:
            raise RuntimeError("t2i offline")
        rendered["template"], rendered["data"] = template, data
        return "card.png"

    obj.html_render = fake_render
    return obj, rendered


def html_of(rendered):
    return jinja2.Template(rendered["template"]).render(**rendered["data"])


class InfoCardTests(unittest.IsolatedAsyncioTestCase):
    async def test_theme_list_renders_card(self):
        obj, rendered = carded()
        result = await run(obj.help_theme(with_message(CardEvent, "/绘图主题")))
        self.assertEqual(result, [("image", "card.png")])
        self.assertIs(rendered["template"], templates.REIMU_INFO_CARD_TMPL)
        html = html_of(rendered)
        for theme in templates.HELP_CARD_THEMES:
            self.assertIn(theme, html)
        self.assertIn("当前：默认", html)

    async def test_cloud_overview_renders_card_without_secrets(self):
        obj, rendered = carded(
            openai_image_base_url="https://secret-host.example/v1",
            openai_image_api_key="sk-not-real-secret",
        )
        result = await run(obj.cloud_switch(with_message(CardEvent, "/云绘图切换")))
        self.assertEqual(result, [("image", "card.png")])
        html = html_of(rendered)
        self.assertIn("云绘图方案", html)
        self.assertIn("/云绘图切换 &lt;方案名&gt; [模型名]", html)
        self.assertNotIn("secret-host", html)
        self.assertNotIn("sk-not-real-secret", html)

    async def test_draw_list_renders_default_tag(self):
        obj, rendered = carded()
        result = await run(obj.draw_list(with_message(CardEvent, "/绘图列表")))
        self.assertEqual(result, [("image", "card.png")])
        rows = rendered["data"]["sections"][0]["rows"]
        self.assertTrue(any(r["tag"] == "默认" for r in rows))
        self.assertIn("绘图工作流", html_of(rendered))

    async def test_render_failure_falls_back_to_text(self):
        obj, _ = carded(render_ok=False)
        theme = await run(obj.help_theme(with_message(CardEvent, "/绘图主题")))
        self.assertEqual(theme[0][0], "plain")
        self.assertIn("当前：默认", theme[0][1])
        listing = await run(obj.draw_list(with_message(CardEvent, "/绘图列表")))
        self.assertEqual(listing[0][0], "plain")
        self.assertIn("可用工作流", listing[0][1])

    async def test_card_without_illustration_still_renders(self):
        html = jinja2.Template(templates.REIMU_INFO_CARD_TMPL).render(
            title="T", sections=[{"title": "S", "lines": ["x"]}], illust="")
        self.assertNotIn("<img", html)
        html = jinja2.Template(templates.REIMU_INFO_CARD_TMPL).render(
            title="T", sections=[], illust="data:image/jpeg;base64,AAAA")
        self.assertIn('src="data:image/jpeg;base64,AAAA"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
