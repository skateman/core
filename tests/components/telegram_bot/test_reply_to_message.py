"""Tests for telegram_bot reply_to_message event data."""
import pytest

from homeassistant.components.telegram_bot import (
    BaseTelegramBotEntity,
    EVENT_TELEGRAM_COMMAND,
    EVENT_TELEGRAM_TEXT,
)
from homeassistant.core import callback

CHAT_ID = 123456
USER_ID = 123456


def _base_message(text="/start", reply_to=None):
    """Build a minimal Telegram update dict with a message."""
    msg = {
        "message_id": 1,
        "from": {"id": USER_ID, "first_name": "Test"},
        "chat": {"id": CHAT_ID},
        "text": text,
    }
    if reply_to is not None:
        msg["reply_to_message"] = reply_to
    return {"message": msg}


@pytest.fixture
def telegram_bot(hass):
    """Return a BaseTelegramBotEntity instance."""
    return BaseTelegramBotEntity(hass, [CHAT_ID])


@pytest.fixture
def captured_events(hass):
    """Capture telegram events."""
    events = []

    @callback
    def _capture(event):
        events.append(event.data)

    hass.bus.async_listen(EVENT_TELEGRAM_COMMAND, _capture)
    hass.bus.async_listen(EVENT_TELEGRAM_TEXT, _capture)
    return events


async def test_regular_message_no_reply(hass, telegram_bot, captured_events):
    """A regular message (not a reply) should NOT contain reply_to_message."""
    telegram_bot.process_message(_base_message(text="hello"))
    await hass.async_block_till_done()

    assert len(captured_events) == 1
    assert "reply_to_message" not in captured_events[0]


async def test_reply_to_user_message(hass, telegram_bot, captured_events):
    """A reply to a user message includes reply_to_message with from fields."""
    reply_to = {
        "message_id": 42,
        "text": "original text",
        "from": {
            "id": 999,
            "first_name": "Alice",
            "last_name": "Smith",
            "is_bot": False,
        },
    }
    telegram_bot.process_message(_base_message(text="my reply", reply_to=reply_to))
    await hass.async_block_till_done()

    assert len(captured_events) == 1
    reply_data = captured_events[0]["reply_to_message"]
    assert reply_data["message_id"] == 42
    assert reply_data["text"] == "original text"
    assert reply_data["from"]["id"] == 999
    assert reply_data["from"]["first_name"] == "Alice"
    assert reply_data["from"]["last_name"] == "Smith"
    assert reply_data["from"]["is_bot"] is False


async def test_reply_to_bot_message(hass, telegram_bot, captured_events):
    """A reply to a bot message includes from.is_bot == True."""
    reply_to = {
        "message_id": 55,
        "text": "bot response",
        "from": {
            "id": 888,
            "first_name": "MyBot",
            "last_name": None,
            "is_bot": True,
        },
    }
    telegram_bot.process_message(_base_message(text="replying to bot", reply_to=reply_to))
    await hass.async_block_till_done()

    assert len(captured_events) == 1
    reply_data = captured_events[0]["reply_to_message"]
    assert reply_data["from"]["is_bot"] is True


async def test_reply_to_caption_message(hass, telegram_bot, captured_events):
    """A reply to a message with no text but a caption uses caption as text."""
    reply_to = {
        "message_id": 77,
        "caption": "photo caption",
        "from": {
            "id": 999,
            "first_name": "Alice",
            "last_name": "Smith",
            "is_bot": False,
        },
    }
    telegram_bot.process_message(_base_message(text="nice pic", reply_to=reply_to))
    await hass.async_block_till_done()

    assert len(captured_events) == 1
    reply_data = captured_events[0]["reply_to_message"]
    assert reply_data["text"] == "photo caption"


async def test_command_with_reply(hass, telegram_bot, captured_events):
    """A command message that is also a reply includes both command and reply_to_message."""
    reply_to = {
        "message_id": 10,
        "text": "the question",
        "from": {
            "id": 999,
            "first_name": "Alice",
            "last_name": "Smith",
            "is_bot": False,
        },
    }
    telegram_bot.process_message(
        _base_message(text="/ask something", reply_to=reply_to)
    )
    await hass.async_block_till_done()

    assert len(captured_events) == 1
    ev = captured_events[0]
    # Command fields
    assert ev["command"] == "/ask"
    assert ev["args"] == ["something"]
    # Reply fields
    reply_data = ev["reply_to_message"]
    assert reply_data["message_id"] == 10
    assert reply_data["text"] == "the question"
