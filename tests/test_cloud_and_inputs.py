"""Offline regressions for cloud URL fallback, result decoding and input images."""
import base64
import json
import os
import tempfile
import types
import unittest
from unittest.mock import patch

from test_optimized_plugin import Event, module, plugin, PluginError
from test_sub2api_antigravity import PNG, Response, Session


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def openai_payload(image=PNG):
    return {"data": [{"b64_json": base64.b64encode(image).decode("ascii")}]}


class FormData:
    """aiohttp.FormData 替身：记录字段，便于确认每次回退都会重建表单。"""

    created = 0

    def __init__(self):
        FormData.created += 1
        self.fields = []

    def add_field(self, name, value, **kwargs):
        self.fields.append((name, value, kwargs))


class OpenAIFallbackTests(unittest.IsolatedAsyncioTestCase):
    def configured(self, **overrides):
        return plugin({
            "openai_image_provider": "auto",
            "openai_image_base_url": "https://img.example",
            "openai_image_api_key": "test-key-not-real",
            **overrides,
        })

    def patch_session(self, session):
        stub = patch.object(module.aiohttp, "ClientSession", return_value=session, create=True)
        stub.start()
        self.addCleanup(stub.stop)

    async def test_html_404_on_root_still_falls_back_to_v1(self):
        session = Session([
            Response(404, raw=b"<html>Not Found</html>"),
            Response(200, payload=openai_payload()),
        ])
        self.patch_session(session)
        results = await self.configured()._run_openai_image("cat")
        self.assertEqual([url for url, _ in session.calls], [
            "https://img.example/images/generations",
            "https://img.example/v1/images/generations",
        ])
        self.assertEqual(results, [(PNG, "gptimage_0.png")])

    async def test_non_json_error_reports_http_status(self):
        self.patch_session(Session([Response(502, raw=b"<html>Bad Gateway</html>")]))
        with self.assertRaisesRegex(PluginError, "HTTP 502"):
            await self.configured(openai_image_base_url="https://img.example/v1")._run_openai_image("cat")

    async def test_json_error_message_is_kept(self):
        self.patch_session(Session([Response(400, payload={"error": {"message": "prompt rejected"}})]))
        with self.assertRaisesRegex(PluginError, "prompt rejected"):
            await self.configured(openai_image_base_url="https://img.example/v1")._run_openai_image("cat")

    async def test_result_extension_follows_image_bytes(self):
        self.patch_session(Session([Response(200, payload=openai_payload(JPEG))]))
        results = await self.configured(
            openai_image_base_url="https://img.example/v1"
        )._run_openai_image("cat")
        self.assertEqual(results[0][1], "gptimage_0.jpg")

    async def test_edit_fallback_rebuilds_form(self):
        session = Session([
            Response(405, raw=b""),
            Response(200, payload=openai_payload()),
        ])
        self.patch_session(session)
        FormData.created = 0
        with patch.object(module.aiohttp, "FormData", FormData):
            results = await self.configured()._run_openai_image_edit("变手办", [PNG])
        self.assertEqual(FormData.created, 2)
        self.assertIsNot(session.calls[0][1]["data"], session.calls[1][1]["data"])
        self.assertTrue(session.calls[1][0].endswith("/v1/images/edits"))
        self.assertEqual(results, [(PNG, "gptedit_0.png")])

    async def test_missing_data_is_reported(self):
        self.patch_session(Session([Response(200, payload={"data": []})]))
        with self.assertRaisesRegex(PluginError, "云端绘图没有返回图片数据"):
            await self.configured(openai_image_base_url="https://img.example/v1")._run_openai_image("cat")


class InputImageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(handle, "wb") as f:
            f.write(PNG)
        self.addCleanup(os.remove, self.path)

    def event_with(self, component):
        event = Event()
        event.message_obj = types.SimpleNamespace(message=[component])
        return event

    def test_local_path_variants(self):
        uri = "file:///" + os.path.abspath(self.path)
        for comp in (
            types.SimpleNamespace(file=self.path),
            types.SimpleNamespace(file=uri),
            types.SimpleNamespace(file="file://" + os.path.abspath(self.path)),
            types.SimpleNamespace(file="image.png", path=self.path),
        ):
            self.assertEqual(
                os.path.abspath(module.ComfyUIDrawPlugin._local_image_path(comp)),
                os.path.abspath(self.path),
            )
        self.assertIsNone(module.ComfyUIDrawPlugin._local_image_path(
            types.SimpleNamespace(file="https://example.com/a.png")
        ))
        self.assertIsNone(module.ComfyUIDrawPlugin._local_image_path(
            types.SimpleNamespace(file="file:///definitely/missing.png")
        ))

    async def test_file_uri_image_is_collected(self):
        Image = module.Comp.Image
        comp = Image(file="file:///" + os.path.abspath(self.path))
        images = await plugin()._collect_input_images(self.event_with(comp), limit=2)
        self.assertEqual(images, [PNG])

    async def test_oversized_local_image_is_rejected(self):
        Image = module.Comp.Image
        comp = Image(file="file:///" + os.path.abspath(self.path))
        obj = plugin({"max_input_size_mb": 1})
        with open(self.path, "wb") as f:
            f.write(b"\x00" * (1024 * 1024 + 1))
        with self.assertRaisesRegex(PluginError, "体积上限"):
            await obj._collect_input_images(self.event_with(comp))


class ComfyPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_json_prompt_response_is_readable(self):
        class WS:
            async def close(self):
                return None

        class PromptResponse:
            status = 502

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def json(self, content_type=None):
                raise json.JSONDecodeError("Expecting value", "<html>", 0)

        class ComfySession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def ws_connect(self, *_args, **_kwargs):
                return WS()

            def post(self, *_args, **_kwargs):
                return PromptResponse()

        with patch.object(module.aiohttp, "ClientSession", return_value=ComfySession(), create=True):
            with self.assertRaisesRegex(PluginError, "HTTP 502"):
                await plugin()._run_comfyui_inner({"1": {"class_type": "X", "inputs": {}}}, 5)


class SizeTests(unittest.TestCase):
    def test_resolve_size_matches_strict_parser_and_defaults(self):
        obj = plugin({"default_width": 640, "default_height": 900})
        self.assertEqual(obj._resolve_size("768x1024"), (768, 1024))
        self.assertEqual(obj._resolve_size("770×1030"), (768, 1032))
        self.assertEqual(obj._resolve_size("9999*10"), (2048, 64))
        self.assertEqual(obj._resolve_size("big"), (640, 896))
        self.assertEqual(obj._resolve_size(None), (640, 896))


if __name__ == "__main__":
    unittest.main(verbosity=2)
