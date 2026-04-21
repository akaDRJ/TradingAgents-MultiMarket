import unittest
from types import SimpleNamespace

from cli.main import MessageBuffer, record_stream_messages


class RecordStreamMessagesTests(unittest.TestCase):
    def test_records_each_new_message_and_tool_call_once(self):
        buffer = MessageBuffer()
        messages = [
            SimpleNamespace(
                id="m1",
                content="alpha",
                tool_calls=[{"name": "fetch_news", "args": {"ticker": "BTCUSDT"}}],
            ),
            SimpleNamespace(
                id="m1",
                content="alpha",
                tool_calls=[{"name": "fetch_news", "args": {"ticker": "BTCUSDT"}}],
            ),
            SimpleNamespace(
                id="m2",
                content="beta",
                tool_calls=[SimpleNamespace(name="fetch_price", args={"ticker": "BTCUSDT"})],
            ),
        ]

        record_stream_messages(buffer, messages)

        self.assertEqual(len(buffer.messages), 2)
        self.assertEqual(len(buffer.tool_calls), 2)
        self.assertEqual(buffer.messages[0][1:], ("System", "alpha"))
        self.assertEqual(buffer.messages[1][1:], ("System", "beta"))
        self.assertEqual(buffer.tool_calls[0][1:], ("fetch_news", {"ticker": "BTCUSDT"}))
        self.assertEqual(buffer.tool_calls[1][1:], ("fetch_price", {"ticker": "BTCUSDT"}))


if __name__ == "__main__":
    unittest.main()
