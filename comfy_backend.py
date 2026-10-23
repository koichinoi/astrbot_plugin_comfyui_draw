"""本地 ComfyUI：提交工作流、取回结果、工作流加载、参数与 LoRA 注入。"""
import asyncio
import json
import math
import os
import uuid

import aiohttp

from astrbot.api import logger

from .errors import ComfyUIError
from .templates import DEFAULT_WORKFLOW


class ComfyBackendMixin:
    """本地 ComfyUI：提交工作流、取回结果、工作流加载、参数与 LoRA 注入。混入 ComfyUIDrawPlugin 使用，依赖主类的配置读取等通用方法。"""

    # ------------------------------------------------------------------ #
    # ComfyUI 交互
    # ------------------------------------------------------------------ #
    async def _run_comfyui(self, workflow: dict):
        """提交工作流到 ComfyUI，等待完成并下载所有输出图片。

        返回 list[(bytes, filename)]。失败时抛出 ComfyUIError / asyncio.TimeoutError。
        """
        timeout = self._config_int("timeout", 300, 1, 7200)
        # 超时覆盖提交、WebSocket 等待、history 轮询和文件下载的完整链路。
        return await asyncio.wait_for(
            self._run_comfyui_inner(workflow, timeout),
            timeout=timeout,
        )

    async def _run_comfyui_inner(self, workflow: dict, timeout: int):
        http_base, ws_base = self._split_url(self.config.get("comfyui_base_url", "127.0.0.1:8188"))
        client_id = uuid.uuid4().hex
        sess_timeout = aiohttp.ClientTimeout(
            total=timeout,
            sock_connect=min(15, timeout),
            sock_read=timeout,
        )

        async with aiohttp.ClientSession(timeout=sess_timeout) as session:
            # 1) 先连 WebSocket，避免任务在我们开始监听之前就已经跑完导致漏掉完成信号
            ws_url = f"{ws_base}/ws?clientId={client_id}"
            try:
                ws = await session.ws_connect(
                    ws_url, heartbeat=30, timeout=min(15, timeout)
                )
            except Exception as e:  # noqa: BLE001
                raise ComfyUIError(
                    f"无法连接 ComfyUI（{ws_url}）：{e}。请检查地址是否正确、ComfyUI 是否已启动。"
                )

            try:
                # 2) 提交工作流
                try:
                    async with session.post(
                        f"{http_base}/prompt",
                        json={"prompt": workflow, "client_id": client_id},
                    ) as resp:
                        try:
                            body = await resp.json(content_type=None)
                        except ValueError:
                            # 反向代理或 ComfyUI 崩溃时可能返回 HTML/空响应。
                            raise ComfyUIError(
                                f"ComfyUI 返回了无法解析的响应（HTTP {resp.status}），"
                                "请检查地址或查看 ComfyUI 控制台日志。"
                            )
                        if resp.status != 200:
                            raise ComfyUIError(self._format_prompt_error(body))
                        prompt_id = body.get("prompt_id")
                        node_errors = body.get("node_errors") or {}
                        if not prompt_id:
                            raise ComfyUIError(f"提交工作流失败：{body}")
                        if node_errors:
                            raise ComfyUIError(self._format_node_errors(node_errors) or "工作流校验失败。")
                except aiohttp.ClientError as e:
                    raise ComfyUIError(f"提交工作流到 ComfyUI 失败：{e}")

                # 3) 等待执行完成；外层 wait_for 负责完整链路的总超时。
                await self._wait_done(ws, prompt_id)
            finally:
                try:
                    await ws.close()
                except Exception:  # noqa: BLE001
                    pass

            # 4) 从 /history 拿输出（带短暂轮询，应对漏掉的 ws 信号）
            entry = await self._get_history(
                session, http_base, prompt_id, retries=max(20, timeout)
            )
            # 5) 下载图片
            return await self._collect_images(session, http_base, entry)

    async def _wait_done(self, ws, prompt_id: str):
        """监听 WebSocket，直到对应 prompt_id 执行完成或出错。"""
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    m = json.loads(msg.data)
                except Exception:  # noqa: BLE001
                    continue
                mtype = m.get("type")
                data = m.get("data") or {}
                if mtype == "executing":
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        return  # 执行完成
                elif mtype == "execution_error" and data.get("prompt_id") == prompt_id:
                    raise ComfyUIError(self._format_exec_error(data))
                elif mtype == "execution_interrupted" and data.get("prompt_id") == prompt_id:
                    raise ComfyUIError("ComfyUI 任务被中断。")
            elif msg.type == aiohttp.WSMsgType.BINARY:
                continue  # 预览图，忽略
            elif msg.type in (
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.ERROR,
            ):
                return
        return

    async def _get_history(self, session, http_base, prompt_id, retries=20, delay=1.0):
        last = None
        for _ in range(retries):
            try:
                async with session.get(f"{http_base}/history/{prompt_id}") as resp:
                    if resp.status == 200:
                        hist = await resp.json(content_type=None)
                        entry = hist.get(prompt_id) if isinstance(hist, dict) else None
                        if entry:
                            status = entry.get("status") or {}
                            if entry.get("outputs"):
                                return entry
                            if status.get("status_str") == "error":
                                raise ComfyUIError("工作流执行出错（请在 ComfyUI 控制台查看详细日志）。")
                            if status.get("completed") is True:
                                return entry
                            last = entry
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(delay)
        if last is not None:
            return last
        raise ComfyUIError(
            "生成超时或未取到结果。请检查 ComfyUI 运行状态、模型是否存在，或增大超时时间。"
        )

    async def _collect_images(self, session, http_base, entry):
        outputs = entry.get("outputs") or {}
        collected = []
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            for key in ("images", "gifs", "videos", "video"):
                for item in node_output.get(key) or []:
                    if isinstance(item, dict) and item.get("filename"):
                        collected.append(item)
        # 优先取最终输出（type == output），没有再退而求其次
        final = [i for i in collected if i.get("type") == "output"]
        chosen = final if final else collected
        results = []
        for item in chosen:
            data = await self._view(session, http_base, item)
            if data:
                results.append((data, item.get("filename", "image.png")))
        if not results:
            raise ComfyUIError(
                "任务完成了，但没有取到图片。请确认工作流里包含 SaveImage（或同类输出）节点。"
            )
        return results

    async def _view(self, session, http_base, item):
        params = {
            "filename": item.get("filename", ""),
            "subfolder": item.get("subfolder", ""),
            "type": item.get("type", "output"),
        }
        try:
            async with session.get(f"{http_base}/view", params=params) as resp:
                if resp.status == 200:
                    return await self._read_limited(
                        resp,
                        self._max_bytes("max_output_size_mb", 100),
                        "ComfyUI 输出文件",
                    )
        except aiohttp.ClientError:
            return None
        return None

    # ------------------------------------------------------------------ #
    # 工作流 / 占位符
    # ------------------------------------------------------------------ #
    def _extra_workflows(self) -> dict:
        result = {}
        for item in self.config.get("extra_workflows", []) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            wf = item.get("workflow") or ""
            if name and str(wf).strip():
                result[name] = wf
        return result

    def _dir_workflows(self) -> dict:
        """扫描配置的 workflow_dir 目录，返回 {名称: 文件绝对路径}；名称取文件名（去扩展名）。"""
        result = {}
        d = str(self.config.get("workflow_dir", "") or "").strip()
        if not d:
            return result
        try:
            if not os.path.isdir(d):
                logger.warning(f"[comfyui_draw] 工作流目录不存在或无法访问：{d}")
                return result
            for fn in sorted(os.listdir(d)):
                if fn.lower().endswith(".json"):
                    result[os.path.splitext(fn)[0]] = os.path.join(d, fn)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[comfyui_draw] 读取工作流目录失败 {d}: {e}")
        return result

    @staticmethod
    def _read_file(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[comfyui_draw] 读取工作流文件失败 {path}: {e}")
            return None

    def _workflow_names(self):
        names = ["默认"]
        for n in self._dir_workflows().keys():
            if n not in names:
                names.append(n)
        for n in self._extra_workflows().keys():
            if n not in names:
                names.append(n)
        return names

    def _resolve_named(self, name):
        """按名称解析工作流文本：目录文件优先，其次配置 extra_workflows。"""
        dirwf = self._dir_workflows()
        if name in dirwf:
            return self._read_file(dirwf[name])
        return self._extra_workflows().get(name)

    def _resolve_workflow(self, name):
        # 未显式指定 -> 先看配置的「默认工作流名」，再退回默认工作流文本 / 内置示例
        if not name or name in ("默认", "default"):
            dflt = str(self.config.get("default_workflow_name", "") or "").strip()
            if dflt:
                wf = self._resolve_named(dflt)
                if wf is not None:
                    return wf
            wf = self.config.get("default_workflow") or ""
            return wf if str(wf).strip() else DEFAULT_WORKFLOW
        return self._resolve_named(name)

    @staticmethod
    def _placeholder_names(text):
        if not isinstance(text, str):
            return set()
        return {
            ph
            for ph in (
                "%prompt%",
                "%negative_prompt%",
                "%seed%",
                "%width%",
                "%height%",
                "%steps%",
                "%cfg%",
                "%batch_size%",
            )
            if ph in text
        }

    @staticmethod
    def _is_ui_format(wf):
        # ComfyUI 网页「Save」导出的普通工作流：顶层是带 nodes/links 列表的对象
        return (isinstance(wf, dict) and isinstance(wf.get("nodes"), list)
                and ("links" in wf or "last_node_id" in wf))

    @staticmethod
    def _looks_like_api(wf):
        # API 格式：顶层是 {节点id: {"class_type": ..., "inputs": {...}}}
        if not isinstance(wf, dict) or not wf:
            return False
        dict_vals = [v for v in wf.values() if isinstance(v, dict)]
        if not dict_vals:
            return False
        with_class = sum(1 for v in dict_vals if "class_type" in v)
        return with_class >= max(1, len(dict_vals) // 2)

    def _format_problem(self, workflow):
        """若工作流格式有问题返回错误说明文本，否则返回 None。"""
        if self._is_ui_format(workflow):
            return ("这看起来是 ComfyUI 网页里直接「Save」导出的工作流（包含 nodes / links），"
                    "不是 API 格式，/prompt 接口无法运行。\n"
                    "请在 ComfyUI 设置里勾选 “Enable Dev mode Options”，"
                    "再用 “Save (API Format)” 重新导出后使用。")
        if not self._looks_like_api(workflow):
            return ("无法识别这份工作流的格式。应为 ComfyUI 的「API 格式」JSON，"
                    "顶层形如 {\"节点编号\": {\"class_type\": ..., \"inputs\": {...}}, ...}。")
        return None

    def _build_mapping(self, prompt, negative, seed, width, height, steps, cfg, batch):
        # 值带类型标记："str" 支持子串替换；其余仅做精确匹配（替换为正确类型）
        return {
            "%prompt%": ("str", prompt),
            "%negative_prompt%": ("str", negative),
            "%seed%": ("int", int(seed)),
            "%width%": ("int", int(width)),
            "%height%": ("int", int(height)),
            "%steps%": ("int", int(steps)),
            "%cfg%": ("float", float(cfg)),
            "%batch_size%": ("int", int(batch)),
        }

    def _apply_placeholders(self, obj, mapping):
        if isinstance(obj, dict):
            return {k: self._apply_placeholders(v, mapping) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._apply_placeholders(v, mapping) for v in obj]
        if isinstance(obj, str):
            # 整个字符串就是一个占位符 -> 替换成带类型的真实值
            if obj in mapping:
                return mapping[obj][1]
            # 否则只对文本类占位符做子串替换（支持把提示词嵌进一段模板文字里）
            result = obj
            for ph, (typ, val) in mapping.items():
                if typ == "str" and ph in result:
                    result = result.replace(ph, str(val))
            return result
        return obj

    # ------------------------------------------------------------------ #
    # 原始工作流（无占位符）的智能参数注入
    # ------------------------------------------------------------------ #
    SAMPLER_HINT = ("KSampler", "SamplerCustom")  # class_type 含这些子串视为采样器

    def _inject_raw(self, workflow, prompt, opts, seed_value, skip_prompt=False):
        """对没有占位符的原始 API 工作流，按图结构注入参数。
        规则：正向提示词总是注入；负向 / 步数 / CFG / 尺寸 / 张数 仅在用户显式指定时覆盖，
        其余沿用工作流自身保存的值。返回实际生效值 dict 供回显。"""
        eff = {"seed": seed_value, "width": None, "height": None,
               "steps": None, "cfg": None, "batch_size": None}

        samplers = [(nid, node) for nid, node in workflow.items()
                    if isinstance(node, dict)
                    and any(h in str(node.get("class_type", "")) for h in self.SAMPLER_HINT)]

        mode = str(self.config.get("prompt_mode", "prepend") or "prepend").strip().lower()
        if mode not in ("prepend", "append", "replace"):
            mode = "prepend"

        # 1) 正 / 负提示词：顺着采样器的 positive / negative 连线找到目标文本节点
        pos_targets, neg_targets = [], []
        for _nid, node in samplers:
            inp = node.get("inputs", {})
            if not isinstance(inp, dict):
                continue
            p = self._link_target(inp.get("positive"))
            n = self._link_target(inp.get("negative"))
            if p and p not in pos_targets:
                pos_targets.append(p)
            if n and n not in neg_targets:
                neg_targets.append(n)

        injected_prompt = bool(skip_prompt)
        if not skip_prompt:
            for tid in pos_targets:
                if self._inject_text(workflow, tid, prompt, mode):
                    injected_prompt = True
            # 兜底：没有采样器线索时，若全图只有一个可写文本的节点，就当正向
            if not injected_prompt:
                text_nodes = [nid for nid, node in workflow.items()
                              if isinstance(node, dict) and isinstance(node.get("inputs"), dict)
                              and any(k in node["inputs"] and not isinstance(node["inputs"][k], list)
                                      for k in ("text", "text_g", "value", "string"))]
                if len(text_nodes) == 1:
                    injected_prompt = self._inject_text(workflow, text_nodes[0], prompt, mode)

        if not injected_prompt:
            raise ComfyUIError(
                "没能在这份工作流里自动定位「正向提示词」节点。\n"
                "可在该工作流 JSON 中，把正向提示词节点的 text 值改成 \"%prompt%\"（带引号），"
                "插件就会把提示词填到那里；负向同理用 \"%negative_prompt%\"。")

        neg = opts.get("negative")
        if neg is not None and str(neg).strip() != "":
            for tid in neg_targets:
                self._inject_text(workflow, tid, neg, mode)

        # 2) seed / steps / cfg 注入采样器
        want_seed = self.config.get("auto_randomize_seed", True) or (opts.get("seed") is not None)
        exp_steps = self._to_int(opts.get("steps"), None)
        exp_cfg = self._to_float(opts.get("cfg"), None)
        for _nid, node in samplers:
            inp = node.get("inputs", {})
            if not isinstance(inp, dict):
                continue
            if want_seed:
                for sk in ("seed", "noise_seed"):
                    if sk in inp and isinstance(inp[sk], int) and not isinstance(inp[sk], bool):
                        inp[sk] = seed_value
            if exp_steps is not None and isinstance(inp.get("steps"), (int, float)) \
                    and not isinstance(inp.get("steps"), bool):
                inp["steps"] = exp_steps
            if exp_cfg is not None and isinstance(inp.get("cfg"), (int, float)) \
                    and not isinstance(inp.get("cfg"), bool):
                inp["cfg"] = exp_cfg
            if isinstance(inp.get("steps"), (int, float)) and not isinstance(inp.get("steps"), bool):
                eff["steps"] = inp.get("steps")
            if isinstance(inp.get("cfg"), (int, float)) and not isinstance(inp.get("cfg"), bool):
                eff["cfg"] = inp.get("cfg")

        # 3) 尺寸 / 张数 注入到“潜空间创建”节点（须同时含 width/height/batch_size，
        #    以此把放大 / 缩放类节点（只有 width/height、无 batch_size）排除在外）
        size = self._parse_size_strict(opts.get("size"))
        exp_batch = self._to_int(opts.get("batch"), None)
        old_lat_w = old_lat_h = None
        for _nid, node in workflow.items():
            if not isinstance(node, dict):
                continue
            inp = node.get("inputs", {})
            if not isinstance(inp, dict):
                continue
            is_latent_size = (
                "width" in inp and "height" in inp and "batch_size" in inp
                and not isinstance(inp.get("width"), list)
                and not isinstance(inp.get("height"), list))
            if not is_latent_size:
                continue
            if size is not None:
                if old_lat_w is None:
                    ow, oh = inp.get("width"), inp.get("height")
                    if (isinstance(ow, (int, float)) and not isinstance(ow, bool) and ow > 0
                            and isinstance(oh, (int, float)) and not isinstance(oh, bool) and oh > 0):
                        old_lat_w, old_lat_h = float(ow), float(oh)
                inp["width"], inp["height"] = size
            if not isinstance(inp.get("batch_size"), list):
                if exp_batch is not None:
                    inp["batch_size"] = self._clamp_batch(exp_batch)
                if isinstance(inp.get("batch_size"), (int, float)) and not isinstance(inp.get("batch_size"), bool):
                    eff["batch_size"] = inp.get("batch_size")
            if isinstance(inp.get("width"), (int, float)) and not isinstance(inp.get("width"), bool):
                eff["width"] = inp.get("width")
            if isinstance(inp.get("height"), (int, float)) and not isinstance(inp.get("height"), bool):
                eff["height"] = inp.get("height")

        # 3.5) 若改了尺寸：按“原潜空间 → 原缩放目标”的放大倍率，同步换算写死尺寸的
        #      ImageScale 节点，避免横竖比不同的固定缩放把新图拉变形（如 鬼针草 的放大链）。
        if size is not None and old_lat_w and old_lat_h:
            try:
                for _nid, node in workflow.items():
                    if not isinstance(node, dict) or str(node.get("class_type", "")) != "ImageScale":
                        continue
                    sinp = node.get("inputs")
                    if not isinstance(sinp, dict):
                        continue
                    sw, sh = sinp.get("width"), sinp.get("height")
                    if (isinstance(sw, (int, float)) and not isinstance(sw, bool) and sw > 0
                            and isinstance(sh, (int, float)) and not isinstance(sh, bool) and sh > 0):
                        factor = ((float(sw) / old_lat_w) + (float(sh) / old_lat_h)) / 2.0
                        if factor <= 0:
                            continue
                        sinp["width"] = self._round8(int(round(size[0] * factor)))
                        sinp["height"] = self._round8(int(round(size[1] * factor)))
                        logger.info(f"[comfyui_draw] 已按放大倍率 {factor:.2f}x 同步 ImageScale -> "
                                    f"{sinp['width']}x{sinp['height']}")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[comfyui_draw] 同步 ImageScale 尺寸失败（忽略）：{e!r}")

        return eff

    @staticmethod
    def _link_target(ref):
        """ComfyUI 连线形如 ["6", 0]，返回上游节点 id 字符串。"""
        if isinstance(ref, list) and ref and isinstance(ref[0], (str, int)):
            return str(ref[0])
        return None

    @staticmethod
    def _combine_prompt(prompt, existing, mode):
        """把用户输入与节点里已有文本合并。
        prepend(默认)：用户词在前、已有文本在后（保留触发词 / 质量词等后缀）；
        append：已有文本在前、用户词在后；replace：直接用用户词覆盖。
        会智能处理分隔符（半角 / 全角逗号、顿号、分号）。"""
        p = (prompt or "").strip()
        e = existing if isinstance(existing, str) else ""
        if mode == "replace" or not e.strip():
            return p
        if not p:
            return e
        seps = "，,、;；"
        if mode == "append":
            left = e.rstrip()
            return (left + p) if (left and left[-1] in seps) else (left + ", " + p)
        # prepend
        right = e.lstrip()
        return (p + right) if (right and right[0] in seps) else (p + ", " + right)

    def _inject_text(self, workflow, node_id, new_text, mode, _depth=0):
        """把文本写入目标节点的文本控件（兼容 text / text_g+text_l / value 等），
        按 mode 与节点已有文本合并。若文本来自上游链接，跳一跳到上游再写。成功返回 True。"""
        if node_id is None or _depth > 6:
            return False
        node = workflow.get(str(node_id))
        if not isinstance(node, dict):
            return False
        inp = node.get("inputs")
        if not isinstance(inp, dict):
            return False
        # SDXL 双文本：两个都按同样规则合并
        dual = [k for k in ("text_g", "text_l") if k in inp and not isinstance(inp[k], list)]
        if dual:
            for k in dual:
                inp[k] = self._combine_prompt(new_text, inp.get(k, ""), mode)
            return True
        for k in ("text", "value", "string", "String", "wildcard_text", "populated_text", "prompt"):
            if k in inp:
                if isinstance(inp[k], list):
                    up = self._link_target(inp[k])
                    if up is not None and up != str(node_id):
                        return self._inject_text(workflow, up, new_text, mode, _depth + 1)
                else:
                    inp[k] = self._combine_prompt(new_text, inp.get(k, ""), mode)
                    return True
        return False

    def _parse_size_strict(self, size_str):
        """仅在能解析出宽高时返回 (w, h)，否则 None（不回退默认值）。"""
        if not size_str:
            return None
        for sep in ("x", "X", "*", "×", "✕", "✖"):
            if sep in size_str:
                a, _, b = size_str.partition(sep)
                try:
                    return self._clamp_dim(int(a)), self._clamp_dim(int(b))
                except Exception:  # noqa: BLE001
                    return None
        return None

    @staticmethod
    def _fmt_parts(eff):
        parts = []
        w, h = eff.get("width"), eff.get("height")
        if w and h:
            parts.append(f"{int(w)}x{int(h)}")
        if eff.get("steps") is not None:
            parts.append(f"steps={eff.get('steps')}")
        if eff.get("cfg") is not None:
            parts.append(f"cfg={eff.get('cfg')}")
        if eff.get("seed") is not None:
            parts.append(f"seed={eff.get('seed')}")
        loras = eff.get("loras") or []
        if loras:
            parts.append("LoRA:" + "/".join(f"{n}@{s}" for n, s in loras))
        return " · ".join(parts) if parts else "默认参数"

    # ------------------------------------------------------------------ #
    # LoRA 注入：往工作流模型链里插入 LoraLoaderModelOnly 节点
    # ------------------------------------------------------------------ #
    def _collect_loras(self, opts):
        """汇总配置 default_loras + 命令 --lora，返回 [(名称, 权重), ...]。"""
        raw = []
        dl = self.config.get("default_loras", [])
        if isinstance(dl, (list, tuple)):
            raw += [str(x) for x in dl]
        elif isinstance(dl, str):
            raw += dl.replace("，", " ").split()
        raw += list(opts.get("loras") or [])
        return self._parse_lora_list(raw)

    def _parse_lora_list(self, raw_items):
        max_loras = self._config_int("max_loras", 4, 0, 64)
        if len(raw_items) > max_loras:
            raise ComfyUIError(f"一次最多叠加 {max_loras} 个 LoRA。")
        max_strength = self._config_float("max_lora_strength", 2.0, 0.0, 100.0)
        out = []
        for x in raw_items:
            s = str(x).strip()
            if not s:
                continue
            name, strength = self._split_lora(s)
            if not name:
                raise ComfyUIError("LoRA 名称不能为空。")
            if not math.isfinite(strength) or abs(strength) > max_strength:
                raise ComfyUIError(
                    f"LoRA「{name}」权重必须在 {-max_strength:g} 到 {max_strength:g} 之间。"
                )
            out.append((name, strength))
        return out

    def _split_lora(self, s):
        """解析 名称[:权重]；权重缺省取 default_lora_strength；名称无扩展名时补 .safetensors。"""
        strength = self._to_float(self.config.get("default_lora_strength", 0.8), 0.8)
        name = s
        if ":" in s:
            a, b = s.rsplit(":", 1)
            try:
                strength = float(b)
                name = a
            except ValueError:
                name = s
        name = name.strip().strip('"').strip("'")
        if name and "." not in name and "/" not in name and "\\" not in name:
            name += ".safetensors"
        return name, float(strength)

    def _inject_lora(self, workflow, loras):
        """在工作流模型链最前端（紧接模型加载节点）插入若干 LoraLoaderModelOnly 节点，
        并把原本直接用该模型输出的节点改接到 LoRA 链末端。对单 / 多采样器都适用。"""
        if not loras:
            return
        samplers = [nid for nid, node in workflow.items()
                    if isinstance(node, dict)
                    and any(h in str(node.get("class_type", "")) for h in self.SAMPLER_HINT)]
        if not samplers:
            raise ComfyUIError("工作流里找不到采样器（KSampler 等），无法自动插入 LoRA。")
        origins = []
        for sampler_id in samplers:
            origin = self._trace_model_origin(workflow, sampler_id)
            if origin is not None:
                key = (str(origin[0]), origin[1])
                if key not in origins:
                    origins.append(key)
        if not origins:
            raise ComfyUIError("没能定位模型加载节点（UNet / Checkpoint），无法插入 LoRA。")
        next_id = self._max_int_id(workflow) + 1
        for origin_id, origin_slot in origins:
            # 收集直接消费该 MODEL 输出的连线，先收集再插入，避免把新 LoRA 自己重连。
            consumers = []
            for nid, node in list(workflow.items()):
                if not isinstance(node, dict):
                    continue
                inp = node.get("inputs", {})
                if not isinstance(inp, dict):
                    continue
                for k, v in inp.items():
                    if (
                        isinstance(v, list)
                        and len(v) >= 2
                        and str(v[0]) == origin_id
                        and v[1] == origin_slot
                    ):
                        consumers.append((nid, k))

            prev = [origin_id, origin_slot]
            for name, strength in loras:
                nid = str(next_id)
                next_id += 1
                workflow[nid] = {
                    "class_type": "LoraLoaderModelOnly",
                    "inputs": {
                        "lora_name": name,
                        "strength_model": float(strength),
                        "model": prev,
                    },
                    "_meta": {"title": "LoRA(自动插入)"},
                }
                prev = [nid, 0]

            for cid, ck in consumers:
                workflow[cid]["inputs"][ck] = list(prev)

    def _trace_model_origin(self, workflow, sampler_id, max_hop=12):
        """从采样器的 model 输入回溯，跳过已有的 LoRA 节点，找到真正的模型加载节点。
        返回 [节点id, 输出槽]。"""
        node = workflow.get(str(sampler_id))
        if not isinstance(node, dict):
            return None
        ref = (node.get("inputs", {}) or {}).get("model")
        if not (isinstance(ref, list) and ref):
            return None
        cur_id, slot = str(ref[0]), (ref[1] if len(ref) > 1 else 0)
        visited = set()
        for _ in range(max_hop):
            cur = workflow.get(cur_id)
            if not isinstance(cur, dict):
                return [cur_id, slot]
            cls = str(cur.get("class_type", ""))
            if "lora" in cls.lower():
                mref = (cur.get("inputs", {}) or {}).get("model")
                if isinstance(mref, list) and mref and cur_id not in visited:
                    visited.add(cur_id)
                    cur_id, slot = str(mref[0]), (mref[1] if len(mref) > 1 else 0)
                    continue
                return [cur_id, slot]
            return [cur_id, slot]
        return [cur_id, slot]

    @staticmethod
    def _max_int_id(workflow):
        mx = 0
        for k in workflow.keys():
            try:
                mx = max(mx, int(str(k)))
            except Exception:  # noqa: BLE001
                pass
        return max(mx, 1000)

    @staticmethod
    def _split_url(raw):
        """把用户填的地址规整成 (http_base, ws_base)。接受带或不带 scheme。"""
        raw = str(raw).strip()
        if raw.startswith("http://"):
            host, scheme = raw[len("http://"):], "http"
        elif raw.startswith("https://"):
            host, scheme = raw[len("https://"):], "https"
        else:
            host, scheme = raw, "http"
        host = host.strip("/")
        ws_scheme = "wss" if scheme == "https" else "ws"
        return f"{scheme}://{host}", f"{ws_scheme}://{host}"

    def _format_prompt_error(self, body):
        if isinstance(body, dict):
            err = body.get("error")
            msg = ""
            if isinstance(err, dict):
                msg = err.get("message") or err.get("type") or ""
            elif err:
                msg = str(err)
            extra = self._format_node_errors(body.get("node_errors"))
            joined = (msg + ("\n" + extra if extra else "")).strip()
            return joined or "提交工作流被 ComfyUI 拒绝。"
        return f"提交工作流失败：{body}"

    @staticmethod
    def _format_node_errors(node_errors):
        if not isinstance(node_errors, dict) or not node_errors:
            return ""
        parts = []
        for node_id, info in node_errors.items():
            errs = info.get("errors", []) if isinstance(info, dict) else []
            for e in errs:
                if isinstance(e, dict):
                    line = f"节点 {node_id}: {e.get('message', '')} {e.get('details', '')}".strip()
                    parts.append(line)
        return "\n".join(parts)

    @staticmethod
    def _format_exec_error(data):
        node = data.get("node_type") or data.get("node_id") or "?"
        msg = data.get("exception_message") or "执行错误"
        return f"工作流执行出错（节点 {node}）：{msg}"
