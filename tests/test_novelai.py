"""NovelAI request/response and integration tests; no real tokens or network."""
import asyncio
import base64
import io
import json
import unittest
import zipfile
from unittest.mock import patch

from test_optimized_plugin import Event, module, plugin, PluginError
from test_sub2api_antigravity import PNG, Response, Session

KEY = "nai-token-not-real"


def nai(**overrides):
    obj = plugin({"openai_image_provider": "novelai", "nai_api_key": KEY,
                  "show_progress": False, "text_as_card": False, **overrides})
    obj._sweep_temp = lambda: None
    obj._add_usage = lambda *_: None
    obj._record_history = lambda *_args, **_kwargs: None
    obj._daily_me_save = lambda: None
    return obj


def archive(image=PNG, name="image_0.png", extras=()):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr(name, image)
        for key, value in extras:
            output.writestr(key, value)
    return stream.getvalue()


class PayloadTests(unittest.TestCase):
    def test_models_and_v4_caption_structure(self):
        obj = nai()
        for alias, model in obj.NAI_MODEL_ALIASES.items():
            with self.subTest(alias=alias):
                payload = obj._build_nai_payload("博丽灵梦，樱花树", options={"model": alias, "negative": "watermark"})
                self.assertEqual(payload["model"], model)
                self.assertEqual(payload["parameters"]["n_samples"], 1)
                if model.startswith(("nai-diffusion-4", "nai-diffusion-5")):
                    p = payload["parameters"]
                    self.assertEqual(p["v4_prompt"]["caption"], {"base_caption": payload["input"], "char_captions": []})
                    self.assertEqual(p["v4_negative_prompt"]["caption"]["base_caption"], "watermark")
                    self.assertFalse(p["use_coords"])
                else:
                    self.assertNotIn("v4_prompt", payload["parameters"])

    def test_zero_seed_parameters_and_negative_override(self):
        obj = nai(nai_seed=12, nai_negative_prompt="configured negative")
        p = obj._build_nai_payload("a girl", options={"seed": 0, "steps": 28, "cfg": 5, "negative": ""})["parameters"]
        self.assertEqual((p["seed"], p["steps"], p["scale"], p["negative_prompt"]), (0, 28, 5, ""))
        p = obj._build_nai_payload("a girl")["parameters"]
        self.assertEqual((p["seed"], p["negative_prompt"]), (12, "configured negative"))
        p = nai()._build_nai_payload("cat")["parameters"]
        self.assertGreaterEqual(p["seed"], 0)
        self.assertLessEqual(p["seed"], 2 ** 32 - 1)

    def test_cost_limit_dimensions_and_unlimited_mode(self):
        obj = nai()
        self.assertEqual(obj._nai_dimensions(), (832, 1216))
        self.assertEqual(obj._nai_dimensions("1024x1024"), (1024, 1024))
        for size in ("1536x1024", "1080x1920", "16:9", "49152x64", "500×900"):
            width, height = obj._nai_dimensions(size)
            self.assertEqual((width % 64, height % 64), (0, 0))
            self.assertLessEqual(width * height, 1048576)
        large = nai(nai_limit_cost=False)._build_nai_payload("cat", "2048x1536", options={"steps": 50})
        self.assertEqual((large["parameters"]["width"], large["parameters"]["height"], large["parameters"]["steps"]), (2048, 1536, 50))

    def test_invalid_numeric_options_and_size(self):
        obj = nai()
        for options in ({"seed": -2}, {"seed": 2 ** 32}, {"seed": True}, {"steps": 29},
                        {"steps": 2.5}, {"cfg": "nan"}, {"cfg": 11}, {"sampler": "bad"},
                        {"schedule": "bad"}, {"quality": "2K"}):
            with self.subTest(options=options), self.assertRaises(PluginError):
                obj._build_nai_payload("cat", options=options)
        for size in ("0x1024", "1x1", "bad", "0:9", "100000x100000", "NaNx1"):
            with self.subTest(size=size), self.assertRaises(PluginError):
                obj._nai_dimensions(size)

    def test_img2img_raw_data_and_strength(self):
        obj = nai()
        payload = obj._build_nai_payload("make a figurine", source_images=[PNG], options={"seed": 0, "strength": 0.55, "noise": 0.1})
        p = payload["parameters"]
        self.assertEqual(payload["action"], "img2img")
        self.assertEqual(base64.b64decode(p["image"]), PNG)
        self.assertEqual((p["seed"], p["extra_noise_seed"], p["strength"], p["noise"]), (0, 0, 0.55, 0.1))
        for sources, options in (([PNG, PNG], {}), ([b"GIF89a"], {}), ([PNG], {"strength": 1.1}), ([PNG], {"noise": -1})):
            with self.assertRaises(PluginError):
                obj._build_nai_payload("cat", source_images=sources, options=options)

    def test_connection_uses_independent_base_token_and_model(self):
        obj = nai(openai_image_base_url="https://other.example", openai_image_api_key="other-key-not-real", openai_image_model="gpt-image-2")
        conn = obj._cloud_connection()
        self.assertEqual((conn["base_url"], conn["api_key"], conn["model"]), ("https://image.novelai.net", KEY, "nai-diffusion-5-full"))
        self.assertEqual(nai(nai_api_key="", openai_image_api_key="other-key-not-real")._cloud_connection()["api_key"], "")
        obj.config.update(cloud_profiles=[{"name": "NAI", "provider": "novelai", "base_url": "https://nai.example", "model": "v4.5"}], active_cloud_profile="NAI")
        conn = obj._cloud_connection()
        self.assertEqual((conn["api_key"], conn["model"]), ("", "nai-diffusion-4-5-full"))
        obj.config["cloud_profiles"][0]["api_key"] = "profile-token-not-real"
        self.assertEqual(obj._cloud_connection()["api_key"], "profile-token-not-real")

    def test_url_validation(self):
        obj = nai()
        for base in ("https://image.novelai.net", "https://nai.example/prefix/", "https://nai.example/ai/generate-image"):
            self.assertTrue(obj._nai_url(base).endswith("/ai/generate-image"))
        for base in ("file:///tmp", "http://user:pass@site", "https://site?key=secret", "not-a-url"):
            with self.assertRaises(PluginError):
                obj._nai_url(base)

    def test_zip_and_official_json_decoding(self):
        obj = nai()
        self.assertEqual(obj._decode_nai_image(archive(extras=[("metadata.json", "{}")]))[0], PNG)
        # 成员路径不会写到文件系统，只在内存读取。
        self.assertEqual(obj._decode_nai_image(archive(name="../../image.png"))[0], PNG)
        for images in ([{"image": base64.b64encode(PNG).decode(), "seed": 0}], [base64.b64encode(PNG).decode()]):
            self.assertEqual(obj._decode_nai_image(json.dumps({"images": images}).encode()), (PNG, "png"))

    def test_malformed_and_oversized_zip_json(self):
        obj = nai(max_output_size_mb=1)
        for raw in (b"PKbroken", b"<html>bad</html>", archive(b"not-image"), archive(b"x", name="metadata.txt"),
                    archive(PNG + b"x" * (1024 * 1024)), json.dumps({"images": [{"image": "!bad!"}]}).encode(),
                    archive(extras=[(str(i), "x") for i in range(33)])):
            with self.subTest(prefix=raw[:8]), self.assertRaises(PluginError):
                obj._decode_nai_image(raw)

    def test_argument_aliases_and_daily_prompt(self):
        obj = nai()
        prompt, opts = obj._parse_args("a girl --model v5 --uc lowres, watermark --seed 0 --steps 23 --cfg 5 --strength 0.5 --sampler k_euler --noise 0.1", cloud=True)
        self.assertEqual(prompt, "a girl")
        self.assertEqual(opts["negative"], "lowres, watermark")
        self.assertEqual((opts["seed"], opts["model"], opts["strength"]), ("0", "v5", "0.5"))
        self.assertEqual(obj._daily_me_cloud_prompt("1girl, shrine"), "1girl, shrine")


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    def transport(self, *responses):
        session = Session(responses)
        return session, patch.object(module.aiohttp, "ClientSession", return_value=session, create=True)

    async def test_zip_201_generation_request(self):
        session, stub = self.transport(Response(201, raw=archive()))
        with stub:
            result = await nai(nai_seed=0)._run_openai_image("樱花树下的少女")
        self.assertEqual(result, [(PNG, "nai_0_0.png")])
        url, kwargs = session.calls[0]
        self.assertEqual(url, "https://image.novelai.net/ai/generate-image")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual(kwargs["json"]["parameters"]["n_samples"], 1)
        self.assertEqual(kwargs["json"]["action"], "generate")

    async def test_json_200_img2img_with_proxy_and_bearer_token(self):
        raw = json.dumps({"images": [{"image": base64.b64encode(PNG).decode()}]}).encode()
        session, stub = self.transport(Response(200, raw=raw))
        with stub:
            await nai(nai_api_key="Bearer " + KEY, nai_proxy_url="http://127.0.0.1:7890")._run_openai_image_edit("变手办", [PNG])
        request = session.calls[0][1]
        self.assertEqual(request["headers"]["Authorization"], "Bearer " + KEY)
        self.assertEqual(request["proxy"], "http://127.0.0.1:7890")
        self.assertEqual(request["json"]["action"], "img2img")

    async def test_batch_seeds_and_partial_results(self):
        session, stub = self.transport(Response(201, raw=archive()), Response(201, raw=archive()), Response(429, {"message": "rate limited"}))
        with stub, self.assertRaisesRegex(PluginError, "2/3") as caught:
            await nai(nai_seed=0)._run_nai_image("cat", n=3)
        self.assertEqual(len(caught.exception.partial_results), 2)
        self.assertEqual([kwargs["json"]["parameters"]["seed"] for _, kwargs in session.calls], [0, 1, 2])
        self.assertEqual(len(session.calls), 3)

    async def test_validation_never_sends_network_requests(self):
        session, stub = self.transport()
        cases = [(nai(nai_api_key="", openai_image_api_key="other-key"), {}),
                 (nai(nai_steps=29), {}), (nai(nai_proxy_url="socks5://localhost"), {}),
                 (nai(max_total_pixels=4096), {}), (nai(), {"source_images": [PNG, PNG]})]
        with stub:
            for obj, kwargs in cases:
                with self.assertRaises(PluginError):
                    await obj._run_nai_image("cat", **kwargs)
        self.assertEqual(session.calls, [])

    async def test_http_errors_are_redacted_and_not_retried(self):
        for status in (400, 401, 402, 403, 429, 500):
            session, stub = self.transport(Response(status, {"message": "bad " + KEY}))
            with stub, self.assertRaisesRegex(PluginError, f"HTTP {status}") as caught:
                await nai()._run_nai_image("cat")
            self.assertNotIn(KEY, str(caught.exception))
            self.assertEqual(len(session.calls), 1)

    async def test_timeout_keeps_generated_images(self):
        session, stub = self.transport(Response(201, raw=archive()), Response(201, raw=archive(), delay=1.3))
        with stub, self.assertRaisesRegex(PluginError, "超时.*1/2") as caught:
            await nai(openai_image_timeout=1)._run_nai_image("cat", n=2)
        self.assertEqual(len(caught.exception.partial_results), 1)

    async def test_same_token_requests_run_serially(self):
        active, maximum = 0, 0

        class CountingResponse(Response):
            async def __aenter__(self):
                nonlocal active, maximum
                active += 1
                maximum = max(maximum, active)
                await asyncio.sleep(0.02)
                return self

            async def __aexit__(self, *_):
                nonlocal active
                active -= 1

        session, stub = self.transport(CountingResponse(201, raw=archive()), CountingResponse(201, raw=archive()))
        obj = nai()
        with stub:
            await asyncio.gather(obj._run_nai_image("cat"), obj._run_nai_image("dog"))
        self.assertEqual(maximum, 1)

    async def test_cloud_render_passes_model_negative_seed_and_edit_parameters(self):
        obj = nai(nai_seed=8)
        async def collect(_event, limit):
            return []
        obj._collect_input_images = collect
        session, stub = self.transport(Response(201, raw=archive()))
        prompt, opts = obj._parse_args("a girl --model v3 --uc watermark --seed 0 --steps 20 --cfg 4", cloud=True)
        with stub:
            output = [item async for item in obj._render_openai(Event(), prompt, opts)]
        self.assertEqual(output[-1][0], "chain")
        body = session.calls[0][1]["json"]
        self.assertEqual(body["model"], "nai-diffusion-3")
        self.assertEqual((body["parameters"]["seed"], body["parameters"]["negative_prompt"]), (0, "watermark"))
        self.assertEqual(obj.config.get("nai_model"), None)  # 单次 --model 不修改配置

    async def test_daily_me_cloud_keeps_own_negative_and_card(self):
        obj = nai(daily_me_backend="cloud", daily_me_cloud_size="832x1216", daily_me_result_card=False,
                  daily_me_reply_source=False, daily_me_negative_prompt="watermark, bad hands")
        session, stub = self.transport(Response(201, raw=archive()))
        with stub:
            output = [item async for item in obj.daily_me(Event())]
        self.assertEqual(output[-1][0], "chain")
        p = session.calls[0][1]["json"]["parameters"]
        self.assertEqual(p["negative_prompt"], "watermark, bad hands")
        self.assertEqual((p["width"], p["height"]), (832, 1216))


if __name__ == "__main__":
    unittest.main(verbosity=2)
