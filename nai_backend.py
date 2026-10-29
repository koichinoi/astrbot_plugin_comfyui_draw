"""NovelAI 原生图片接口；按公开 API schema 构建请求，不依赖 Yunzai。"""
import asyncio
import base64
import hashlib
import io
import json
import math
import secrets
import zipfile
from urllib.parse import urlsplit

import aiohttp

from .errors import ComfyUIError


class NovelAIBackendMixin:
    NAI_DEFAULT_BASE = "https://image.novelai.net"
    NAI_DEFAULT_MODEL = "nai-diffusion-5-full"
    NAI_NEGATIVE = "nsfw, lowres, worst quality, bad quality, blurry, jpeg artifacts, watermark, logo, signature"
    NAI_MODEL_ALIASES = {
        "v5": "nai-diffusion-5-full", "v5-full": "nai-diffusion-5-full",
        "v5-curated": "nai-diffusion-5-curated",
        "v4.5": "nai-diffusion-4-5-full", "v4.5-full": "nai-diffusion-4-5-full",
        "v4.5-curated": "nai-diffusion-4-5-curated",
        "v4": "nai-diffusion-4-full", "v4-full": "nai-diffusion-4-full",
        "v4-curated": "nai-diffusion-4-curated-preview",
        "v3": "nai-diffusion-3", "furry-v3": "nai-diffusion-furry-3",
    }
    NAI_SAMPLERS = {"k_euler_ancestral", "k_euler", "k_dpmpp_2m", "k_dpmpp_2s_ancestral", "k_dpmpp_sde", "k_dpmpp_2m_sde", "ddim_v3"}

    @classmethod
    def _nai_model(cls, value):
        value = str(value or cls.NAI_DEFAULT_MODEL).strip()
        return cls.NAI_MODEL_ALIASES.get(value.lower(), value)

    @staticmethod
    def _nai_url(base):
        base = str(base or "").strip().rstrip("/")
        uri = urlsplit(base)
        if uri.scheme not in {"http", "https"} or not uri.netloc or uri.username or uri.password or uri.query or uri.fragment:
            raise ComfyUIError("NAI 地址需为不含账号密码和查询参数的 http(s) 服务地址。")
        return base if uri.path.endswith("/ai/generate-image") else base + "/ai/generate-image"

    @staticmethod
    def _nai_number(value, label, minimum, maximum, integer=False):
        try:
            if isinstance(value, bool):
                raise ValueError
            number = float(value)
            if not math.isfinite(number) or not minimum <= number <= maximum:
                raise ValueError
            if integer and number != int(number):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ComfyUIError(f"NAI {label}必须为 {minimum:g}–{maximum:g} 的{'整数' if integer else '有限数值'}。") from None
        return int(number) if integer else number

    def _nai_dimensions(self, size=None):
        text = str(size or self.config.get("nai_image_size", "832x1216") or "832x1216").strip().lower()
        for sep in ("*", "×", "✕", "✖"):
            text = text.replace(sep, "x")
        max_pixels = 1048576 if self.config.get("nai_limit_cost", True) else 3145728
        ratio_only = ":" in text
        try:
            width, height = (int(v.strip()) for v in text.replace(":", "x").split("x"))
            if ratio_only:
                if not (1 <= width <= 100 and 1 <= height <= 100):
                    raise ValueError
                ratio = width / height
                width, height = math.sqrt(max_pixels * ratio), math.sqrt(max_pixels / ratio)
            elif not (64 <= width <= 49152 and 64 <= height <= 49152):
                raise ValueError
        except (ValueError, OverflowError):
            raise ComfyUIError("NAI 尺寸应为 64–49152 的宽x高，或 16:9 等正整数比例。") from None
        scale = min(1.0, math.sqrt(max_pixels / (width * height)))
        # 向下对齐防止四舍五入后超过像素预算；最低为 64 像素。
        width = max(64, int(width * scale / 64) * 64)
        height = max(64, int(height * scale / 64) * 64)
        while width * height > max_pixels:
            if width >= height:
                width -= 64
            else:
                height -= 64
        return width, height

    def _build_nai_payload(self, prompt, size=None, source_images=None, options=None, model=None):
        options = options or {}
        model = self._nai_model(options.get("model") or model or self.config.get("nai_model"))
        if not self._valid_model_name(model):
            raise ComfyUIError("NAI 模型名格式不正确。")
        width, height = self._nai_dimensions(size)

        def setting(option, config, default):
            value = options.get(option)
            return self.config.get(config, default) if value is None else value

        max_steps = 28 if self.config.get("nai_limit_cost", True) else 50
        steps = self._nai_number(setting("steps", "nai_steps", 23), "步数", 1, max_steps, True)
        seed = setting("seed", "nai_seed", -1)
        if str(seed).strip() == "-1":
            seed = secrets.randbits(32)
        else:
            seed = self._nai_number(seed, "种子", 0, 2 ** 32 - 1, True)
        scale = self._nai_number(setting("cfg", "nai_scale", 6), "CFG", 0, 10)
        rescale = self._nai_number(self.config.get("nai_cfg_rescale", 0), "CFG rescale", 0, 1)
        sampler = str(setting("sampler", "nai_sampler", "k_euler_ancestral")).strip()
        schedule = str(setting("schedule", "nai_noise_schedule", "karras")).strip()
        if sampler not in self.NAI_SAMPLERS:
            raise ComfyUIError("NAI 采样器不受支持，请使用 k_euler_ancestral、k_euler 或 k_dpmpp_2m 等。")
        if schedule not in {"native", "karras", "exponential", "polyexponential"}:
            raise ComfyUIError("NAI 噪声调度应为 native、karras、exponential 或 polyexponential。")
        negative = str(setting("negative", "nai_negative_prompt", self.NAI_NEGATIVE) or "").strip()
        text = str(prompt or "").strip()
        if not text:
            raise ComfyUIError("请填写 NAI 绘图提示词。")
        if options.get("style"):
            text += "\nStyle: " + str(options["style"]).strip()
        if options.get("quality"):
            raise ComfyUIError("NAI 不使用 --quality；请用 --steps、--cfg 和 --size 控制出图。")
        p = {
            "params_version": 3, "width": width, "height": height,
            "steps": steps, "seed": seed, "scale": scale, "cfg_rescale": rescale,
            "sampler": sampler, "noise_schedule": schedule, "n_samples": 1,
            "negative_prompt": negative, "qualityToggle": True, "ucPreset": 0,
            "legacy": False, "sm": False, "sm_dyn": False,
        }
        # V5 与 V4.x 的基本正负提示结构相同；V3 不携带 v4 字段。
        if model.startswith(("nai-diffusion-4", "nai-diffusion-5")):
            p["v4_prompt"] = {"caption": {"base_caption": text, "char_captions": []}, "use_coords": False, "use_order": True}
            p["v4_negative_prompt"] = {"caption": {"base_caption": negative, "char_captions": []}}
            p["characterPrompts"] = []
            p["use_coords"] = False
        sources = list(source_images or [])
        if len(sources) > 1:
            raise ComfyUIError("NAI 普通图生图一次仅支持一张原图；多图参考、Vibe 与 Precise Reference 暂未接入。")
        if sources:
            raw = sources[0]
            if not isinstance(raw, bytes) or not raw or len(raw) > self._max_bytes("max_input_size_mb", 20):
                raise ComfyUIError("NAI 原图为空或超过输入图片体积上限。")
            if not self._nai_image_extension(raw):
                raise ComfyUIError("NAI 原图请使用 PNG、JPEG 或 WebP。")
            p.update(
                image=base64.b64encode(raw).decode("ascii"), extra_noise_seed=seed,
                strength=self._nai_number(setting("strength", "nai_strength", 0.7), "重绘强度", 0, 1),
                noise=self._nai_number(setting("noise", "nai_noise", 0.2), "噪声强度", 0, 1),
            )
        return {"input": text, "model": model, "action": "img2img" if sources else "generate", "parameters": p}

    @staticmethod
    def _nai_image_extension(raw):
        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if raw.startswith(b"\xff\xd8\xff"):
            return "jpg"
        if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return "webp"
        return None

    def _decode_nai_image(self, raw):
        """ZIP 只在内存读取，先检查成员体积；同时兼容官方 JSON 图片响应。"""
        limit = self._max_bytes("max_output_size_mb", 100)
        image = None
        if raw.startswith(b"PK"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    members = archive.infolist()
                    if len(members) > 32:
                        raise ComfyUIError("NAI ZIP 响应成员过多。")
                    for member in members:
                        if member.is_dir() or not member.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            continue
                        if member.file_size <= 0 or member.file_size > limit or member.flag_bits & 1:
                            raise ComfyUIError("NAI ZIP 图片为空、加密或超过体积上限。")
                        with archive.open(member) as stream:
                            image = stream.read(limit + 1)
                        break
            except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError, EOFError, ValueError):
                raise ComfyUIError("NAI 返回了损坏或不支持的 ZIP 图片包。") from None
        else:
            try:
                payload = json.loads(raw.decode("utf-8"))
                images = payload.get("images") if isinstance(payload, dict) else None
                item = images[0] if isinstance(images, list) and images else None
                encoded = item.get("image") if isinstance(item, dict) else item
                if not isinstance(encoded, str):
                    raise ValueError
                if encoded.startswith("data:") and ";base64," in encoded:
                    encoded = encoded.split(";base64,", 1)[1]
                if len(encoded) > ((limit + 2) // 3) * 4:
                    raise ComfyUIError("NAI 返回的图片超过体积上限。")
                image = base64.b64decode(encoded, validate=True)
            except (UnicodeDecodeError, ValueError, TypeError):
                raise ComfyUIError("NAI 未返回可识别的 ZIP 或 JSON 图片数据。") from None
        if not image:
            raise ComfyUIError("NAI 响应中没有图片。")
        if len(image) > limit:
            raise ComfyUIError("NAI 返回的图片超过体积上限。")
        extension = self._nai_image_extension(image)
        if not extension:
            raise ComfyUIError("NAI 返回的文件不是支持的图片格式。")
        return image, extension

    async def _run_nai_image(self, prompt, size=None, n=1, source_images=None, options=None, conn=None):
        conn = conn or self._cloud_connection()
        key = str(conn.get("api_key") or "").strip()
        if key.lower().startswith("bearer "):
            key = key[7:].strip()
        if not key:
            raise ComfyUIError("请先填写 nai_api_key（NovelAI Persistent API Token），或在当前 NAI 方案中填写 API Key。")
        url = self._nai_url(conn.get("base_url") or self.NAI_DEFAULT_BASE)
        proxy = str(self.config.get("nai_proxy_url", "") or "").strip()
        if proxy:
            parsed = urlsplit(proxy)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ComfyUIError("NAI 正向代理需为 http(s) 地址。")
        options = dict(options or {})
        payload = self._build_nai_payload(prompt, size, source_images, options, conn.get("model"))
        count = self._clamp_batch(self._nai_number(n, "张数", 1, 100, True))
        p = payload["parameters"]
        if p["width"] * p["height"] * count > self._config_int("max_total_pixels", 8388608, 4096, 1000000000):
            raise ComfyUIError("NAI 本次宽×高×张数超过 max_total_pixels 限制，请减少尺寸或张数。")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/zip"}
        seconds = self._config_int("openai_image_timeout", 360, 1, 3600)
        results = []
        locks = getattr(self, "_nai_account_locks", None)
        if locks is None:
            locks = self._nai_account_locks = {}
        # 同一个 Token 串行，避免 cloud 并发设置触发账号并发限制。
        lock_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
        lock = locks.setdefault(lock_id, asyncio.Lock())

        async def generate():
            async with lock:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=seconds)) as session:
                    for index in range(count):
                        body = {**payload, "parameters": dict(p)}
                        # 固定种子首张精确复现，后续 +1；随机种子每张独立。
                        requested_seed = options.get("seed")
                        if requested_seed is None:
                            requested_seed = self.config.get("nai_seed", -1)
                        seed = p["seed"] if index == 0 else (
                            secrets.randbits(32) if str(requested_seed).strip() == "-1"
                            else (p["seed"] + index) % (2 ** 32)
                        )
                        body["parameters"]["seed"] = seed
                        if source_images:
                            body["parameters"]["extra_noise_seed"] = seed
                        kwargs = {"json": body, "headers": headers, "allow_redirects": False}
                        if proxy:
                            kwargs["proxy"] = proxy
                        async with session.post(url, **kwargs) as resp:
                            raw = await self._read_limited(resp, self._max_bytes("max_output_size_mb", 100) * 2 + 1024 * 1024, "NAI 绘图响应")
                            if resp.status not in {200, 201}:
                                message = ""
                                try:
                                    error = json.loads(raw.decode("utf-8"))
                                    if isinstance(error, dict):
                                        message = str(error.get("message") or error.get("error") or "")[:400]
                                except (UnicodeDecodeError, ValueError):
                                    pass
                                hints = {401: "Token 无效或已过期", 402: "订阅或 Anlas 额度不足", 403: "账号没有该模型或绘图权限", 429: "账号并发或频率受限，请稍后再试"}
                                detail = message.replace(key, "[已隐藏]") or hints.get(resp.status, "请检查服务地址、模型与账号状态")
                                raise ComfyUIError(f"NAI 绘图失败（HTTP {resp.status}）：{detail}")
                            image, extension = self._decode_nai_image(raw)
                            results.append((image, f"nai_{seed}_{index}.{extension}"))
            return results

        try:
            return await asyncio.wait_for(generate(), timeout=seconds)
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, asyncio.TimeoutError):
                message = "NAI 绘图超时，请减少张数或调整 openai_image_timeout。"
            elif isinstance(exc, ComfyUIError):
                message = str(exc)
            else:
                message = f"NAI 连接或图片解析失败（{type(exc).__name__}）。"
            if results:
                message += f" 已完成 {len(results)}/{count} 张，将发送已完成图片。"
            error = ComfyUIError(message.replace(key, "[已隐藏]"))
            error.partial_results = results
            raise error from None
