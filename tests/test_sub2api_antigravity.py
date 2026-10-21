"""Offline protocol and render regressions: no live API calls or credentials."""
import asyncio
import base64
import json
import types
import unittest
from unittest.mock import patch

from test_optimized_plugin import Event, Plain, Reply, module, plugin, PluginError


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aU1cAAAAASUVORK5CYII="
)


def response(image=PNG, mime="image/png", thought=False):
    return {"candidates": [{"content": {"parts": [
        {"thought": thought, "inlineData": {
            "mimeType": mime, "data": base64.b64encode(image).decode("ascii")
        }}
    ]}, "finishReason": "STOP"}]}


def configured(**overrides):
    return plugin({
        "openai_image_provider": "sub2api-antigravity",
        "openai_image_base_url": "https://sub2.example/proxy/v1",
        "openai_image_api_key": "test-key-not-real",
        "show_progress": False,
        **overrides,
    })


class Response:
    def __init__(self, status=200, payload=None, raw=None, delay=0, length=None):
        self.status = status
        self.raw = raw if raw is not None else json.dumps(payload or response()).encode()
        self.delay = delay
        self.headers = {"Content-Length": str(length if length is not None else len(self.raw))}
        self.content = self

    async def __aenter__(self):
        if self.delay:
            await asyncio.sleep(self.delay)
        return self

    async def __aexit__(self, *_args):
        return False

    async def iter_chunked(self, size):
        for start in range(0, len(self.raw), size):
            yield self.raw[start:start + size]


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ConfigurationTests(unittest.TestCase):
    def test_urls_and_reverse_proxy_prefix(self):
        obj = configured()
        target = "https://sub2.example/proxy/antigravity/v1beta/models/gemini-3.1-flash-image:generateContent"
        for suffix in ("", "/", "/v1", "/v1/", "/v1beta", "/antigravity",
                       "/antigravity/v1", "/antigravity/v1beta",
                       "/v1/images/generations", "/images/edits",
                       "/antigravity/v1beta/models/old:streamGenerateContent?alt=sse"):
            with self.subTest(suffix=suffix):
                self.assertEqual(obj._antigravity_image_url("https://sub2.example/proxy" + suffix, obj._cloud_image_model()), target)
        self.assertIn("/models/custom%2Fmodel:generateContent", obj._antigravity_image_url("https://sub2.example", "models/custom/model"))
        for invalid in ("", "example.com", "file:///temp", "https://user:pass@example.com"):
            with self.assertRaises(PluginError):
                obj._antigravity_image_url(invalid, "gemini-image")

    def test_separate_models(self):
        self.assertEqual(configured(openai_image_model="gpt-image-2")._cloud_image_model(), "gemini-3.1-flash-image")
        self.assertEqual(configured(gemini_image_model="custom-image")._cloud_image_model(), "custom-image")
        self.assertEqual(plugin({"openai_image_model": "other-model"})._cloud_image_model(), "other-model")

    def test_aspect_and_resolution(self):
        obj = configured(gemini_image_resolution="2K")
        for size, ratio in (("1920x1080", "16:9"), ("1080x1920", "9:16"),
                            ("1024x1536", "2:3"), ("1536x1024", "3:2"),
                            ("16:9", "16:9"), ("1500×1000", "3:2"),
                            ("2560X1080", "21:9"), ("1x1", "1:1")):
            with self.subTest(size=size):
                self.assertEqual(obj._gemini_image_config(size), {"aspectRatio": ratio, "imageSize": "2K"})
        self.assertEqual(obj._gemini_image_config("auto", "4k"), {"imageSize": "4K"})
        self.assertEqual(obj._cloud_edit_source_size(PNG), "1x1")
        for size in ("bad", "0x10", "-10x1", "1x2x3"):
            with self.assertRaises(PluginError):
                obj._gemini_image_config(size)
        with self.assertRaises(PluginError):
            configured(gemini_image_resolution="8K")._gemini_image_config()
        with self.assertRaises(PluginError):
            obj._gemini_image_config("16:9", "high")

    def test_final_image_and_thought_filter(self):
        payload = response()
        parts = payload["candidates"][0]["content"]["parts"]
        parts.insert(0, response(b"preview", thought=True)["candidates"][0]["content"]["parts"][0])
        self.assertEqual(configured()._decode_gemini_image_results({"response": payload}), [(PNG, "gemini_0.png")])
        snake = {"candidates": [{"content": {"parts": [{"inline_data": {
            "mime_type": "image/webp", "data": base64.b64encode(b"webp").decode()
        }}]}}]}
        self.assertEqual(configured()._decode_gemini_image_results(snake), [(b"webp", "gemini_0.webp")])

    def test_invalid_blocked_and_oversized_images(self):
        obj = configured(max_output_size_mb=1)
        for payload in ([], {"candidates": "bad"}, response(thought=True),
                        {"error": {"message": "permission denied"}},
                        {"candidates": [{"content": {"parts": "bad"}}]}):
            with self.assertRaises(PluginError):
                obj._decode_gemini_image_results(payload)
        with self.assertRaisesRegex(PluginError, "SAFETY"):
            obj._decode_gemini_image_results({"promptFeedback": {"blockReason": "SAFETY"}})
        for value, message in (("", "为空"), ("not-base64!", "Base64"),
                               (base64.b64encode(b"x" * (1024 * 1024 + 1)).decode(), "体积上限")):
            payload = response()
            payload["candidates"][0]["content"]["parts"][0]["inlineData"]["data"] = value
            with self.assertRaisesRegex(PluginError, message):
                obj._decode_gemini_image_results(payload)


