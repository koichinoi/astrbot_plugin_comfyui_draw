import asyncio
import importlib.util
import json
import sys
import tempfile
import time
import types
from pathlib import Path


class Logger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class Filter:
    @staticmethod
    def command(*_args, **_kwargs):
        return lambda fn: fn

    @staticmethod
    def llm_tool(*_args, **_kwargs):
        return lambda fn: fn


class Star:
    def __init__(self, context=None):
        self.context = context


class Image:
    def __init__(self, file=None):
        self.file = file

    @staticmethod
    def fromBytes(data):
        return ("image", data)

    @staticmethod
    def fromFileSystem(path):
        return ("image_path", path)

    @staticmethod
    def fromURL(url):
        return ("image_url", url)

    @staticmethod
    def fromBase64(data):
        return ("image_base64", data)


class Video:
    @staticmethod
    def fromFileSystem(path):
        return ("video_path", path)


class Plain:
    def __init__(self, text):
        self.text = text


class Reply:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")


class MessageChain:
    def __init__(self, chain):
        self.chain = chain


class Node:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


astrbot = types.ModuleType("astrbot")
api = types.ModuleType("astrbot.api")
event = types.ModuleType("astrbot.api.event")
star = types.ModuleType("astrbot.api.star")
components = types.ModuleType("astrbot.api.message_components")
api.logger = Logger()
api.AstrBotConfig = dict
event.filter = Filter()
event.AstrMessageEvent = object
event.MessageEventResult = object
event.MessageChain = MessageChain
star.Context = object
star.Star = Star
components.Image = Image
components.Video = Video
components.Plain = Plain
components.Reply = Reply
components.Node = Node
aiohttp = types.ModuleType("aiohttp")
aiohttp.ClientTimeout = lambda **kwargs: kwargs
aiohttp.FormData = object
aiohttp.ClientError = Exception
aiohttp.WSMsgType = types.SimpleNamespace(
    TEXT=1, BINARY=2, CLOSED=3, CLOSING=4, ERROR=5
)
sys.modules.update(
    {
        "aiohttp": aiohttp,
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.event": event,
        "astrbot.api.star": star,
        "astrbot.api.message_components": components,
    }
)

