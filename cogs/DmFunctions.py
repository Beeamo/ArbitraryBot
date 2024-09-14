import discord
from discord.ext import commands
from discord import ui, app_commands
import asyncio
import time
from utils.DmQueue import MessageQueue, get_dm_queue

class DmGroup(commands.GroupCog, name="mention", description="mention options"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.loop.create_task(self.message_queue_worker())

    @app_commands.command(name="pause", description="pause dm actions")
    @app_commands.checks.has_permissions(administrator=True)
    async def pause(self, itx: discord.Interaction):
        queue = get_dm_queue(self.bot)
        await queue.pause()
        await itx.response.send_message("Messaging has been paused", ephemeral=True)

    @app_commands.command(name="resume", description="resume dm actions")
    @app_commands.checks.has_permissions(administrator=True)
    async def resume(self, itx: discord.Interaction):
        queue = get_dm_queue(self.bot)
        await queue.resume()
        await itx.response.send_message("Messaging has been resumed", ephemeral=True)

    async def message_queue_worker(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            queue = get_dm_queue(self.bot)
            await queue.process_queue()
            await asyncio.sleep(1)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        mentionset = set(message.mentions)
        members = list()
        for member in mentionset:
            if member == message.author or member.bot:
                continue
            members.append(member)
        if members == []:
            return
        queue = get_dm_queue(self.bot)
        if message.reference:
            reference = message.reference
            referencemessage = await message.channel.fetch_message(reference.message_id)
            member = list()
            member.append(referencemessage.author)
            if referencemessage.author != message.author:   
                queue.add_message(f"🫴you have received a reply: {message.jump_url}", message.guild.id, member)
            for item in mentionset:
                if item == referencemessage.author:
                    remove = item
                    break
            if remove:
                mentionset.remove(remove)
        if len(mentionset) != 0: 
            queue.add_message(f"👆You Were Mentioned: {message.jump_url}", message.guild.id, mentionset)


    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        await thread.add_user(self.bot.user)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DmGroup(bot))