class RequestTests(unittest.IsolatedAsyncioTestCase):
    def transport(self, *responses):
        session = Session(responses)
        stub = patch.object(module.aiohttp, "ClientSession", return_value=session, create=True)
        return session, stub

    async def test_generation_request(self):
        session, stub = self.transport(Response())
        with stub:
            result = await configured()._run_openai_image("樱花树下的少女", "1920x1080", quality="2K", style="watercolor")
        self.assertEqual(result, [(PNG, "gemini_0.png")])
        url, request = session.calls[0]
        self.assertEqual(url, "https://sub2.example/proxy/antigravity/v1beta/models/gemini-3.1-flash-image:generateContent")
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-key-not-real")
        self.assertFalse(request["allow_redirects"])
        self.assertEqual(request["json"]["generationConfig"], {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"imageSize": "2K", "aspectRatio": "16:9"},
        })
        self.assertIn("watercolor", request["json"]["contents"][0]["parts"][0]["text"])
        for forbidden in ("model", "n", "response_format", "quality", "size"):
            self.assertNotIn(forbidden, request["json"])

    async def test_multi_image_edit_and_batch(self):
        jpeg = b"\xff\xd8\xffjpeg-source"
        session, stub = self.transport(Response(), Response())
        with stub:
            results = await configured()._run_openai_image_edit("变手办", [PNG, jpeg], "2:3", 2)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual([item[1] for item in results], ["gemini_0.png", "gemini_1.png"])
        parts = session.calls[0][1]["json"]["contents"][0]["parts"]
        self.assertEqual(base64.b64decode(parts[0]["inlineData"]["data"]), PNG)
        self.assertEqual(parts[1]["inlineData"]["mimeType"], "image/jpeg")
        self.assertEqual(parts[2], {"text": "变手办"})

    async def test_failures_do_not_retry(self):
        for item, message in ((Response(403, {"error": {"message": "forbidden"}}), "分组"),
                              (Response(404, raw=b"<html>not found</html>"), "HTTP 404"),
                              (Response(payload={"candidates": []}), "没有返回"),
                              (OSError("private test-key-not-real"), "OSError"),
                              (Response(length=100 * 1024 * 1024), "体积超过")):
            session, stub = self.transport(item)
            with stub, self.assertRaisesRegex(PluginError, message) as caught:
                await configured(max_output_size_mb=1)._run_openai_image("cat")
            self.assertNotIn("test-key-not-real", str(caught.exception))
            self.assertEqual(len(session.calls), 1)

    async def test_aspect_400_fallback_preserves_edit_and_batch(self):
        obj = configured(gemini_image_model="gemini-3.8-flash-image")
        rejected = {"error": {"message": "Aspect ratio is not enabled for this model"}}
        session, stub = self.transport(Response(400, rejected), Response(), Response())
        with stub:
            results = await obj._run_openai_image_edit("变手办", [PNG], "9:16", 2, quality="2K")
        self.assertEqual(len(results), 2)
        self.assertEqual(len(session.calls), 3)
        initial = session.calls[0][1]["json"]
        fallback = session.calls[1][1]["json"]
        self.assertEqual(initial["generationConfig"]["imageConfig"]["aspectRatio"], "9:16")
        self.assertEqual(fallback["generationConfig"]["imageConfig"], {"imageSize": "2K"})
        initial_parts = initial["contents"][0]["parts"]
        self.assertEqual(fallback["contents"][0]["parts"][:len(initial_parts)], initial_parts)
        self.assertIn("9:16", fallback["contents"][0]["parts"][-1]["text"])
        self.assertEqual(session.calls[2][1]["json"], fallback)

    async def test_aspect_capability_cache_is_scoped_to_model(self):
        obj = configured()
        rejected = {"error": {"message": "Aspect ratio is not enabled for this model"}}
        session, stub = self.transport(Response(400, rejected), Response(), Response(), Response())
        with stub:
            await obj._run_openai_image("cat", "16:9")
            await obj._run_openai_image("dog", "9:16")
            obj.config["gemini_image_model"] = "another-image-model"
            await obj._run_openai_image("bird", "4:3")
        cached = session.calls[2][1]["json"]
        self.assertNotIn("aspectRatio", cached["generationConfig"]["imageConfig"])
        self.assertIn("9:16", cached["contents"][0]["parts"][-1]["text"])
        self.assertEqual(session.calls[3][1]["json"]["generationConfig"]["imageConfig"]["aspectRatio"], "4:3")

    async def test_strict_and_other_errors_do_not_aspect_fallback(self):
        rejected = {"error": {"message": "Aspect ratio is not enabled for this model"}}
        for mode, status, payload in (("strict", 400, rejected), ("auto", 500, rejected),
                                      ("auto", 429, rejected),
                                      ("auto", 400, {"error": {"message": "invalid prompt"}})):
            session, stub = self.transport(Response(status, payload))
            with stub, self.assertRaises(PluginError):
                await configured(gemini_image_aspect_mode=mode)._run_openai_image("cat", "16:9")
            self.assertEqual(len(session.calls), 1)

    async def test_prompt_aspect_mode_omits_field_from_first_request(self):
        session, stub = self.transport(Response())
        with stub:
            await configured(gemini_image_aspect_mode="prompt")._run_openai_image("cat", "16:9")
        self.assertEqual(len(session.calls), 1)
        payload = session.calls[0][1]["json"]
        self.assertNotIn("aspectRatio", payload["generationConfig"]["imageConfig"])
        self.assertEqual(payload["contents"][0]["parts"][0], {"text": "cat"})
        self.assertIn("16:9", payload["contents"][0]["parts"][-1]["text"])
        with self.assertRaises(PluginError):
            configured(gemini_image_aspect_mode="invalid")._gemini_aspect_mode()

    async def test_aspect_fallback_is_bounded_to_one_retry(self):
        rejected = {"error": {"message": "Aspect ratio is not enabled for this model"}}
        session, stub = self.transport(Response(400, rejected), Response(400, rejected))
        with stub, self.assertRaisesRegex(PluginError, "模型映射"):
            await configured()._run_openai_image("cat", "16:9")
        self.assertEqual(len(session.calls), 2)

    async def test_timeout_keeps_completed_images(self):
        session, stub = self.transport(Response(), Response(delay=1.3))
        with stub, self.assertRaisesRegex(PluginError, "超时.*1/2") as caught:
            await configured(openai_image_timeout=1)._run_openai_image("cat", n=2)
        self.assertEqual(caught.exception.partial_results, [(PNG, "gemini_0.png")])
        self.assertEqual(len(session.calls), 2)

    async def test_partial_batch_stops_and_returns_completed(self):
        session, stub = self.transport(Response(), Response(429, {"error": {"message": "quota"}}))
        with stub, self.assertRaisesRegex(PluginError, "1/3") as caught:
            await configured()._run_openai_image("cat", n=3)
        self.assertEqual(caught.exception.partial_results, [(PNG, "gemini_0.png")])
        self.assertEqual(len(session.calls), 2)

    async def test_missing_key_invalid_resolution_and_gif_never_request(self):
        session, stub = self.transport()
        with stub:
            for obj, sources in ((configured(openai_image_api_key=""), [PNG]),
                                 (configured(gemini_image_resolution="8K"), [PNG]),
                                 (configured(), [b"GIF89a" + b"x" * 20])):
                with self.assertRaises(PluginError):
                    await obj._run_openai_image_edit("cat", sources)
            with self.assertRaises(PluginError):
                await configured()._run_openai_image_edit("cat", [])
            with self.assertRaisesRegex(PluginError, "控制台"):
                await configured()._fetch_cloud_quota()
        self.assertEqual(session.calls, [])

    async def render(self, obj, sources=(), **kwargs):
        async def collect(_event, limit):
            return list(sources)
        obj._collect_input_images = collect
        obj._sweep_temp = lambda: None
        return [item async for item in obj._render_openai(Event(), "a cat", kwargs.pop("opts", {}), **kwargs)]

    async def test_presets_render_and_partial_results_are_sent(self):
        obj = configured()
        session, stub = self.transport(Response(), Response(429, {"error": {"message": "quota"}}))
        with stub:
            outputs = await self.render(obj, opts={"preset": "手办", "batch": 2})
        self.assertTrue(any(item[0] == "plain" and "1/2" in item[1] for item in outputs))
        self.assertEqual(outputs[-1][0], "chain")
        self.assertIn(("image", PNG), outputs[-1][1])
        texts = [part.get("text", "") for part in session.calls[0][1]["json"]["contents"][0]["parts"]]
        self.assertTrue(any("figurine" in text.lower() for text in texts))

    async def test_daily_card_actual_dimensions_and_model(self):
        obj = configured(openai_image_quality="high", gemini_image_resolution="1K")
        captured = {}
        async def card(desc, effective, model, data, filename):
            captured.update(effective=effective, model=model, data=data)
            return "C:/temp/card.png"
        obj._render_daily_me_card = card
        session, stub = self.transport(Response())
        with stub:
            output = await self.render(obj, caption_prefix="今日角色", daily_card=True, opts={"size": "1920x1080"})
        self.assertEqual(captured["effective"], {"width": 1, "height": 1})
        self.assertEqual(captured["model"], "云端·gemini-3.1-flash-image")
        self.assertIn(("image_path", "C:/temp/card.png"), output[-1][1])
        self.assertIn(("image", PNG), output[-1][1])
        self.assertEqual(session.calls[0][1]["json"]["generationConfig"]["imageConfig"]["imageSize"], "1K")

    async def test_source_ratio_and_explicit_size_override(self):
        for opts, ratio in (({"preset": "手办"}, "1:1"), ({"preset": "手办", "size": "16:9"}, "16:9")):
            session, stub = self.transport(Response())
            with stub:
                output = await self.render(configured(), [PNG], opts=opts)
            self.assertEqual(output[-1][0], "chain")
            self.assertEqual(session.calls[0][1]["json"]["generationConfig"]["imageConfig"]["aspectRatio"], ratio)


if __name__ == "__main__":
    unittest.main(verbosity=2)
