"""排队、限流、每日次数与出图记录。"""
import asyncio
import json
import math
import os
import time

from astrbot.api import logger

from .draw_queue import DrawCancelled, DrawQueue
from .errors import DrawRejected


class UsageMixin:
    """排队、限流、每日次数与出图记录。混入 ComfyUIDrawPlugin 使用，依赖主类的配置读取等通用方法。"""

    # ------------------------------------------------------------------ #
    # 排队、限流与每日次数
    # ------------------------------------------------------------------ #
    QUEUE_LABELS = {"local": "本地 ComfyUI", "cloud": "云端"}

    def _queue(self, kind):
        """本地与云端各一个队列；并发上限每次按配置刷新，改配置后无需重启。"""
        queues = getattr(self, "_queues", None)
        if queues is None:
            queues = self._queues = {}
        if kind == "cloud":
            limit = self._config_int("max_concurrent_cloud_tasks", 2, 1, 32)
        else:
            limit = self._config_int("max_concurrent_tasks", 2, 1, 32)
        queue = queues.get(kind)
        if queue is None:
            queue = queues[kind] = DrawQueue(kind, limit)
        elif queue.limit != limit:
            queue.set_limit(limit)
        return queue

    def _all_tickets(self):
        return [t for q in (getattr(self, "_queues", None) or {}).values() for t in q.tickets()]

    @classmethod
    def _user_id(cls, event):
        return cls._daily_me_uid(event)

    def _user_name(self, event):
        return self._safe_call(event, "get_sender_name") or self._user_id(event)

    def _admission_error(self, event, kind, count):
        """检查每人同时任务数、冷却、排队上限和每日次数；放行返回 None，否则返回提示。
        count 为本次要计入每日次数的张数（0 表示不计）。管理员不受限。"""
        if self._is_admin(event):
            return None
        uid = self._user_id(event)
        per_user = self._config_int("max_tasks_per_user", 1, 0, 100)
        if per_user:
            active = sum(1 for t in self._all_tickets() if t.uid == uid)
            if active >= per_user:
                return f"⚠️ 你已有 {active} 个绘图任务在生成或排队，等它完成后再发吧～（发送 /绘图队列 查看）"
        cooldown = self._config_int("user_cooldown_seconds", 0, 0, 86400)
        last = (getattr(self, "_user_last_start", None) or {}).get(uid)
        if cooldown and last is not None:
            remaining = int(math.ceil(cooldown - (time.time() - last)))
            if remaining > 0:
                return f"⚠️ 画得太快啦，请 {remaining} 秒后再试。"
        queue = self._queue(kind)
        max_waiting = self._config_int("max_queue_size", 20, 0, 1000)
        if max_waiting and len(queue.waiting) >= max_waiting:
            return f"⚠️ {self.QUEUE_LABELS.get(kind, kind)}排队的人太多了（{len(queue.waiting)} 个），请稍后再试。"
        limit = self._daily_limit(kind)
        if limit and count:
            used = self._usage_today(uid, kind)
            if used >= limit:
                return f"⚠️ 你今天的{self.QUEUE_LABELS.get(kind, kind)}绘图次数已用完（{used}/{limit} 张），明天再来吧～"
            if used + count > limit:
                return f"⚠️ 你今天的{self.QUEUE_LABELS.get(kind, kind)}绘图只剩 {limit - used} 张，本次要 {count} 张，请减少张数。"
        return None

    @staticmethod
    def _queue_error_text(error):
        if isinstance(error, DrawCancelled):
            return "⚠️ 这个绘图任务已被取消。"
        return str(error)

    async def _generate_in_queue(self, event, kind, label, progress_text, run, state, count=0):
        """排队 → 进度提示 → 执行 run()，逐条 yield 需要发送的消息。
        结果写入 state["results"]，异常写入 state["error"]（DrawRejected / DrawCancelled / 其他）。"""
        rejected = self._admission_error(event, kind, count)
        if rejected:
            state["error"] = DrawRejected(rejected)
            return
        queue = self._queue(kind)
        uid = self._user_id(event)
        ticket = queue.join(uid, self._user_name(event), label)
        last_start = getattr(self, "_user_last_start", None)
        if last_start is None:
            last_start = self._user_last_start = {}
        last_start[uid] = time.time()
        queue_message_id = progress_message_id = None
        try:
            if not ticket.running and self.config.get("show_progress", True):
                text = (
                    f"⏳ 排队中：第 {queue.ahead(ticket) + 1} 位，{len(queue.running)} 个任务正在生成"
                    f"（编号 #{ticket.id}）。轮到后自动开始，发送 /绘图队列 可查看或取消。"
                )
                queue_message_id, fallback = await self._start_progress(event, text)
                if fallback is not None:
                    yield fallback
            await queue.wait(ticket)
            await self._recall_progress_message(event, queue_message_id)
            queue_message_id = None
            if ticket.cancelled:
                raise DrawCancelled()
            if progress_text and self.config.get("show_progress", True):
                progress_message_id, fallback = await self._start_progress(event, progress_text)
                if fallback is not None:
                    yield fallback
            ticket.task = asyncio.ensure_future(run())
            try:
                state["results"] = await ticket.task
            except asyncio.CancelledError:
                if ticket.cancelled:
                    raise DrawCancelled() from None
                ticket.task.cancel()
                raise
        except DrawCancelled as e:
            state["error"] = e
        except Exception as e:  # noqa: BLE001
            state["error"] = e
        finally:
            queue.leave(ticket)
            await self._recall_progress_message(event, queue_message_id)
            await self._recall_progress_message(event, progress_message_id)

    def _data_path(self, filename):
        """运行态数据放在 data 目录，避免插件更新/重装时丢失。"""
        return os.path.join("data", "plugin_data", "astrbot_plugin_comfyui_draw", filename)

    def _load_json(self, path, default):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[comfyui_draw] 读取 {path} 失败：{e}")
            return default

    def _save_json(self, path, data):
        """原子写入 JSON，成功返回 True。"""
        tmp = path + ".tmp"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, path)
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[comfyui_draw] 保存 {path} 失败：{e}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:  # noqa: BLE001
                pass
            return False

    def _daily_limit(self, kind):
        key = "daily_limit_cloud" if kind == "cloud" else "daily_limit_local"
        return self._config_int(key, 0, 0, 100000)

    def _usage_store(self):
        """{"date": 今天, "local": {uid: 张数}, "cloud": {uid: 张数}}，跨天自动清零。"""
        today = time.strftime("%Y-%m-%d")
        usage = getattr(self, "_usage_data", None)
        if usage is None:
            usage = self._load_json(self._data_path("draw_usage.json"), {})
            if not isinstance(usage, dict):
                usage = {}
        if usage.get("date") != today:
            usage = {"date": today}
        for kind in ("local", "cloud"):
            if not isinstance(usage.get(kind), dict):
                usage[kind] = {}
        self._usage_data = usage
        return usage

    def _usage_today(self, uid, kind):
        return int(self._usage_store()[kind].get(str(uid), 0) or 0)

    def _add_usage(self, uid, kind, count):
        """只在开启了每日上限时计数，避免无意义的写盘。"""
        if not count or not self._daily_limit(kind):
            return
        usage = self._usage_store()
        usage[kind][str(uid)] = self._usage_today(uid, kind) + int(count)
        self._save_json(self._data_path("draw_usage.json"), usage)

    # ------------------------------------------------------------------ #
    # 出图记录（/重画、/我的绘图）
    # ------------------------------------------------------------------ #
    def _history_size(self):
        return self._config_int("history_size", 10, 0, 100)

    def _history(self):
        history = getattr(self, "_history_data", None)
        if history is None:
            history = self._load_json(self._data_path("draw_history.json"), {})
            if not isinstance(history, dict):
                history = {}
            self._history_data = history
        return history

    def _user_history(self, uid):
        records = self._history().get(str(uid))
        return records if isinstance(records, list) else []

    def _record_history(self, uid, kind, prompt, opts, label, images, edit=False):
        size = self._history_size()
        if not size:
            return
        saved_opts = {}
        for key, value in (opts or {}).items():
            if value is None or value == "" or value == []:
                continue
            if isinstance(value, (str, int, float, bool)) or (
                isinstance(value, list) and all(isinstance(v, str) for v in value)
            ):
                saved_opts[key] = value
        record = {
            "kind": kind,
            "prompt": str(prompt or ""),
            "opts": saved_opts,
            "label": label,
            "images": int(images),
            "edit": bool(edit),
            "time": int(time.time()),
        }
        history = self._history()
        history[str(uid)] = ([record] + self._user_history(uid))[:size]
        self._save_json(self._data_path("draw_history.json"), history)

    @staticmethod
    def _describe_record(record):
        prompt = str(record.get("prompt") or "").strip()
        preset = (record.get("opts") or {}).get("preset")
        if preset:
            prompt = f"[{preset}] {prompt}".strip()
        if record.get("edit"):
            prompt = f"(编辑原图) {prompt}".strip()
        if len(prompt) > 60:
            prompt = prompt[:60] + "…"
        return prompt or "（无描述）"