main_path = Path(__file__).resolve().parents[1] / "main.py"
spec = importlib.util.spec_from_file_location("optimized_plugin", main_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Plugin = module.ComfyUIDrawPlugin
PluginError = module.ComfyUIError


class Event:
    role = "member"
    message_str = "/绘图默认 other"

    @staticmethod
    def plain_result(text):
        return ("plain", text)

    @staticmethod
    def chain_result(chain):
        return ("chain", chain)

    @staticmethod
    def is_admin():
        return False


def plugin(config=None):
    obj = Plugin.__new__(Plugin)
    obj.config = {
        "max_batch_size": 4,
        "max_steps": 150,
        "max_cfg": 100,
        "max_total_pixels": 8_388_608,
        "max_prompt_length": 4000,
        "max_loras": 4,
        "max_lora_strength": 2,
        "default_loras": [],
        "auto_randomize_seed": True,
        **(config or {}),
    }
    obj._sem = asyncio.Semaphore(2)
    obj._daily_me_lock = asyncio.Lock()
    obj._daily_me_pending = set()
    obj._daily_me = {"date": module.time.strftime("%Y-%m-%d"), "used": {}}
    return obj


def assert_raises(fn, text):
    try:
        fn()
    except PluginError as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError("expected ComfyUIError")


def test_size_presets():
    obj = plugin()
    cases = {
        "--横图": "1216x832",
        "--landscape": "1216x832",
        "--竖图": "832x1216",
        "--portrait": "832x1216",
        "--方图": "1024x1024",
        "--square": "1024x1024",
        "--宽图": "1344x768",
        "--宽屏": "1344x768",
        "--wide": "1344x768",
    }
    for flag, expected in cases.items():
        prompt, opts = obj._parse_args(f"a cat {flag}")
        assert prompt == "a cat"
        assert opts["size"] == expected

    prompt, opts = obj._parse_args("a cat --横图 --size 640x640")
    assert prompt == "a cat"
    assert opts["size"] == "640x640"
    prompt, opts = obj._parse_args("a cat --size 640x640 --竖图")
    assert prompt == "a cat"
    assert opts["size"] == "832x1216"

    prompt, opts = obj._parse_args("a cat --neg bad hands --横图")
    assert prompt == "a cat"
    assert opts["negative"] == "bad hands"
    assert opts["size"] == "1216x832"

    _, cloud_opts = obj._parse_args("a cat --竖图", cloud=True)
    assert cloud_opts["size"] == "1024x1536"
    _, cloud_opts = obj._parse_args("a cat --宽屏", cloud=True)
    assert cloud_opts["size"] == "1536x1024"


def test_daily_me_traits_are_coherent():
    obj = plugin()
    prompts = set()
    for uid in range(120):
        prompt, desc = obj._daily_me_traits(f"daily-user-{uid}")
        prompts.add(prompt)
        assert prompt.startswith("1girl, solo,")
        assert "coherent outfit" in prompt
        assert "detailed face" in prompt
        assert prompt.count("witch hat") <= 1
        assert not any(
            unstable in prompt
            for unstable in ("crying, tears", "yandere smile", "star-shaped pupils")
        )
        assert "主题｜" in desc
        assert "形象｜" in desc
        assert "造型｜" in desc
        assert "场景｜" in desc
        assert len(prompt) < 1000
    assert len(prompts) >= 110

    negative = obj._daily_me_negative_prompt()
    for term in ("text", "watermark", "logo", "signature", "artist name", "username"):
        assert term in negative
    obj.config["daily_me_negative_prompt"] = ""
    assert obj._daily_me_negative_prompt() == ""


async def test_partial_placeholder_injection():
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 1,
                "steps": 20,
                "cfg": 7,
                "model": ["1", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "%prompt%", "clip": ["1", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "bad", "clip": ["1", 1]},
        },
    }
    obj = plugin(
        {
            "default_workflow": json.dumps(workflow),
            "show_progress": False,
            "send_seed_info": False,
        }
    )
    captured = {}

    async def fake_run(value):
        captured["workflow"] = value
        return [(b"png", "result.png")]

    async def no_input(_event, _workflow, _seed):
        return None

    obj._run_comfyui = fake_run
    obj._apply_input_images = no_input
    obj._sweep_temp = lambda: None
    results = [
        item
        async for item in obj._render(
            Event(),
            "a cat",
            {
                "negative": None,
                "size": "768x1024",
                "steps": "30",
                "cfg": None,
                "seed": "42",
                "batch": None,
                "workflow": None,
                "loras": [],
            },
            caption_prefix="每日角色说明",
        )
    ]
    actual = captured["workflow"]
    assert actual["6"]["inputs"]["text"] == "a cat"
    assert actual["3"]["inputs"]["steps"] == 30
    assert actual["5"]["inputs"]["width"] == 768
    assert actual["5"]["inputs"]["height"] == 1024
    assert results and results[-1][0] == "chain"
    assert isinstance(results[-1][1][0], Plain)
    assert results[-1][1][0].text == "每日角色说明"


async def test_admin_guard():
    obj = plugin({"extra_workflows": [{"name": "other", "workflow": module.DEFAULT_WORKFLOW}]})
    output = [item async for item in obj.set_default(Event())]
    assert "管理员" in output[-1][1]
    assert obj.config.get("default_workflow_name") is None


async def test_daily_reservation():
    obj = plugin()
    results = await asyncio.gather(
        obj._daily_me_reserve("u"),
        obj._daily_me_reserve("u"),
    )
    assert sorted(results) == [False, True]
    await obj._daily_me_finish("u", False)
    assert await obj._daily_me_reserve("u") is True
    await obj._daily_me_finish("u", False)
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "daily.json"
        obj._daily_me_path = lambda: str(path)
        assert await obj._daily_me_reserve("saved-user") is True
        await obj._daily_me_finish("saved-user", True)
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["used"]["saved-user"] == 1
        assert not Path(str(path) + ".tmp").exists()


async def test_total_timeout():
    obj = plugin({"timeout": 1})

    async def slow_inner(_workflow, _timeout):
        await asyncio.sleep(2)

    obj._run_comfyui_inner = slow_inner
    started = time.monotonic()
    try:
        await obj._run_comfyui({})
    except asyncio.TimeoutError:
        pass
    else:
        raise AssertionError("full-chain timeout did not fire")
    assert time.monotonic() - started < 1.5


