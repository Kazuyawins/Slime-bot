"""Regression coverage for link refresh after restarts and missing originals."""

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import discord
from slime.links import LinkControlView


class LinkRefreshTests(unittest.IsolatedAsyncioTestCase):
    def interaction(self, displayed, original=""):
        return NS(
            channel=NS(fetch_message=AsyncMock(return_value=NS(content=original))),
            message=NS(content=displayed, edit=AsyncMock()),
            response=NS(defer=AsyncMock()),
            followup=NS(send=AsyncMock()),
        )

    async def test_restored_view_keeps_converted_link_without_reconverting(self):
        view = LinkControlView(0, 0, "")
        original = "https://fxreddit.seria.moe/r/test/comments/123"
        interaction = self.interaction(original + "\n\n-# 🔄 更新済み")
        await view.update_link_button.callback(interaction)
        interaction.channel.fetch_message.assert_not_awaited()
        interaction.message.edit.assert_awaited_once_with(
            content=original + "\n\n-# 🔄 更新済み", suppress=False
        )

    async def test_missing_original_uses_current_link(self):
        view = LinkControlView(7, 1, "")
        interaction = self.interaction("https://fxtwitter.com/u/status/123")
        interaction.channel.fetch_message.side_effect = discord.NotFound(
            NS(status=404, reason="Not Found"), "Unknown message"
        )
        await view.update_link_button.callback(interaction)
        self.assertIn(
            "https://fxtwitter.com/u/status/123",
            interaction.message.edit.call_args.kwargs["content"],
        )

    async def test_deleted_link_in_original_does_not_erase_current_link(self):
        for original in ("", "リンクを削除しました"):
            with self.subTest(original=original):
                view = LinkControlView(7, 1, "")
                interaction = self.interaction("https://fxtwitter.com/u/status/123", original)
                await view.update_link_button.callback(interaction)
                self.assertIn(
                    "https://fxtwitter.com/u/status/123",
                    interaction.message.edit.call_args.kwargs["content"],
                )

    async def test_no_recoverable_url_does_not_edit_message(self):
        view = LinkControlView(0, 0, "")
        interaction = self.interaction("\n\n-# 🔄 更新済み")
        await view.update_link_button.callback(interaction)
        interaction.message.edit.assert_not_awaited()
        self.assertIn("変更していません", interaction.followup.send.call_args.args[0])

    async def test_edit_failure_is_reported_after_deferral(self):
        view = LinkControlView(0, 0, "")
        interaction = self.interaction("https://fxtwitter.com/u/status/123")
        interaction.message.edit.side_effect = RuntimeError("edit failed")
        await view.update_link_button.callback(interaction)
        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        interaction.followup.send.assert_awaited_once()
        self.assertIn("更新に失敗", interaction.followup.send.call_args.args[0])
