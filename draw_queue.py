"""绘图任务排队：先到先得，限制同时运行数，并支持查看与取消。"""
import asyncio
import itertools
import time
from collections import deque


class DrawCancelled(Exception):
    """任务在排队或生成中被取消。"""
    pass


class DrawTicket:
    """一次绘图请求在队列里的票据。"""

    _ids = itertools.count(1)

    def __init__(self, queue, uid, user_name, label):
        self.id = next(self._ids)
        self.queue = queue
        self.uid = str(uid)
        self.user_name = str(user_name or "") or self.uid
        self.label = str(label or "")
        self.created = time.time()
        self.started = None
        self.future = None
        self.task = None
        self.cancelled = False

    @property
    def running(self):
        return self.started is not None


class DrawQueue:
    """FIFO 队列。join() 立即返回票据；有空位直接开始，否则排队等待 wait()。"""

    def __init__(self, name, limit):
        self.name = name
        self.limit = max(1, int(limit))
        self.running = []
        self.waiting = deque()

    def set_limit(self, limit):
        self.limit = max(1, int(limit))
        self._dispatch()

    def join(self, uid, user_name="", label=""):
        ticket = DrawTicket(self, uid, user_name, label)
        if len(self.running) < self.limit and not self.waiting:
            ticket.started = time.time()
            self.running.append(ticket)
        else:
            ticket.future = asyncio.get_running_loop().create_future()
            self.waiting.append(ticket)
        return ticket

    def ahead(self, ticket):
        """排在该票据前面的等待数；已开始返回 0。"""
        try:
            return list(self.waiting).index(ticket)
        except ValueError:
            return 0

    async def wait(self, ticket):
        """等到轮到该票据；排队中被取消时抛出 DrawCancelled。"""
        if ticket.future is not None and not ticket.running:
            await ticket.future

    def leave(self, ticket):
        """结束（成功、失败或取消）时调用，可重复调用。"""
        if ticket in self.running:
            self.running.remove(ticket)
        else:
            try:
                self.waiting.remove(ticket)
            except ValueError:
                pass
        if ticket.future is not None and not ticket.future.done():
            ticket.future.cancel()
        self._dispatch()

    def cancel(self, ticket):
        """取消票据：排队中的直接移出；生成中的取消其后台任务。"""
        ticket.cancelled = True
        if ticket in self.waiting:
            self.waiting.remove(ticket)
            if ticket.future is not None and not ticket.future.done():
                ticket.future.set_exception(DrawCancelled())
            self._dispatch()
            return True
        if ticket in self.running:
            if ticket.task is not None and not ticket.task.done():
                ticket.task.cancel()
            return True
        return False

    def tickets(self):
        return list(self.running) + list(self.waiting)

    def _dispatch(self):
        while self.waiting and len(self.running) < self.limit:
            ticket = self.waiting.popleft()
            if ticket.future is None or ticket.future.done():
                continue
            ticket.started = time.time()
            self.running.append(ticket)
            ticket.future.set_result(None)