async def test_chinese_prompt_translation():
    class Response:
        completion_text = (
            "silver-white long hair, blue and white dress, sitting under a large "
            "blooming cherry blossom tree, visible trunk and pink flowering branches"
        )

    class Provider:
        async def text_chat(self, **kwargs):
            assert "樱花树" in kwargs["prompt"]
            assert kwargs["contexts"] == []
            return Response()

    class Context:
        @staticmethod
        def get_using_provider(_umo=None):
            return Provider()

    obj = plugin(
        {
            "enable_prompt_translation": True,
            "prompt_translation_workflows": ["鬼针草-中文"],
            "prompt_translation_timeout": 5,
        }
    )
    obj.context = Context()
    translated = await obj._maybe_translate_draw_prompt(
        Event(),
        "银白色长发的少女坐在樱花树下，穿蓝白色连衣裙",
        "鬼针草-中文",
    )
    assert "cherry blossom tree" in translated
    assert "silver-white long hair" in translated

    obj.context = None
    fallback = await obj._maybe_translate_draw_prompt(
        Event(),
        "银白色长发的少女坐在樱花树下，穿蓝白色连衣裙",
        "鬼针草-中文",
    )
    assert "cherry blossom tree" in fallback
    assert "blue and white dress" in fallback

    untouched = await obj._maybe_translate_draw_prompt(
        Event(), "樱花树下的少女", "小叶子"
    )
    assert untouched == "樱花树下的少女"


async def test_progress_auto_recall():
    class Result:
        def __init__(self, text):
            self.chain = [Plain(text)]

    class Bot:
        def __init__(self):
            self.sent = []
            self.deleted = []

        async def send_group_msg(self, **params):
            self.sent.append(params)
            return {"data": {"message_id": "321"}}

        async def delete_msg(self, **params):
            self.deleted.append(params)

    class RecallEvent(Event):
        def __init__(self):
            self.bot = Bot()

        @staticmethod
        def plain_result(text):
            return Result(text)

        @staticmethod
        def get_group_id():
            return "12345"

        @staticmethod
        def get_sender_id():
            return "67890"

        @staticmethod
        async def _parse_onebot_json(message_chain):
            return [("text", message_chain.chain[0].text)]

    obj = plugin(
        {
            "auto_recall_progress": True,
            "progress_recall_delay_ms": 0,
        }
    )
    recall_event = RecallEvent()
    message_id, sent = await obj._send_progress_message(
        recall_event, "🎨 正在生成..."
    )
    assert sent is True
    assert message_id == "321"
    assert recall_event.bot.sent[0]["group_id"] == 12345
    await obj._recall_progress_message(recall_event, message_id)
    assert recall_event.bot.deleted == [{"message_id": 321}]


async def test_daily_me_card_reply_and_original():
    class DailyEvent(Event):
        message_obj = types.SimpleNamespace(message_id="source-123")

    obj = plugin(
        {
            "default_workflow": module.DEFAULT_WORKFLOW,
            "show_progress": False,
            "send_seed_info": True,
        }
    )
    captured_card = {}

    async def fake_run(_workflow):
        return [(b"full-resolution-image", "daily.png")]

    async def no_input(_event, _workflow, _seed):
        return None

    async def fake_html_render(_template, data):
        captured_card.update(data)
        return "C:/temp/daily-card.png"

    obj._run_comfyui = fake_run
    obj._apply_input_images = no_input
    obj._sweep_temp = lambda: None
    obj.html_render = fake_html_render

    description = (
        "✨ 今日的二次元的你\n"
        "主题｜玻璃花房\n"
        "形象｜银发·短波波头｜蓝瞳｜温柔微笑\n"
        "造型｜薄荷色连衣裙与蝴蝶发饰\n"
        "场景｜在温室花草间轻触花瓣\n"
        "（每人每天一抽，明天会是新形象哦～）"
    )
    output = [
        item
        async for item in obj._render(
            DailyEvent(),
            "1girl, silver hair",
            {
                "negative": None,
                "size": None,
                "steps": None,
                "cfg": None,
                "seed": None,
                "batch": None,
                "workflow": None,
                "loras": [],
            },
            caption_prefix=description,
            daily_card=True,
            reply_to_source=True,
        )
    ]
    chain = output[-1][1]
    assert isinstance(chain[0], Reply)
    assert chain[0].id == "source-123"
    assert chain[1] == ("image_path", "C:/temp/daily-card.png")
    assert chain[2] == ("image", b"full-resolution-image")
    assert not any(isinstance(item, Plain) for item in chain)
    assert captured_card["items"][0]["value"] == "玻璃花房"
    assert captured_card["preview_data_uri"].startswith("data:image/png;base64,")
    assert "工作流=默认" in captured_card["meta"]
    assert obj._rendered_image_component(
        "http://127.0.0.1:8999/text2img/data/card.jpeg"
    ) == (
        "image_url",
        "http://127.0.0.1:8999/text2img/data/card.jpeg",
    )


