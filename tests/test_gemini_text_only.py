"""Offline checks for Gemini replies that contain text but no image."""
import unittest
from unittest.mock import patch

from test_optimized_plugin import PluginError, module
from test_sub2api_antigravity import PNG, Response, Session, configured

# 群聊截图里的真实回复：正常结束（STOP），只有文字和一个假的“[图片：…]”描述。
CHATTY = {"candidates": [{"content": {"parts": [{"text": (
    "好的，为您生成了一张博丽灵梦的图片。\n\n[图片：博丽灵梦的全身立绘。她站在神社的鸟居前，"
    "身穿经典的巫女服，手持御币，面带微笑。]\n\n如果您有其他需求，随时告诉我。"
)}]}, "finishReason": "STOP"}]}

SAFETY_TEXT = {"candidates": [{"content": {"parts": [{"text": "I can't help with that."}]},
                               "finishReason": "IMAGE_SAFETY"}]}


class TextOnlyTests(unittest.IsolatedAsyncioTestCase):
    def transport(self, *responses):
        session = Session(responses)
        return session, patch.object(module.aiohttp, "ClientSession", return_value=session, create=True)

    @staticmethod
    def texts(call):
        return [part.get("text", "") for part in call[1]["json"]["contents"][0]["parts"]]

    async def test_request_asks_for_image_output(self):
        session, stub = self.transport(Response())
        with stub:
            await configured()._run_openai_image("博丽灵梦")
        texts = self.texts(session.calls[0])
        self.assertEqual(texts[0], "博丽灵梦")  # 用户原文保持不变
        self.assertIn("return it as an image", texts[1])

    async def test_edit_uses_edit_hint(self):
        session, stub = self.transport(Response())
        with stub:
            await configured()._run_openai_image_edit("变手办", [PNG])
        self.assertIn("provided image", self.texts(session.calls[0])[-1])

    async def test_text_only_reply_is_retried_once_then_succeeds(self):
        session, stub = self.transport(Response(payload=CHATTY), Response())
        with stub:
            results = await configured()._run_openai_image("博丽灵梦")
        self.assertEqual(results, [(PNG, "gemini_0.png")])
        self.assertEqual(len(session.calls), 2)
        first, retry = self.texts(session.calls[0]), self.texts(session.calls[1])
        self.assertEqual(retry[:len(first)], first)
        self.assertIn("previous reply contained only text", retry[-1])

    async def test_text_only_twice_gives_clear_error(self):
        session, stub = self.transport(Response(payload=CHATTY), Response(payload=CHATTY))
        with stub:
            with self.assertRaises(PluginError) as caught:
                await configured()._run_openai_image("博丽灵梦")
        message = str(caught.exception)
        self.assertEqual(len(session.calls), 2)
        self.assertIn("只回复了文字", message)
        self.assertIn("已自动要求重新出图一次", message)
        self.assertIn("…", message)  # 模型回复被截断，不会把整段文字刷屏
        self.assertLess(len(message), 220)

    async def test_retry_can_be_disabled(self):
        session, stub = self.transport(Response(payload=CHATTY))
        with stub:
            with self.assertRaisesRegex(PluginError, "只回复了文字"):
                await configured(gemini_text_only_retry=False)._run_openai_image("博丽灵梦")
        self.assertEqual(len(session.calls), 1)

    async def test_safety_or_blocked_replies_are_not_retried(self):
        blocked = {"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"},
                   "candidates": [{"content": {"parts": [{"text": "no"}]}, "finishReason": "STOP"}]}
        for payload in (SAFETY_TEXT, blocked):
            session, stub = self.transport(Response(payload=payload))
            with stub:
                with self.assertRaisesRegex(PluginError, "没有返回最终图片"):
                    await configured()._run_openai_image("cat")
            self.assertEqual(len(session.calls), 1)

    async def test_retry_budget_is_per_image_in_batch(self):
        session, stub = self.transport(
            Response(payload=CHATTY), Response(), Response(payload=CHATTY), Response()
        )
        with stub:
            results = await configured()._run_openai_image("cat", n=2)
        self.assertEqual([name for _, name in results], ["gemini_0.png", "gemini_1.png"])
        self.assertEqual(len(session.calls), 4)

    async def test_partial_batch_keeps_first_image_when_second_stays_text_only(self):
        session, stub = self.transport(Response(), Response(payload=CHATTY), Response(payload=CHATTY))
        with stub:
            with self.assertRaises(PluginError) as caught:
                await configured()._run_openai_image("cat", n=2)
        self.assertEqual(len(caught.exception.partial_results), 1)
        self.assertIn("1/2", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
