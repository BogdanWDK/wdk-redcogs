#imports

#discord
from redbot.core import Config, commands, checks
import discord
#other
from urllib.parse import urlencode
from datetime import datetime
from io import StringIO
from io import BytesIO
import requests
import random
import json
import re
import datetime
import pycurl
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
        datastore = {"api": None,"watching": [], "domain": None}
        self.config.register_guild(**datastore)


    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def shortlinks(self, ctx : commands.Context):
        """ Shorten your links without hassle.
        An account is needed at https://clean.link/
        https://clean.link/user/tools#api - to get the api .

        __**Commands:**__
        **short** Shorten a link. Use [p]short for more info.
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

    @shortlinks.command(name="domain")
    async def domain(self, ctx, domain):
        """ Set the domain for url shortening.."""
        await self.config.guild(ctx.guild).domain.set(domain)
        await ctx.send("All links will be shortened through " + domain + " now.")


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
    async def short(self, ctx, link, alias : str = None, domain : str = None, password : str = None, expiry : str = None, ltype : str = None):
        """Shorten Links.
        ===============
        If you want to set one argument but ignore the rest, use null.
        Password must be longer than 4.
        Expiry format: yyyy-mm-dd
        To see the domain list, login at https://clean.link/
        Type must be direct/frame/splash/splashid*
        *splashid: Get the splash id from https://clean.link/user/splash"""
        data = await self.config.guild(ctx.guild).all()
        key = data["api"]
        payload = {'url' : link}
        if alias:
            if alias != "null":
                payload['custom'] = alias
            else:
                payload['custom'] = ""
        if password:
            if password != "null":
                if len(password) < 4:
                    await ctx.send("Password must be longer than 4.")
                    return
                else:
                    payload['password'] = password
            else:
                payload['password'] = ""
        if domain:
            if domain != "null":
                payload['domain'] = 'https://' + domain + ''
            else:
                if data['domain']:
                    payload['domain'] = 'https://' + data['domain'] + ''
                else:
                    payload['domain'] = ""
        else:
            if data['domain']:
                payload['domain'] = 'https://' + data['domain'] + ''
            else:
                payload['domain'] = ""
        if expiry:
            if expiry != "null":
                if datetime.datetime.strptime(expiry, '%Y-%m-%d'):
                    payload['expiry'] = expiry
                else:
                    await ctx.send("Expiry format incorrect. Example: 2021-07-21")
                    return
            else:
                payload['expiry'] = ""
        if ltype:
            if ltype != "null":
                payload['type'] = ltype
            else:
                payload['type'] = ""
        heds = {'Authorization': 'Token ' + key, 'Content-Type': 'application/json'}
        response = requests.post(url="https://clean.link/api/url/add", headers=heds, json=payload)
        if json.loads(response.text)['error'] == 0:
            await ctx.send(json.loads(response.text)['short'])
        else:
            await ctx.send(json.loads(response.text)['msg'])


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
            newmessage = message.content
            sentence = message.content.split()
            isit = 0
            for word in sentence:
                if self._match_url(word):
                    payload = {'url' : word}
                    heds = {'Authorization': 'Token ' + data['api'], 'Content-Type': 'application/json'}
                    response = requests.post(url="https://clean.link/api/url/add", headers=heds, json=payload)
                    if json.loads(response.text)['error'] == 0:
                        newmessage = newmessage.replace(word, json.loads(response.text)['short'])
                        isit = 1
                    else:
                        await ctx.send(json.loads(response.text)['msg'])
            if isit > 0:    
                await message.channel.send(newmessage)
                await message.delete()
        except Exception as e:
            print(e)
            pass

    @staticmethod
    def _match_url(url):
        return links_regex.match(url)