def test_validation_and_multimodel_lora():
    obj = plugin()
    assert_raises(
        lambda: obj._normalize_options("x", {"steps": "999"}, cloud=False),
        "采样步数",
    )
    assert_raises(
        lambda: obj._normalize_options("x", {"cfg": "nan"}, cloud=False),
        "CFG",
    )
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {}},
        "2": {"class_type": "UNETLoader", "inputs": {}},
        "3": {"class_type": "KSampler", "inputs": {"model": ["1", 0]}},
        "4": {"class_type": "KSampler", "inputs": {"model": ["2", 0]}},
    }
    obj._inject_lora(workflow, [("style.safetensors", 0.8)])
    assert workflow["3"]["inputs"]["model"][0] != "1"
    assert workflow["4"]["inputs"]["model"][0] != "2"
    loaders = [
        node for node in workflow.values() if node.get("class_type") == "LoraLoaderModelOnly"
    ]
    assert len(loaders) == 2


def test_daily_card_fills_render_canvas():
    template = module.DAILY_ME_CARD_TMPL
    assert "width: 100vw;" in template
    assert "min-width: 900px;" in template
    assert ".card {\n    width: 100%;" in template
    assert ".card {\n    width: 900px;" not in template


def test_chatgpt2api_profile():
    obj = plugin({"openai_image_provider": "chatgpt2api"})
    assert obj._openai_image_urls("http://127.0.0.1:3000") == [
        "http://127.0.0.1:3000/v1/images/generations"
    ]
    assert obj._openai_image_urls("http://127.0.0.1:3000/v1") == [
        "http://127.0.0.1:3000/v1/images/generations"
    ]
    endpoint = "http://127.0.0.1:3000/v1/images/generations"
    assert obj._openai_image_urls(endpoint) == [endpoint]
    assert obj._openai_image_response_format() == "b64_json"

    auto = plugin({"openai_image_provider": "auto"})
    assert auto._openai_image_urls("http://127.0.0.1:3000") == [
        "http://127.0.0.1:3000/images/generations",
        "http://127.0.0.1:3000/v1/images/generations",
    ]
    assert "bad request" in auto._format_openai_error(
        {"detail": [{"msg": "bad request"}]}, 422
    )

    invalid = plugin({"openai_image_response_format": "invalid"})
    assert_raises(invalid._openai_image_response_format, "response_format")


async def test_actual_workflows():
    root = Path(__file__).parent / "actual_workflows"
    if not root.is_dir():
        return
    passed = []
    for path in sorted(root.glob("*.json")):
        obj = plugin(
            {
                "workflow_dir": str(root),
                "show_progress": False,
                "send_seed_info": False,
                "prompt_mode": "prepend",
            }
        )
        captured = {}

        async def fake_run(value):
            captured["workflow"] = value
            return [(b"result", "result.png")]

        async def no_input(_event, _workflow, _seed):
            return None

        obj._run_comfyui = fake_run
        obj._apply_input_images = no_input
        obj._sweep_temp = lambda: None
        output = [
            item
            async for item in obj._render(
                Event(),
                "compatibility test prompt",
                {
                    "negative": "bad quality",
                    "size": "768x1024",
                    "steps": "25",
                    "cfg": "7",
                    "seed": "42",
                    "batch": "1",
                    "workflow": path.stem,
                    "loras": [],
                },
            )
        ]
        if "workflow" not in captured:
            messages = [
                item[1] for item in output if isinstance(item, tuple) and item[0] == "plain"
            ]
            raise AssertionError(f"{path.name} failed: {messages}")
        assert output[-1][0] == "chain", path.name
        assert obj._format_problem(captured["workflow"]) is None
        passed.append(path.name)
    print("actual workflows:", ", ".join(passed))


async def main():
    test_size_presets()
    test_daily_me_traits_are_coherent()
    await test_partial_placeholder_injection()
    await test_admin_guard()
    await test_daily_reservation()
    await test_total_timeout()
    await test_chinese_prompt_translation()
    await test_progress_auto_recall()
    await test_daily_me_card_reply_and_original()
    test_validation_and_multimodel_lora()
    test_daily_card_fills_render_canvas()
    test_chatgpt2api_profile()
    await test_actual_workflows()
    print("optimized plugin core tests: OK")


if __name__ == "__main__":
    asyncio.run(main())
