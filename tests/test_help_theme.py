"""Offline checks for help card themes and the /绘图主题 command."""
import sys
import unittest

from test_optimized_plugin import Event, plugin
from test_cloud_profiles import AdminEvent, Config, run, with_message

templates = sys.modules["comfyui_draw_plugin.templates"]


def themed(**config):
    obj = plugin(config)
    obj.config = Config(obj.config)
    rendered = {}

    async def fake_render(template, data, **_kwargs):
        rendered["template"], rendered["data"] = template, data
        return "card.png"

    obj.html_render = fake_render
    return obj, rendered


class HelpThemeTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_shrine_templates(self):
        obj, rendered = themed()
        self.assertEqual(await obj._render_draw_help(), "card.png")
        self.assertIs(rendered["template"], templates.DRAW_HELP_TMPL)

        obj.config["help_card_theme"] = "神社"
        await obj._render_draw_help()
        self.assertIs(rendered["template"], templates.SHRINE_HELP_TMPL)

        obj.config["help_card_theme"] = "不存在"
        await obj._render_draw_help()
        self.assertIs(rendered["template"], templates.DRAW_HELP_TMPL)

    async def test_shrine_template_renders_all_help_data(self):
        import jinja2

        obj, rendered = themed(help_card_theme="神社")
        await obj._render_draw_help()
        html = jinja2.Template(rendered["template"]).render(**rendered["data"])
        for group in rendered["data"]["groups"]:
            for item in group["items"]:
                self.assertIn(item["cmd"], html)
        for example in rendered["data"]["examples"]:
            self.assertIn(example, html)
        self.assertIn("绘马堂", html)
        self.assertIn("/绘图主题 [主题名]", html)

    async def test_reimu_template_renders_all_help_data(self):
        import jinja2

        obj, rendered = themed(help_card_theme="博丽灵梦")
        await obj._render_draw_help()
        self.assertIs(rendered["template"], templates.REIMU_HELP_TMPL)
        html = jinja2.Template(rendered["template"]).render(**rendered["data"])
        for group in rendered["data"]["groups"]:
            for item in group["items"]:
                self.assertIn(item["cmd"], html)
        for example in rendered["data"]["examples"]:
            self.assertIn(example, html)
        self.assertIn("博丽神社", html)
        self.assertIn("/绘图主题 [主题名]", html)

    async def test_command_view_and_permissions(self):
        obj, _ = themed()
        view = await run(obj.help_theme(with_message(Event, "/绘图主题")))
        self.assertIn("当前：默认", view[0][1])
        self.assertIn("神社", view[0][1])

        denied = await run(obj.help_theme(with_message(Event, "/绘图主题 神社")))
        self.assertIn("只有管理员", denied[0][1])
        self.assertNotIn("help_card_theme", obj.config)

        bad = await run(obj.help_theme(with_message(AdminEvent, "/绘图主题 樱花")))
        self.assertIn("没有「樱花」主题", bad[0][1])

        ok = await run(obj.help_theme(with_message(AdminEvent, "/帮助主题 神社")))
        self.assertIn("已切换为「神社」", ok[0][1])
        self.assertEqual(obj.config["help_card_theme"], "神社")
        self.assertEqual(obj.config.saves, 1)

        same = await run(obj.help_theme(with_message(AdminEvent, "/绘图主题 神社")))
        self.assertIn("已经是", same[0][1])
        self.assertEqual(obj.config.saves, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
