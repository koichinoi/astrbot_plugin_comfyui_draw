"""Offline checks for cloud drawing profiles and the online switch commands."""
import unittest
from unittest.mock import patch

from test_optimized_plugin import Event, module, plugin
from test_cloud_and_inputs import openai_payload
from test_sub2api_antigravity import PNG, Response, Session


class Config(dict):
    """带 save_config 的配置替身，记录写回次数。"""

    saves = 0

    def save_config(self):
        self.saves += 1


class AdminEvent(Event):
    role = "admin"

    @staticmethod
    def is_admin():
        return True


def with_message(event_cls, text):
    event = event_cls()
    event.message_str = text
    return event


GPT_KEY = "gpt-key-not-real"
GEMINI_KEY = "gemini-key-not-real"


def profiled(**overrides):
    obj = plugin({
        "openai_image_provider": "auto",
        "openai_image_base_url": "https://default.example",
        "openai_image_api_key": "default-key-not-real",
        "openai_image_model": "gpt-image-2",
        "gemini_image_model": "gemini-3.1-flash-image",
        "show_progress": False,
        "cloud_profiles": [
            {"name": "GPT", "provider": "openai-compatible", "base_url": "https://gpt.example",
             "api_key": GPT_KEY, "model": ""},
            {"name": "Gemini", "provider": "sub2api-antigravity", "base_url": "https://sub2.example",
             "api_key": GEMINI_KEY, "model": "gemini-3-pro-image"},
            {"name": "SameSite", "provider": "openai-compatible", "base_url": "", "api_key": "",
             "model": "other-image-model"},
            {"name": "默认", "provider": "openai-compatible"},
            {"name": "", "provider": "openai-compatible"},
        ],
        **overrides,
    })
    obj.config = Config(obj.config)
    return obj


async def run(gen):
    return [item async for item in gen]


class ProfileResolutionTests(unittest.TestCase):
    def test_default_profile_uses_top_level_config(self):
        conn = profiled()._cloud_connection()
        self.assertEqual(conn["name"], "默认")
        self.assertEqual(conn["provider"], "auto")
        self.assertEqual(conn["base_url"], "https://default.example")
        self.assertEqual(conn["model"], "gpt-image-2")

    def test_named_profiles_override_and_inherit(self):
        obj = profiled(active_cloud_profile="GPT")
        conn = obj._cloud_connection()
        self.assertEqual((conn["provider"], conn["base_url"], conn["api_key"]),
                         ("openai-compatible", "https://gpt.example", GPT_KEY))
        self.assertEqual(conn["model"], "gpt-image-2")  # 留空沿用顶层 OpenAI 模型
        self.assertEqual(obj._openai_image_provider(), "openai-compatible")

        gemini = obj._cloud_connection("Gemini")
        self.assertEqual((gemini["provider"], gemini["model"]),
                         ("sub2api-antigravity", "gemini-3-pro-image"))

        same = obj._cloud_connection("SameSite")
        self.assertEqual(same["base_url"], "https://default.example")
        self.assertEqual(same["api_key"], "default-key-not-real")
        self.assertEqual(same["model"], "other-image-model")

    def test_provider_specific_top_level_keys(self):
        obj = profiled(sub2api_antigravity_api_key="sub2-key-not-real")
        self.assertEqual(obj._cloud_connection()["api_key"], "default-key-not-real")  # auto 用通用 Key
        obj.config["openai_image_provider"] = "chatgpt2api"  # 已移除的类型回退到 auto，用通用 Key
        conn = obj._cloud_connection()
        self.assertEqual(conn["provider"], "auto")
        self.assertEqual(conn["api_key_field"], "openai_image_api_key")
        obj.config["openai_image_provider"] = "sub2api-antigravity"
        self.assertEqual(obj._cloud_connection()["api_key"], "sub2-key-not-real")
        obj.config["openai_image_provider"] = "openai-compatible"  # 专属 Key 留空沿用通用 Key
        conn = obj._cloud_connection()
        self.assertEqual(conn["api_key"], "default-key-not-real")
        self.assertEqual(conn["api_key_field"], "openai_compatible_api_key")

        # 同站点方案（地址留空）按自己的接口类型取专属 Key
        obj.config["openai_compatible_api_key"] = "compat-key-not-real"
        self.assertEqual(obj._cloud_connection("SameSite")["api_key"], "compat-key-not-real")

    def test_profile_with_own_url_never_borrows_top_level_key(self):
        obj = profiled(sub2api_antigravity_api_key="sub2-key-not-real")
        obj.config["cloud_profiles"][0]["api_key"] = ""
        obj.config["cloud_profiles"][1]["api_key"] = ""
        self.assertEqual(obj._cloud_connection("GPT")["api_key"], "")
        self.assertEqual(obj._cloud_connection("Gemini")["api_key"], "")

    def test_empty_gemini_model_uses_gemini_setting(self):
        obj = profiled(active_cloud_profile="Gemini")
        obj.config["cloud_profiles"][1]["model"] = ""
        self.assertEqual(obj._cloud_image_model(), "gemini-3.1-flash-image")

    def test_missing_or_reserved_profiles(self):
        obj = profiled(active_cloud_profile="Deleted")
        self.assertEqual(obj._cloud_connection()["name"], "默认")
        self.assertEqual(obj._cloud_profile_names(), ["默认", "GPT", "Gemini", "SameSite"])
        self.assertEqual(obj._match_cloud_profile("gpt"), "GPT")
        self.assertEqual(obj._match_cloud_profile("default"), "默认")
        self.assertIsNone(obj._match_cloud_profile("nope"))

    def test_model_name_validation(self):
        valid = module.ComfyUIDrawPlugin._valid_model_name
        self.assertTrue(valid("models/gemini-3-pro-image"))
        self.assertTrue(valid("gpt-image-2@2026"))
        for bad in ("", "a b", "x" * 201, "<script>", "模型"):
            self.assertFalse(valid(bad), bad)


class ProfileRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_profile_controls_request(self):
        session = Session([Response(200, payload=openai_payload())])
        with patch.object(module.aiohttp, "ClientSession", return_value=session, create=True):
            await profiled(active_cloud_profile="GPT")._run_openai_image("cat")
        url, kwargs = session.calls[0]
        self.assertEqual(url, "https://gpt.example/images/generations")
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {GPT_KEY}")
        self.assertEqual(kwargs["json"]["model"], "gpt-image-2")
        self.assertNotIn("history_disabled", kwargs["json"])

    async def test_switch_to_gemini_profile_uses_antigravity(self):
        session = Session([Response(200, payload={"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png",
                            "data": __import__("base64").b64encode(PNG).decode()}}
        ]}}]})])
        with patch.object(module.aiohttp, "ClientSession", return_value=session, create=True):
            await profiled(active_cloud_profile="Gemini")._run_openai_image("cat")
        url, kwargs = session.calls[0]
        self.assertEqual(
            url, "https://sub2.example/antigravity/v1beta/models/gemini-3-pro-image:generateContent"
        )
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {GEMINI_KEY}")

    async def test_missing_key_hint_names_profile(self):
        obj = profiled(active_cloud_profile="SameSite", openai_image_api_key="")
        with self.assertRaisesRegex(module.ComfyUIError, "SameSite"):
            await obj._run_openai_image("cat")


    async def test_missing_key_names_provider_field(self):
        obj = profiled(openai_image_provider="openai-compatible", openai_image_api_key="")
        with self.assertRaisesRegex(module.ComfyUIError, "openai_compatible_api_key"):
            await obj._run_openai_image("cat")

    async def test_top_level_provider_key_is_sent(self):
        session = Session([Response(200, payload=openai_payload())])
        obj = profiled(openai_image_provider="openai-compatible", openai_compatible_api_key="compat-key-not-real")
        with patch.object(module.aiohttp, "ClientSession", return_value=session, create=True):
            await obj._run_openai_image("cat")
        self.assertEqual(session.calls[0][1]["headers"]["Authorization"], "Bearer compat-key-not-real")


class SwitchCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_overview_is_public_and_hides_secrets(self):
        obj = profiled(active_cloud_profile="GPT")
        output = await run(obj.cloud_switch(with_message(Event, "/云绘图切换")))
        text = output[0][1]
        self.assertIn("当前：GPT", text)
        self.assertIn("Antigravity/Gemini · gemini-3-pro-image", text)
        for secret in (GPT_KEY, GEMINI_KEY, "default-key-not-real", "gpt.example", "sub2.example"):
            self.assertNotIn(secret, text)

    async def test_non_admin_cannot_switch(self):
        obj = profiled()
        output = await run(obj.cloud_switch(with_message(Event, "/云绘图切换 Gemini")))
        self.assertIn("只有管理员", output[0][1])
        self.assertNotIn("active_cloud_profile", obj.config)
        self.assertEqual(obj.config.saves, 0)

    async def test_admin_switch_with_model_and_back_to_default(self):
        obj = profiled()
        output = await run(obj.cloud_switch(with_message(AdminEvent, "/云绘图切换 gemini gemini-3.1-flash-image")))
        self.assertIn("已切换到「Gemini」", output[0][1])
        self.assertEqual(obj.config["active_cloud_profile"], "Gemini")
        self.assertEqual(obj._cloud_image_model(), "gemini-3.1-flash-image")
        self.assertEqual(obj.config.saves, 1)

        await run(obj.cloud_switch(with_message(AdminEvent, "/云切换 默认")))
        self.assertEqual(obj.config["active_cloud_profile"], "")
        self.assertEqual(obj._cloud_connection()["provider"], "auto")

    async def test_switch_rejects_unknown_profile_and_bad_model(self):
        obj = profiled()
        output = await run(obj.cloud_switch(with_message(AdminEvent, "/云绘图切换 Nope")))
        self.assertIn("找不到云绘图方案", output[0][1])
        output = await run(obj.cloud_switch(with_message(AdminEvent, "/云绘图切换 GPT <bad>")))
        self.assertIn("模型名只能包含", output[0][1])
        self.assertNotIn("active_cloud_profile", obj.config)

    async def test_switch_warns_when_profile_lacks_credentials(self):
        obj = profiled(openai_image_api_key="")
        output = await run(obj.cloud_switch(with_message(AdminEvent, "/云绘图切换 SameSite")))
        self.assertIn("缺少地址或 Key", output[0][1])

    async def test_model_command(self):
        obj = profiled()
        view = await run(obj.cloud_model(with_message(Event, "/云绘图模型")))
        self.assertIn("gpt-image-2", view[0][1])
        denied = await run(obj.cloud_model(with_message(Event, "/云绘图模型 x")))
        self.assertIn("只有管理员", denied[0][1])

        await run(obj.cloud_model(with_message(AdminEvent, "/云绘图模型 gpt-image-1")))
        self.assertEqual(obj.config["openai_image_model"], "gpt-image-1")

        obj.config["active_cloud_profile"] = "Gemini"
        await run(obj.cloud_model(with_message(AdminEvent, "/云模型 gemini-3.1-flash-image")))
        self.assertEqual(obj.config["cloud_profiles"][1]["model"], "gemini-3.1-flash-image")
        self.assertEqual(obj.config["gemini_image_model"], "gemini-3.1-flash-image")
        self.assertEqual(obj.config.saves, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
