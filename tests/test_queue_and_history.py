"""Offline checks for task queues, per-user limits, daily caps, /绘图队列, /重画 and /我的绘图."""
import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from test_optimized_plugin import Event, plugin
from test_sub2api_antigravity import PNG

draw_queue = sys.modules["comfyui_draw_plugin.draw_queue"]


class UserEvent(Event):
    def __init__(self, uid="u1", text="", admin=False, name=None):
        self.uid, self.message_str, self.admin, self.name = uid, text, admin, name or f"用户{uid}"

    def get_sender_id(self):
        return self.uid

    def get_sender_name(self):
        return self.name

    def is_admin(self):
        return self.admin


def texts(output):
    return [item[1] for item in output if item[0] == "plain"]


class Harness:
    """云端与本地出图都换成可控的假实现，每次调用都等 gate 放行。"""

    def __init__(self, **config):
        self.tmp = tempfile.TemporaryDirectory()
        self.obj = plugin({"text_as_card": False, "auto_recall_progress": False, **config})
        self.obj._data_path = lambda name: str(Path(self.tmp.name) / name)
        self.obj._sweep_temp = lambda: None
        self.calls = []
        self.gate = None
        self.sources = []

        async def wait_gate():
            if self.gate is not None:
                await self.gate.wait()

        async def fake_cloud(prompt, size=None, n=1, quality=None, style=None, conn=None):
            self.calls.append(("cloud", prompt, size, n, conn))
            await wait_gate()
            return [(PNG, f"gptimage_{i}.png") for i in range(n)]

        async def fake_edit(prompt, sources, size=None, n=1, quality=None, conn=None):
            self.calls.append(("edit", prompt, size, n, conn))
            await wait_gate()
            return [(PNG, "gptedit_0.png")]

        async def fake_comfy(workflow):
            self.calls.append(("local", workflow))
            await wait_gate()
            return [(PNG, "result.png")]

        async def collect(_event, limit=1):
            return list(self.sources)

        async def no_input(_event, _workflow, _seed):
            return None

        self.obj._run_openai_image = fake_cloud
        self.obj._run_openai_image_edit = fake_edit
        self.obj._run_comfyui = fake_comfy
        self.obj._collect_input_images = collect
        self.obj._apply_input_images = no_input

    async def run(self, gen):
        return [item async for item in gen]

    def cloud(self, event, prompt="a cat", **opts):
        return self.run(self.obj._render_openai(event, prompt, opts, record=True))

    def local(self, event, text="a dog"):
        prompt, opts = self.obj._parse_args(text)
        return self.run(self.obj._render(event, prompt, opts))

    def command(self, name, event):
        return self.run(getattr(self.obj, name)(event))

    def close(self):
        self.tmp.cleanup()


class QueueUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_fifo_limit_and_cancel_waiting(self):
        queue = draw_queue.DrawQueue("cloud", 1)
        first, second, third = (queue.join(u) for u in ("a", "b", "c"))
        self.assertTrue(first.running)
        self.assertEqual((queue.ahead(second), queue.ahead(third)), (0, 1))
        self.assertTrue(queue.cancel(second))
        with self.assertRaises(draw_queue.DrawCancelled):
            await queue.wait(second)
        queue.leave(first)
        await queue.wait(third)
        self.assertTrue(third.running)
        queue.leave(third)
        self.assertEqual(queue.tickets(), [])


class QueueRenderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = Harness(max_concurrent_cloud_tasks=1, max_concurrent_tasks=1)
        self.h.gate = asyncio.Event()

    async def asyncTearDown(self):
        self.h.close()

    async def test_second_user_sees_queue_position_then_finishes(self):
        first = asyncio.create_task(self.h.cloud(UserEvent("a")))
        await asyncio.sleep(0)
        second = asyncio.create_task(self.h.cloud(UserEvent("b")))
        await asyncio.sleep(0.01)
        self.assertEqual(len(self.h.calls), 1)
        # 云端占满时本地照常出图，两个队列互不占用。
        local = asyncio.create_task(self.h.local(UserEvent("c")))
        await asyncio.sleep(0.01)
        self.assertEqual([c[0] for c in self.h.calls], ["cloud", "local"])
        self.h.gate.set()
        out_a, out_b, _ = await asyncio.gather(first, second, local)
        self.assertEqual(out_a[-1][0], "chain")
        self.assertEqual(out_b[-1][0], "chain")
        self.assertTrue(any("排队中：第 1 位" in t for t in texts(out_b)))
        self.assertFalse(any("排队中" in t for t in texts(out_a)))

    async def test_per_user_limit_and_admin_bypass(self):
        first = asyncio.create_task(self.h.cloud(UserEvent("a")))
        await asyncio.sleep(0.01)
        blocked = await self.h.cloud(UserEvent("a"))
        self.assertIn("已有 1 个绘图任务", texts(blocked)[-1])
        admin = asyncio.create_task(self.h.cloud(UserEvent("a", admin=True)))
        await asyncio.sleep(0.01)
        self.h.gate.set()
        await asyncio.gather(first, admin)
        self.assertEqual(len(self.h.calls), 2)

    async def test_cancel_waiting_and_running_from_queue_command(self):
        running = asyncio.create_task(self.h.cloud(UserEvent("a")))
        await asyncio.sleep(0.01)
        waiting = asyncio.create_task(self.h.cloud(UserEvent("b")))
        await asyncio.sleep(0.01)
        ids = {t.uid: t.id for t in self.h.obj._all_tickets()}

        listing = await self.h.command("draw_queue", UserEvent("x", "/绘图队列"))
        self.assertIn(f"#{ids['a']} 用户a（生成中）", listing[-1][1])
        self.assertIn(f"#{ids['b']} 用户b（排队）", listing[-1][1])

        denied = await self.h.command("draw_queue", UserEvent("x", f"/绘图队列 取消 {ids['b']}"))
        self.assertIn("只能取消自己的任务", denied[-1][1])
        ok = await self.h.command("draw_queue", UserEvent("b", f"/绘图队列 取消 {ids['b']}"))
        self.assertIn("已取消", ok[-1][1])
        self.assertIn("已被取消", texts(await waiting)[-1])

        admin = await self.h.command("draw_queue", UserEvent("x", f"/绘图队列 取消 #{ids['a']}", admin=True))
        self.assertIn("可能仍会计费", admin[-1][1])
        self.assertIn("已被取消", texts(await running)[-1])
        self.assertEqual(self.h.obj._all_tickets(), [])
        self.assertEqual(len(self.h.calls), 1)


class LimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_cooldown(self):
        h = Harness(user_cooldown_seconds=60, max_tasks_per_user=0)
        try:
            self.assertEqual((await h.cloud(UserEvent("a")))[-1][0], "chain")
            self.assertIn("秒后再试", texts(await h.cloud(UserEvent("a")))[-1])
            self.assertEqual((await h.cloud(UserEvent("b")))[-1][0], "chain")
        finally:
            h.close()

    async def test_daily_cloud_limit_counts_images_and_persists(self):
        h = Harness(daily_limit_cloud=3)
        try:
            await h.cloud(UserEvent("a"), batch=2)
            too_many = await h.cloud(UserEvent("a"), batch=2)
            self.assertIn("只剩 1 张", texts(too_many)[-1])
            await h.cloud(UserEvent("a"))
            self.assertIn("已用完（3/3 张）", texts(await h.cloud(UserEvent("a")))[-1])
            self.assertEqual(len(h.calls), 2)
            # 本地不受云端上限影响，重新加载后计数仍在。
            self.assertEqual((await h.local(UserEvent("a")))[-1][0], "chain")
            h.obj._usage_data = None
            self.assertEqual(h.obj._usage_today("a", "cloud"), 3)
            mine = await h.command("my_draws", UserEvent("a", "/我的绘图"))
            self.assertIn("云端：已用 3/3 张，还剩 0 张", mine[-1][1])
        finally:
            h.close()

    async def test_timeout_message_names_config(self):
        h = Harness(openai_image_timeout=350)

        async def slow(*_args, **_kwargs):
            raise asyncio.TimeoutError()

        h.obj._run_openai_image = slow
        try:
            self.assertIn("超过 350 秒，配置项 openai_image_timeout", texts(await h.cloud(UserEvent("a")))[-1])
        finally:
            h.close()


class SnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_switch_mid_generation_keeps_original_connection(self):
        h = Harness(
            openai_image_base_url="https://img.example/v1",
            openai_image_api_key="key-not-real",
            cloud_profiles=[{"name": "G", "provider": "openai-compatible", "model": "other-model"}],
        )
        h.gate = asyncio.Event()
        try:
            task = asyncio.create_task(h.cloud(UserEvent("a")))
            await asyncio.sleep(0.01)
            h.obj.config["active_cloud_profile"] = "G"
            h.gate.set()
            await task
            self.assertEqual(h.calls[0][4]["model"], "gpt-image-2")
            self.assertEqual(h.obj._user_history("a")[0]["label"], "云端·gpt-image-2")
        finally:
            h.close()


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = Harness(history_size=3)

    async def asyncTearDown(self):
        self.h.close()

    async def test_redraw_latest_with_extra_prompt_and_options(self):
        await self.h.command("draw_gpt", UserEvent("a", "/云绘图 银发少女 --手办"))
        await self.h.command("redraw", UserEvent("a", "/重画 加上猫耳 --竖图"))
        first, second = self.h.calls
        self.assertIn("银发少女", second[1])
        self.assertIn("加上猫耳", second[1])
        self.assertIn("figurine", second[1].lower())
        self.assertEqual(second[2], "1024x1536")
        records = self.h.obj._user_history("a")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["prompt"], "银发少女，加上猫耳")

    async def test_history_is_capped_per_user_and_numbered(self):
        for i in range(4):
            await self.h.command("draw_gpt", UserEvent("a", f"/云绘图 第{i}张"))
        await self.h.command("draw_gpt", UserEvent("b", "/云绘图 别人的"))
        records = self.h.obj._user_history("a")
        self.assertEqual([r["prompt"] for r in records], ["第3张", "第2张", "第1张"])
        await self.h.command("redraw", UserEvent("a", "/重画 3"))
        self.assertTrue(self.h.calls[-1][1].startswith("第1张"))
        out = await self.h.command("redraw", UserEvent("a", "/重画 9"))
        self.assertIn("只有 3 条", out[-1][1])
        # 重新加载后记录仍在。
        self.h.obj._history_data = None
        mine = await self.h.command("my_draws", UserEvent("a", "/我的绘图"))
        self.assertIn("1. 第1张", mine[-1][1])
        cleared = await self.h.command("my_draws", UserEvent("a", "/我的绘图 清空"))
        self.assertIn("已清空", cleared[-1][1])
        self.assertEqual(self.h.obj._user_history("a"), [])
        self.assertEqual(len(self.h.obj._user_history("b")), 1)

    async def test_redraw_edit_requires_source_image(self):
        self.h.sources = [PNG]
        await self.h.command("cloud_figure", UserEvent("a", "/变手办"))
        self.h.sources = []
        out = await self.h.command("redraw", UserEvent("a", "/重画"))
        self.assertIn("原图不会保存", out[-1][1])
        self.h.sources = [PNG]
        await self.h.command("redraw", UserEvent("a", "/重画"))
        self.assertEqual([c[0] for c in self.h.calls], ["edit", "edit"])

    async def test_local_redraw_uses_new_seed_unless_given(self):
        await self.h.command("draw", UserEvent("a", "/绘图 a cat --seed 42"))
        self.assertEqual(self.h.obj._user_history("a")[0]["opts"]["seed"], "42")
        await self.h.command("redraw", UserEvent("a", "/重画"))
        await self.h.command("redraw", UserEvent("a", "/重画 --seed 7"))
        seeds = [c[1]["3"]["inputs"]["seed"] for c in self.h.calls]
        self.assertEqual(seeds[0], 42)
        self.assertEqual(seeds[2], 7)

    async def test_no_history_and_disabled(self):
        out = await self.h.command("redraw", UserEvent("z", "/重画"))
        self.assertIn("还没有你的出图记录", out[-1][1])
        self.h.obj.config["history_size"] = 0
        out = await self.h.command("redraw", UserEvent("z", "/重画"))
        self.assertIn("history_size", out[-1][1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
