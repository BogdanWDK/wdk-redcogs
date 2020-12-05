#imports

#discord
from redbot.core import Config, commands, checks
import discord
#other
from urllib.request import Request, urlopen
from datetime import datetime
from io import StringIO
from io import BytesIO
import requests
import random
import json
import re
#endof imports

links_regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

#cog
class ShortLinks(commands.Cog):
    """Shorten a link through my personal url shortener api."""

    async def red_get_data_for_user(self, *, user_id):
        return {}  # No data to get

    async def red_delete_data_for_user(self, *, requester, user_id):
        pass  # No data to delete

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2245879106, force_registration=True)
        datastore = {"api": None,"watching": []}
        self.config.register_guild(**datastore)


    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def shortlinks(self, ctx : commands.Context):
    	""" Shorten your links without hassle.
    	An account is needed at https://clean.link/
    	https://clean.link/user/tools#api - to get the api .
    	"""

    @shortlinks.command(name="api")
    async def shortlinks_api(self, ctx, api):
        """Set the API Key."""
        await self.config.guild(ctx.guild).api.set(api)
        await ctx.send(f"ShortLinks Api set to: {api}.")


    @shortlinks.command(name="watch")
    async def watch(self, ctx, channel: discord.TextChannel):
        """ All links will be replaced with shortened ones in the given channel."""
        channel_list = await self.config.guild(ctx.guild).watching()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
        await self.config.guild(ctx.guild).watching.set(channel_list)
        await ctx.send(f"{self.bot.get_channel(channel.id).mention}'s links will be replaced by shortened ones.")


    @shortlinks.command(name="unwatch")
    async def unwatch(self, ctx, channel: discord.TextChannel):
        """Delete a channel from the watchlist."""
        channel_list = await self.config.guild(ctx.guild).watching()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
        else:
            return await ctx.send("Channel is not being watched.")
        await self.config.guild(ctx.guild).watching.set(channel_list)
        await ctx.send(f"{self.bot.get_channel(channel.id).mention} will not have its links replaced anymore.")

    @commands.command(pass_context=True, aliases=[ 'sh', 'cut'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def short(self, ctx, args):
        """ Shorten links."""
        data = await self.config.guild(ctx.guild).all()
        key = data["api"]
        url = "https://clean.link/api/"
        payload = {'key' : key, 'url' : args}
        r = requests.get(url, params=payload)
        a = r.json()
        if a['error'] == 1:
            await ctx.send(a['msg'])
        else:
            await ctx.message.delete()
            await ctx.send(a['short'])

    @commands.command(pass_context=True, aliases=[ 'sha', 'cuta'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shorta(self, ctx, *, args):
        """ Shorten links with custom alias."""
        data = await self.config.guild(message.guild).all()
        key = data["api"]
        check = args.split(" ")
        url = "https://clean.link/api/"
        payload = {'key' : key, 'url' : check[0], 'custom' : check[1]}
        r = requests.get(url, params=payload)
        a = r.json()
        if a['error'] == 1:
            await ctx.send(a['msg'])
        else:
            await ctx.message.delete()
            await ctx.send(a['short'])


    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        if message.author.bot:
            return
        data = await self.config.guild(message.guild).all()
        watch_channel_list = data["watching"]
        if not watch_channel_list:
            return
        if message.channel.id not in watch_channel_list:
            return
        try:
            sentence = message.content.split()
            for word in sentence:
                if self._match_url(word):
                    key = data["api"]
                    url = "https://clean.link/api/";
                    payload = {'key' : key, 'url' : word}
                    r = requests.get(url, params=payload)
                    a = r.json()
                    if a['error'] == 1:
                        await message_channel.send(a['msg'])
                    else:
                        extra = message.content.replace(word, a['short'])
                        msg1 = "{}: {}".format(message.author.name, extra)
                        await message.channel.send(msg1)
                        await message.delete()
        except Exception as e:
            await message.channel.send(e)
            pass

    @staticmethod
    def _match_url(url):
        return links_regex.match(url)