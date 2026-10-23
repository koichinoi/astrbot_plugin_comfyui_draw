"""Offline checks for the separate local / cloud drawing switches and /绘图开关."""
import unittest

from test_cloud_profiles import Config
from test_queue_and_history import Harness, UserEvent, texts


class SwitchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.h = Harness()
        self.h.obj.config = Config(self.h.obj.config)

    def tearDown(self):
        self.h.close()

    async def test_local_off_blocks_local_paths_only(self):
        self.h.obj.config["enable_local_draw"] = False
        out = await self.h.command("draw", UserEvent("a", "/绘图 a cat", admin=True))
        self.assertIn("本地绘图已关闭", out[-1][1])
        self.assertIn("可以先用 /云绘图", out[-1][1])
        out = await self.h.run(self.h.obj.draw_image_tool(UserEvent("a"), "a cat"))
        self.assertIn("本地绘图已关闭", out[-1][1])
        self.assertEqual(self.h.calls, [])
        out = await self.h.command("draw_gpt", UserEvent("a", "/云绘图 a cat"))
        self.assertEqual(out[-1][0], "chain")
        self.assertEqual([c[0] for c in self.h.calls], ["cloud"])

    async def test_cloud_off_blocks_cloud_paths_and_redraw(self):
        await self.h.command("draw_gpt", UserEvent("a", "/云绘图 a cat"))
        self.h.obj.config["enable_cloud_draw"] = False
        for name, text in (("draw_gpt", "/云绘图 a dog"), ("cloud_figure", "/变手办"), ("redraw", "/重画")):
            out = await self.h.command(name, UserEvent("a", text))
            self.assertIn("云绘图已关闭", out[-1][1], name)
        self.h.obj.config["enable_local_draw"] = False
        out = await self.h.command("draw_gpt", UserEvent("a", "/云绘图 a dog"))
        self.assertNotIn("可以先用", out[-1][1])
        self.assertEqual(len(self.h.calls), 1)

    async def test_daily_me_follows_its_backend_switch(self):
        self.h.obj.config.update({"enable_cloud_draw": False, "daily_me_backend": "cloud"})
        out = await self.h.command("daily_me", UserEvent("a", "/二次元的我"))
        self.assertIn("云绘图已关闭", texts(out)[-1])
        # 没出图不计次，开关打开后还能抽。
        self.h.obj.config["enable_cloud_draw"] = True
        out = await self.h.command("daily_me", UserEvent("a", "/二次元的我"))
        self.assertEqual(out[-1][0], "chain")

    async def test_switch_command_status_permission_and_save(self):
        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关"))
        self.assertIn("本地绘图：开启", out[-1][1])
        self.assertIn("云绘图：开启", out[-1][1])
        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关 云端 关"))
        self.assertIn("只有管理员", out[-1][1])
        self.assertNotIn("enable_cloud_draw", self.h.obj.config)

        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关 云端 关", admin=True))
        self.assertIn("云绘图已关闭", out[-1][1])
        self.assertIs(self.h.obj.config["enable_cloud_draw"], False)
        self.assertEqual(self.h.obj.config.saves, 1)
        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关"))
        self.assertIn("云绘图：关闭", out[-1][1])

        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关 本地 off", admin=True))
        self.assertIs(self.h.obj.config["enable_local_draw"], False)
        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关 云 开", admin=True))
        self.assertIs(self.h.obj.config["enable_cloud_draw"], True)
        out = await self.h.command("draw_switch", UserEvent("a", "/绘图开关 云端 也许", admin=True))
        self.assertIn("用法", out[-1][1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
