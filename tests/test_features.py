"""Offline regression tests: no Discord token or network connection required."""

import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FeatureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.directory.name)
        import bot
        from slime import config

        self.bot, self.config = bot.bot, config
        config.SPAM_SETTINGS = {}
        config.CUSTOM_RESPONSES = {}
        config.user_message_history.clear()

    async def asyncTearDown(self):
        os.chdir(self.cwd)
        self.directory.cleanup()

    def message(self, text):
        return NS(
            content=text,
            id=1,
            guild=NS(id=42),
            author=NS(
                id=7,
                bot=False,
                mention="<@7>",
                guild_permissions=NS(administrator=False),
                timeout=AsyncMock(),
                kick=AsyncMock(),
                ban=AsyncMock(),
            ),
            channel=NS(send=AsyncMock()),
        )

    async def test_commands_registered_once(self):
        names = [c.name for c in self.bot.tree.get_commands()]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(
            set(
                "help ping avatar history setchannel setlog logtoggle spamsetting setwelcome setleave addrole captcha_setup addresponse delresponse exportconfig importconfig sendmessage sendembed test testchannel".split()
            )
            <= set(names)
        )

    async def test_all_ten_preview_services(self):
        samples = [
            ("youtube.com/watch?v=abc", "koutube.com"),
            ("x.com/u/status/123", "fxtwitter.com"),
            ("instagram.com/p/abc", "oginstagram.com"),
            ("vt.tiktok.com/abc", "tnktok.com"),
            ("facebook.com/abc", "facebed.com"),
            ("threads.net/@u/post/1", "fixthreads.com"),
            ("redd.it/abc", "fxreddit.seria.moe"),
            ("pixiv.net/artworks/123", "phixiv.net"),
            ("bsky.app/profile/u/post/1", "bskx.app"),
            ("nicovideo.jp/watch/sm1", "nicovideo.gay"),
        ]
        for url, target in samples:
            with self.subTest(url=url):
                m = self.message("https://" + url)
                await self.bot.on_message(m)
                self.assertIn(target, m.channel.send.call_args.args[0])

    async def test_imported_configuration_reaches_consumers(self):
        from slime import administration, logging_events

        data = {
            "custom_responses": {"42": {"hello": "reply"}},
            "log_settings": {"42": {"channel_id": 9, "enabled": True}},
        }
        i = NS(response=NS(send_message=AsyncMock()))
        file = NS(
            filename="config.json",
            read=AsyncMock(return_value=json.dumps(data).encode()),
        )
        await administration.importconfig.callback(i, file)
        m = self.message("hello")
        await self.bot.on_message(m)
        m.channel.send.assert_awaited_once_with("reply")
        self.assertEqual(logging_events.get_guild_log_channel(42), 9)
        self.assertTrue(Path("custom_responses.txt").exists())

    async def test_moderation_short_circuits_replies_and_links(self):
        self.config.SPAM_SETTINGS = {
            42: {
                "enabled": True,
                "count": 1,
                "seconds": 5,
                "action": "timeout",
                "timeout_duration": 17,
            }
        }
        m = self.message("https://x.com/u/status/123")
        self.config.CUSTOM_RESPONSES = {42: {m.content: "custom reply"}}
        await self.bot.on_message(m)
        m.author.timeout.assert_awaited_once()
        self.assertEqual(m.channel.send.await_count, 1)
        self.assertNotIn("fxtwitter", m.channel.send.call_args.args[0])

    async def test_bot_messages_ignored(self):
        m = self.message("https://x.com/u/status/123")
        m.author.bot = True
        await self.bot.on_message(m)
        m.channel.send.assert_not_awaited()

    async def test_link_refresh_uses_edited_original_message(self):
        from slime.links import LinkControlView

        view = LinkControlView(7, 1, "https://x.com/u/status/123")
        interaction = NS(
            channel=NS(
                fetch_message=AsyncMock(
                    return_value=NS(content="https://x.com/u/status/456")
                )
            ),
            message=NS(edit=AsyncMock()),
            response=NS(send_message=AsyncMock()),
        )
        await view.update_link_button.callback(interaction)
        self.assertIn(
            "fxtwitter.com/u/status/456",
            interaction.message.edit.call_args.kwargs["content"],
        )
        interaction.response.send_message.assert_awaited_once()

    async def test_slash_error_logs_and_replies(self):
        from slime import lifecycle
        from unittest.mock import patch

        interaction = NS(
            guild=NS(id=42),
            command=NS(name="ping"),
            user=NS(mention="<@7>"),
            response=NS(is_done=lambda: False, send_message=AsyncMock()),
        )
        with patch.object(lifecycle, "send_error_log", new_callable=AsyncMock) as log:
            await self.bot.tree.on_error(interaction, RuntimeError("failure"))
            log.assert_awaited_once()
        interaction.response.send_message.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
