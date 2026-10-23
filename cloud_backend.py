"""云端绘图：接口方案、OpenAI 兼容图片接口与 Sub2API Antigravity/Gemini。"""
import asyncio
import base64
import json
import math
from urllib.parse import quote, urlsplit, urlunsplit

import aiohttp

from astrbot.api import logger

from .errors import ComfyUIError, GeminiTextOnlyError


class CloudBackendMixin:
    """云端绘图：接口方案、OpenAI 兼容图片接口与 Sub2API Antigravity/Gemini。混入 ComfyUIDrawPlugin 使用，依赖主类的配置读取等通用方法。"""

    DEFAULT_CLOUD_ART_STYLE = "日系二次元动漫插画，干净线稿，赛璐璐上色，不要真人照片或写实风格"

    def _with_default_art_style(self, prompt):
        """追加默认画风；配置中显式留空时不追加。用户描述里写明的画风优先。"""
        if "cloud_default_art_style" in self.config:
            style = str(self.config.get("cloud_default_art_style") or "").strip()
        else:
            style = self.DEFAULT_CLOUD_ART_STYLE
        if not style:
            return prompt
        return f"{prompt}\n画风要求：{style}（如果上面的描述明确要求了其他画风，以描述为准）"

    def _apply_cloud_prompt_preset(self, prompt: str, requested: str = None):
        """应用云绘图提示词预设，返回（扩展后的提示词、规范名称、建议尺寸）。"""
        key = str(requested or "").strip().lower()
        if not key:
            return str(prompt or "").strip(), "", None
        canonical = self.CLOUD_PROMPT_PRESET_ALIASES.get(key, key)
        item = self.CLOUD_PROMPT_PRESETS.get(canonical)
        if not item:
            available = "、".join(self.CLOUD_PROMPT_PRESETS.keys())
            raise ComfyUIError(f"未知云绘图预设「{requested}」。可选：{available}")
        expanded = str(item["prompt"]).replace("{subject}", str(prompt or "").strip())
        return expanded, canonical, item.get("size")

    # ------------------------------------------------------------------ #
    # 云绘图方案：cloud_profiles 中的命名方案可覆盖顶层的地址 / Key / 模型，
    # active_cloud_profile 为空时使用顶层配置（即「默认」方案）。
    # ------------------------------------------------------------------ #
    CLOUD_PROVIDERS = ("auto", "openai-compatible", "sub2api-antigravity")
    DEFAULT_CLOUD_PROFILE = "默认"
    # 每种接口类型的专属 Key；留空时沿用通用的 openai_image_api_key。
    CLOUD_PROVIDER_KEY_FIELDS = {
        "openai-compatible": "openai_compatible_api_key",
        "sub2api-antigravity": "sub2api_antigravity_api_key",
    }

    @classmethod
    def _normalize_cloud_provider(cls, value, fallback="auto"):
        provider = str(value or "").strip().lower()
        return provider if provider in cls.CLOUD_PROVIDERS else fallback

    def _cloud_profiles(self) -> dict:
        """返回 {方案名: 配置项}；跳过无名称、重名或与「默认」同名的条目。"""
        result = {}
        for item in self.config.get("cloud_profiles", []) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            if not name or name == self.DEFAULT_CLOUD_PROFILE or name in result:
                continue
            result[name] = item
        return result

    def _active_cloud_profile(self):
        """返回 (方案名, 方案配置或 None)；找不到已选方案时安全回退到「默认」。"""
        name = str(self.config.get("active_cloud_profile", "") or "").strip()
        if not name or name == self.DEFAULT_CLOUD_PROFILE:
            return self.DEFAULT_CLOUD_PROFILE, None
        profile = self._cloud_profiles().get(name)
        if profile is None:
            logger.warning(f"[comfyui_draw] 云绘图方案「{name}」不存在，已回退到默认配置。")
            return self.DEFAULT_CLOUD_PROFILE, None
        return name, profile

    @staticmethod
    def _default_cloud_model(provider):
        return "gemini-3.1-flash-image" if provider == "sub2api-antigravity" else "gpt-image-2"

    def _global_model_key(self, provider):
        return "gemini_image_model" if provider == "sub2api-antigravity" else "openai_image_model"

    def _top_level_api_key(self, provider):
        """返回 (配置项名, Key)：优先该接口类型的专属 Key，留空再用通用 Key。"""
        field = self.CLOUD_PROVIDER_KEY_FIELDS.get(provider)
        if field:
            value = str(self.config.get(field, "") or "").strip()
            if value:
                return field, value
        return field or "openai_image_api_key", str(
            self.config.get("openai_image_api_key", "") or ""
        ).strip()

    def _cloud_connection(self, name=None):
        """解析某个方案（默认为当前方案）实际使用的接口类型、地址、Key 和模型。

        方案里留空的地址 / 模型沿用顶层配置，方便同一站点只换接口类型或模型。
        Key 按接口类型取顶层专属 Key；方案填了自己的地址却没填 Key 时不借用顶层 Key，
        避免把一个站点的 Key 发给另一个站点。
        """
        if name is None:
            name, profile = self._active_cloud_profile()
        elif name == self.DEFAULT_CLOUD_PROFILE:
            profile = None
        else:
            profile = self._cloud_profiles().get(name)
        profile = profile or {}
        top_provider = self._normalize_cloud_provider(self.config.get("openai_image_provider", "auto"))
        provider = self._normalize_cloud_provider(profile.get("provider"), top_provider)

        def pick(key, config_key):
            value = str(profile.get(key, "") or "").strip()
            return value or str(self.config.get(config_key, "") or "").strip()

        model = (
            str(profile.get("model", "") or "").strip()
            or str(self.config.get(self._global_model_key(provider), "") or "").strip()
            or self._default_cloud_model(provider)
        )
        key_field, api_key = self._top_level_api_key(provider)
        profile_key = str(profile.get("api_key", "") or "").strip()
        if profile_key:
            api_key = profile_key
        elif str(profile.get("base_url", "") or "").strip():
            api_key = ""
        return {
            "name": name,
            "provider": provider,
            "base_url": pick("base_url", "openai_image_base_url"),
            "api_key": api_key,
            "api_key_field": key_field,
            "model": model,
        }

    def _openai_image_provider(self) -> str:
        return self._cloud_connection()["provider"]

    def _cloud_image_model(self) -> str:
        return self._cloud_connection()["model"]

    @staticmethod
    def _valid_model_name(value):
        text = str(value or "").strip()
        if not text or len(text) > 200:
            return False
        return all((ch.isascii() and ch.isalnum()) or ch in "._-:/@" for ch in text)

    def _cloud_profile_hint(self, conn):
        """缺少地址 / Key 时，提示可以在当前方案里补填。"""
        if conn["name"] == self.DEFAULT_CLOUD_PROFILE:
            return ""
        return f"（或在云绘图方案「{conn['name']}」中填写）"

    def _set_cloud_model(self, profile_name, model):
        """把模型写入指定方案；「默认」方案写回对应接口类型的顶层模型配置。"""
        if profile_name == self.DEFAULT_CLOUD_PROFILE:
            provider = self._cloud_connection(profile_name)["provider"]
            self.config[self._global_model_key(provider)] = model
        else:
            self._cloud_profiles()[profile_name]["model"] = model

    @staticmethod
    def _antigravity_image_url(base: str, model: str) -> str:
        """保留反向代理前缀，并归一化根地址、版本路径或完整 Gemini 接口。"""
        parsed = urlsplit(str(base or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ComfyUIError("Sub2API 地址必须是 http:// 或 https:// 开头的服务地址。")
        if parsed.username or parsed.password:
            raise ComfyUIError("Sub2API 地址不能包含用户名密码，请使用 API Key 配置。")
        path = parsed.path.rstrip("/")
        if "/models/" in path:
            path = path.rsplit("/models/", 1)[0]
        for suffix in (
            "/antigravity/v1beta", "/antigravity/v1", "/antigravity",
            "/v1/images/generations", "/v1/images/edits",
            "/images/generations", "/images/edits", "/v1beta", "/v1",
        ):
            if path.endswith(suffix):
                path = path[:-len(suffix)]
                break
        model = str(model or "").strip().removeprefix("models/")
        if not model:
            raise ComfyUIError("请填写 Sub2API 分组允许使用的 Gemini 绘图模型名。")
        path += f"/antigravity/v1beta/models/{quote(model, safe='')}:generateContent"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

    def _gemini_image_config(self, size=None, quality=None):
        """将命令宽高转换成受支持的比例；分辨率档位单独指定。"""
        resolution = str(self.config.get("gemini_image_resolution", "1K") or "1K").strip().upper()
        if quality:
            requested = str(quality).strip().upper()
            if requested not in {"1K", "2K", "4K"}:
                raise ComfyUIError(
                    "Antigravity 的 --quality 只接受 1K、2K、4K；"
                    "请清空原 GPT-Image 默认质量，改用 gemini_image_resolution。"
                )
            resolution = requested
        if resolution not in {"1K", "2K", "4K"}:
            raise ComfyUIError("Gemini 绘图分辨率档位只能是 1K、2K 或 4K。")
        config = {"imageSize": resolution}
        requested_size = str(size or self.config.get("openai_image_size", "") or "").strip()
        if not requested_size or requested_size.lower() == "auto":
            return config
        normalized = requested_size.lower()
        for sep in ("*", "×", "✕", "✖", ":"):
            normalized = normalized.replace(sep, "x")
        try:
            width, height = (int(v.strip()) for v in normalized.split("x"))
        except (TypeError, ValueError):
            raise ComfyUIError("Gemini 尺寸应为 宽x高 或 比例，例如 1536x1024、16:9。")
        if width <= 0 or height <= 0:
            raise ComfyUIError("图片宽高必须大于 0。")
        ratios = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")
        # 对数距离对横竖比对称，原图分辨率不影响选定的比例。
        target = math.log(width) - math.log(height)
        config["aspectRatio"] = min(
            ratios,
            key=lambda value: abs(target - math.log(int(value.split(":")[0]) / int(value.split(":")[1]))),
        )
        return config

    def _gemini_aspect_mode(self):
        mode = str(self.config.get("gemini_image_aspect_mode", "auto") or "auto").strip().lower()
        if mode not in {"auto", "strict", "prompt"}:
            raise ComfyUIError("Gemini 比例兼容模式只能是 auto、strict 或 prompt。")
        return mode

    GEMINI_IMAGE_OUTPUT_HINT = (
        "Output requirement: generate the image described above and return it as an image. "
        "Do not answer with only text, a description, or a placeholder."
    )
    GEMINI_EDIT_OUTPUT_HINT = (
        "Output requirement: apply the request above to the provided image(s) and return the "
        "resulting image. Do not answer with only text or a description."
    )

    @staticmethod
    def _gemini_require_image(body):
        """在不改动原请求的前提下追加更强的出图要求，供“只回文字”时重试一次。"""
        contents = list(body["contents"])
        content = dict(contents[0])
        content["parts"] = [*content["parts"], {
            "text": "IMPORTANT: the previous reply contained only text. This is an image generation "
                    "request. Output the image itself now; at most one short caption is allowed."
        }]
        contents[0] = content
        return {**body, "contents": contents}

    @staticmethod
    def _gemini_without_aspect_ratio(body):
        """只去掉被拒绝的比例字段，原图、提示词、清晰度均保留。"""
        generation = dict(body["generationConfig"])
        image_config = dict(generation["imageConfig"])
        ratio = image_config.pop("aspectRatio", None)
        generation["imageConfig"] = image_config
        revised = {**body, "generationConfig": generation}
        if ratio:
            contents = list(body["contents"])
            content = dict(contents[0])
            content["parts"] = [*content["parts"], {
                "text": f"Composition preference: use a {ratio} width-to-height aspect ratio if possible; follow the model's available image output capabilities."
            }]
            contents[0] = content
            revised["contents"] = contents
        return revised

    def _decode_gemini_image_results(self, data):
        """读取最终 inlineData 图片，跳过思考过程中的预览图。"""
        if not isinstance(data, dict):
            raise ComfyUIError("Antigravity 返回了无效的 Gemini 响应。")
        if isinstance(data.get("response"), dict):
            data = data["response"]
        if data.get("error"):
            raise ComfyUIError(self._format_openai_error(data, 200))
        results, details, texts, finish_reasons = [], [], [], []
        candidates = data.get("candidates") or []
        if not isinstance(candidates, list):
            raise ComfyUIError("Antigravity 返回的 candidates 格式不正确。")
        extensions = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}
        max_bytes = self._max_bytes("max_output_size_mb", 100)
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("finishReason"):
                details.append(str(candidate["finishReason"]))
                finish_reasons.append(str(candidate["finishReason"]).upper())
            content = candidate.get("content") or {}
            parts = content.get("parts", []) if isinstance(content, dict) else []
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not isinstance(part, dict) or part.get("thought"):
                    continue
                if part.get("text"):
                    details.append(str(part["text"])[:300])
                    texts.append(str(part["text"]))
                inline = part.get("inlineData") or part.get("inline_data")
                if not isinstance(inline, dict):
                    continue
                mime = str(inline.get("mimeType") or inline.get("mime_type") or "").lower()
                if mime not in extensions:
                    continue
                encoded = inline.get("data")
                if not isinstance(encoded, str) or not encoded.strip():
                    raise ComfyUIError("Antigravity 返回的图片数据为空。")
                if len(encoded) > ((max_bytes + 2) // 3) * 4:
                    raise ComfyUIError("云端返回的图片超过体积上限。")
                try:
                    raw = base64.b64decode(encoded, validate=True)
                except (ValueError, base64.binascii.Error):
                    raise ComfyUIError("Antigravity 返回的图片 Base64 数据无效。")
                if not raw or len(raw) > max_bytes:
                    raise ComfyUIError("云端返回的图片为空或超过体积上限。")
                results.append((raw, f"gemini_{len(results)}.{extensions[mime]}"))
        if not results:
            feedback = data.get("promptFeedback") or {}
            blocked = isinstance(feedback, dict) and feedback.get("blockReason")
            if blocked:
                details.insert(0, str(feedback["blockReason"]))
            if texts and not blocked and all(r in {"STOP", "FINISH_REASON_UNSPECIFIED"} for r in finish_reasons):
                # 正常结束却只有文字：模型把请求当成了聊天，可再明确要求一次出图。
                excerpt = " ".join(" ".join(texts).split())
                if len(excerpt) > 60:
                    excerpt = excerpt[:60] + "…"
                raise GeminiTextOnlyError(
                    f"Antigravity 只回复了文字，没有生成图片（模型回复：{excerpt}）。"
                    "可以把画面写得更具体，比如人物外貌、动作、场景和画风，再试一次。"
                )
            reason = "；".join(details)[:400] or "请检查绘图模型名、分组绘图权限和上游图片额度。"
            raise ComfyUIError(
                f"Antigravity 没有返回最终图片：{reason} "
                "请确认站点实际映射到支持图片输出的模型，而非仅支持文字或看图的模型。"
            )
        return results

    async def _run_antigravity_image(self, prompt, size=None, n=1, source_images=None, quality=None, style=None,
                                     conn=None):
        """原生绘图；仅对明确的比例参数 400 拒绝做一次兼容回退。"""
        conn = conn or self._cloud_connection()
        base, key = conn["base_url"], conn["api_key"]
        if not base or not key:
            raise ComfyUIError(
                f"请先填写 Sub2API 的 openai_image_base_url 和 {conn['api_key_field']}"
                + self._cloud_profile_hint(conn) + "。"
            )
        url = self._antigravity_image_url(base, conn["model"])
        image_config = self._gemini_image_config(size, quality)
        aspect_mode = self._gemini_aspect_mode()
        parts = []
        for index, raw in enumerate(source_images or []):
            if not raw or len(raw) > self._max_bytes("max_input_size_mb", 20):
                raise ComfyUIError("原图为空或超过输入图片体积上限。")
            _, mime = self._image_upload_meta(raw, index)
            if mime == "image/gif":
                raise ComfyUIError("Gemini 图片编辑请使用 PNG、JPEG 或 WebP 原图，暂不支持 GIF。")
            parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(raw).decode("ascii")}})
        text = str(prompt)
        if style:
            text += f"\nVisual style: {str(style).strip()}"
        parts.append({"text": text})
        # 单独追加输出要求，避免短提示词（如只有角色名）被模型当成聊天而只回文字。
        parts.append({"text": self.GEMINI_EDIT_OUTPUT_HINT if source_images else self.GEMINI_IMAGE_OUTPUT_HINT})
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": image_config},
        }
        disabled_urls = getattr(self, "_gemini_aspect_disabled_urls", None)
        if disabled_urls is None:
            disabled_urls = self._gemini_aspect_disabled_urls = set()
        if aspect_mode == "prompt" or (aspect_mode == "auto" and url in disabled_urls):
            body = self._gemini_without_aspect_ratio(body)
        count = self._clamp_batch(int(n))
        seconds = self._config_int("openai_image_timeout", 360, 1, 3600)
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        text_only_retry = bool(self.config.get("gemini_text_only_retry", True))
        results = []

        async def generate():
            nonlocal body
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=seconds)) as session:
                for index in range(count):
                    request = body
                    retry_left = text_only_retry
                    while True:
                        async with session.post(url, json=request, headers=headers, allow_redirects=False) as resp:
                            raw = await self._read_limited(
                                resp, self._max_bytes("max_output_size_mb", 100) * 2 + 1024 * 1024,
                                "Antigravity 绘图响应",
                            )
                            try:
                                payload = json.loads(raw.decode("utf-8"))
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                raise ComfyUIError(f"Antigravity 接口返回非 JSON（HTTP {resp.status}），请检查站点地址或网关超时。")
                            if resp.status != 200:
                                message = self._format_openai_error(payload, resp.status)
                                aspect_rejected = (
                                    resp.status == 400
                                    and "aspect ratio is not enabled for this model" in message.lower()
                                )
                                if (aspect_rejected and aspect_mode == "auto"
                                        and "aspectRatio" in body["generationConfig"]["imageConfig"]):
                                    # 只针对已明确拒绝的字段回退一次；不重试超时、限流或生成失败。
                                    body = self._gemini_without_aspect_ratio(body)
                                    request = body
                                    disabled_urls.add(url)
                                    logger.warning("[comfyui_draw] 模型拒绝 aspectRatio，已省略该字段并将比例转为构图提示；本次加载期间记住此模型限制。")
                                    continue
                                if aspect_rejected:
                                    message += "；可将 gemini_image_aspect_mode 设为 prompt。若仍报错，请检查站点的模型映射。"
                                if resp.status == 403:
                                    message += "；请检查 Key 所属分组的绘图权限、模型白名单和额度。"
                                raise ComfyUIError(message)
                            try:
                                images = self._decode_gemini_image_results(payload)
                            except GeminiTextOnlyError as e:
                                if not retry_left:
                                    suffix = "（已自动要求重新出图一次，仍只有文字。）" if text_only_retry else ""
                                    raise ComfyUIError(str(e) + suffix) from None
                                # 只对“正常结束但没出图”重试一次；拦截、超时、限流等仍不重试。
                                retry_left = False
                                request = self._gemini_require_image(body)
                                logger.warning("[comfyui_draw] Gemini 只回复了文字，已明确要求输出图片并重试一次。")
                                continue
                            image, filename = images[0]
                            results.append((image, f"gemini_{index}.{filename.rsplit('.', 1)[-1]}"))
                            break
            return results

        try:
            # 所有张数共享同一超时预算，避免批量任务占用任务槽过久。
            return await asyncio.wait_for(generate(), timeout=seconds)
        except Exception as e:  # noqa: BLE001
            if isinstance(e, asyncio.TimeoutError):
                message = (
                    f"Antigravity 绘图超时（超过 {seconds} 秒，配置项 openai_image_timeout），"
                    "请减少张数或提高超时时间。"
                )
            elif isinstance(e, ComfyUIError):
                message = str(e)
            else:
                # 避免把含有请求头/密钥的底层异常直接发到聊天中。
                message = f"无法连接 Antigravity 绘图接口（{type(e).__name__}）。"
            if results:
                message += f" 已完成 {len(results)}/{count} 张，以下发送已生成图片；未自动重试。"
            error = ComfyUIError(message)
            error.partial_results = results
            raise error from None

    def _openai_image_urls(self, base: str, provider: str = None) -> list[str]:
        """按接口类型生成候选地址，并避免重复拼接接口路径。"""
        base = str(base or "").strip().rstrip("/")
        if base.endswith("/images/generations"):
            return [base]

        direct_url = base + "/images/generations"
        if base.endswith("/v1"):
            return [direct_url]

        v1_url = base + "/v1/images/generations"
        if (provider or self._openai_image_provider()) == "auto":
            return [direct_url, v1_url]
        return [direct_url]

    def _openai_image_edit_urls(self, base: str, provider: str = None) -> list[str]:
        """生成 /images/edits 候选地址，兼容根地址、/v1 和完整接口地址。"""
        base = str(base or "").strip().rstrip("/")
        if base.endswith("/images/edits"):
            return [base]
        if base.endswith("/images/generations"):
            return [base[: -len("/images/generations")] + "/images/edits"]

        direct_url = base + "/images/edits"
        if base.endswith("/v1"):
            return [direct_url]

        v1_url = base + "/v1/images/edits"
        if (provider or self._openai_image_provider()) == "auto":
            return [direct_url, v1_url]
        return [direct_url]

    def _openai_image_response_format(self) -> str:
        value = str(
            self.config.get("openai_image_response_format", "") or ""
        ).strip().lower()
        if value and value not in {"url", "b64_json"}:
            raise ComfyUIError(
                "云端绘图 response_format 只能是 url 或 b64_json。"
            )
        return value

    async def _run_openai_image(self, prompt: str, size: str = None, n: int = 1,
                                quality: str = None, style: str = None, conn: dict = None):
        """调用 OpenAI 兼容的 /images/generations 接口，返回 list[(bytes, filename)]。
        conn 为本次固定的接口方案，省略时取当前方案。失败抛出 ComfyUIError / asyncio.TimeoutError。"""
        conn = conn or self._cloud_connection()
        if conn["provider"] == "sub2api-antigravity":
            return await self._run_antigravity_image(prompt, size, n, quality=quality, style=style, conn=conn)
        base, key, model = conn["base_url"].rstrip("/"), conn["api_key"], conn["model"]
        if not base:
            raise ComfyUIError(
                "未配置云端绘图地址，请在插件配置里填写 openai_image_base_url"
                + self._cloud_profile_hint(conn) + "。"
            )
        if not key:
            raise ComfyUIError(
                f"未配置云端绘图 API Key，请在插件配置里填写 {conn['api_key_field']}"
                + self._cloud_profile_hint(conn) + "。"
            )

        urls = self._openai_image_urls(base, conn["provider"])
        body = {"model": model, "prompt": prompt, "n": max(1, int(n))}
        sz = size or str(self.config.get("openai_image_size", "") or "").strip()
        if sz:
            body["size"] = sz
        if quality:
            body["quality"] = str(quality).strip()
        if style:
            body["style"] = str(style).strip()
        rf = self._openai_image_response_format()
        if rf:
            body["response_format"] = rf
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(
            total=self._config_int("openai_image_timeout", 360, 1, 3600)
        )

        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._post_cloud_json(
                session,
                urls,
                lambda: {"json": body, "headers": headers},
                self._cloud_response_limit(n),
                "云端绘图",
            )
            return await self._decode_openai_image_results(
                session, data, prefix="gptimage", label="云端绘图"
            )

    async def _run_openai_image_edit(
        self,
        prompt: str,
        source_images: list,
        size: str = None,
        n: int = 1,
        quality: str = None,
        conn: dict = None,
    ):
        """调用 OpenAI 兼容的 /images/edits，以 multipart 上传一张或多张原图。"""
        conn = conn or self._cloud_connection()
        if conn["provider"] == "sub2api-antigravity":
            if not source_images:
                raise ComfyUIError("图片编辑需要至少一张原图。")
            return await self._run_antigravity_image(prompt, size, n, source_images, quality=quality, conn=conn)
        base, key, model = conn["base_url"].rstrip("/"), conn["api_key"], conn["model"]
        if not base:
            raise ComfyUIError(
                "未配置云端绘图地址，请在插件配置里填写 openai_image_base_url"
                + self._cloud_profile_hint(conn) + "。"
            )
        if not key:
            raise ComfyUIError(
                f"未配置云端绘图 API Key，请在插件配置里填写 {conn['api_key_field']}"
                + self._cloud_profile_hint(conn) + "。"
            )
        if not source_images:
            raise ComfyUIError("图片编辑需要至少一张原图。")

        urls = self._openai_image_edit_urls(base, conn["provider"])
        count = max(1, min(4, int(n)))
        sz = size or str(self.config.get("openai_image_size", "") or "").strip()
        rf = self._openai_image_response_format()
        headers = {"Authorization": f"Bearer {key}"}
        timeout = aiohttp.ClientTimeout(
            total=self._config_int("openai_image_timeout", 360, 1, 3600)
        )

        def build_form():
            # FormData 每次请求后都会被消费；自动回退 /v1 时必须重新创建。
            form = aiohttp.FormData()
            form.add_field("model", model)
            form.add_field("prompt", str(prompt))
            form.add_field("n", str(count))
            if sz:
                form.add_field("size", sz)
            if quality:
                form.add_field("quality", str(quality).strip())
            if rf:
                form.add_field("response_format", rf)
            for index, data in enumerate(source_images):
                filename, content_type = self._image_upload_meta(data, index)
                form.add_field(
                    "image",
                    data,
                    filename=filename,
                    content_type=content_type,
                )
            return form

        async with aiohttp.ClientSession(timeout=timeout) as session:
            data = await self._post_cloud_json(
                session,
                urls,
                lambda: {"data": build_form(), "headers": headers},
                self._cloud_response_limit(count),
                "云端图片编辑",
            )
            return await self._decode_openai_image_results(
                session, data, prefix="gptedit", label="云端图片编辑"
            )

    def _cloud_response_limit(self, count):
        """一次响应可能包含 count 张 Base64 图片，按单图上限的两倍预留并加 1 MB 余量。"""
        return (
            self._max_bytes("max_output_size_mb", 100) * max(1, int(count)) * 2
            + 1024 * 1024
        )

    async def _post_cloud_json(self, session, urls, request_kwargs, response_limit, label):
        """依次请求候选地址并返回 JSON；仅在 404/405 且还有候选地址时换下一个。

        request_kwargs 是无参函数，每次请求都重新生成参数（FormData 只能被消费一次）。
        """
        status, data = 0, None
        for attempt, url in enumerate(urls):
            try:
                async with session.post(url, **request_kwargs()) as resp:
                    status = resp.status
                    # 先判断是否回退：根地址的 404 常是 HTML 页面，不能先当 JSON 解析，
                    # 否则“自动”模式永远走不到 /v1 路径。
                    if status in {404, 405} and attempt + 1 < len(urls):
                        continue
                    raw = await self._read_limited(resp, response_limit, f"{label}响应")
            except (asyncio.TimeoutError, ComfyUIError):
                raise
            except Exception as e:  # noqa: BLE001
                raise ComfyUIError(f"无法连接{label}接口（{url}）：{e}")
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                if status != 200:
                    raise ComfyUIError(
                        f"{label}失败（HTTP {status}）：接口返回的不是 JSON，请检查地址是否正确。"
                    )
                raise ComfyUIError(f"{label}接口返回的不是有效 JSON：{e}")
            break
        if status != 200:
            raise ComfyUIError(self._format_openai_error(data, status))
        return data

    async def _decode_openai_image_results(self, session, data, prefix="gptedit", label="云端图片编辑"):
        """解析图片接口共同的 b64_json / url 返回格式。"""
        items = data.get("data") if isinstance(data, dict) else None
        if not items or not isinstance(items, list):
            raise ComfyUIError(f"{label}没有返回图片数据。")
        results = []
        max_bytes = self._max_bytes("max_output_size_mb", 100)
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            encoded = item.get("b64_json")
            if encoded:
                try:
                    encoded = str(encoded).strip()
                    if encoded.startswith("data:") and ";base64," in encoded:
                        encoded = encoded.split(";base64,", 1)[1]
                    if len(encoded) > (max_bytes * 4 // 3) + 16:
                        raise ComfyUIError("云端返回的图片超过体积上限。")
                    raw = base64.b64decode(encoded)
                except Exception as e:  # noqa: BLE001
                    if isinstance(e, ComfyUIError):
                        raise
                    raise ComfyUIError(f"图片解码失败：{e}")
                if len(raw) > max_bytes:
                    raise ComfyUIError("云端返回的图片超过体积上限。")
            elif item.get("url"):
                raw = await self._download_bytes(session, item["url"])
            else:
                continue
            # 按文件头确定扩展名，JPEG/WebP 结果不再一律标成 .png。
            ext = self._image_upload_meta(raw)[0].rsplit(".", 1)[-1]
            results.append((raw, f"{prefix}_{index}.{ext}"))
        if not results:
            raise ComfyUIError(f"{label}返回了空的图片数据。")
        return results

    async def _download_bytes(self, session, url):
        async with session.get(url) as r:
            if r.status != 200:
                raise ComfyUIError(f"下载生成的图片失败：HTTP {r.status}")
            return await self._read_limited(
                r,
                self._max_bytes("max_output_size_mb", 100),
                "生成图片",
            )

    def _format_openai_error(self, data, status):
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict) and err.get("message"):
                return f"云端绘图失败（HTTP {status}）：{err['message']}"
            if err:
                return f"云端绘图失败（HTTP {status}）：{err}"
            if data.get("message"):
                return f"云端绘图失败（HTTP {status}）：{data['message']}"
            detail = data.get("detail")
            if isinstance(detail, list):
                messages = []
                for item in detail:
                    if isinstance(item, dict):
                        messages.append(str(item.get("msg") or item))
                    elif item:
                        messages.append(str(item))
                if messages:
                    return f"云端绘图失败（HTTP {status}）：{'；'.join(messages)}"
            elif detail:
                return f"云端绘图失败（HTTP {status}）：{detail}"
        return f"云端绘图失败（HTTP {status}）：{str(data)[:300]}"
