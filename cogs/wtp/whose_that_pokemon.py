import os
import discord

from discord.ext import commands
from utils.discord_helpers import get_channel_from_ctx

from cogs.wtp.factory import WtpPokemonFactory
from cogs.wtp.game import WtpGame


class WhoseThatPokemon(commands.Cog):
    def __init__(self, bot, wtp_path, wtp_bucket_path):
        self.bot = bot
        self.poke_factory = WtpPokemonFactory(
            wtp_path=wtp_path,
            wtp_bucket_path=wtp_bucket_path
        )
        self.current_games = []


    @commands.command(name='wtp', help='Start a round of whose that pokemon!')
    async def wtp(self, ctx, guess=None):
        current_game = self._get_game_in_progress(ctx.guild.id)

        if current_game and not guess:
            await ctx.channel.send('There is already a game in progress!')
            return

        if not current_game and guess:
            await ctx.channel.send('There\'s no game to guess on mate')
            return

        if current_game and guess:
            await self._make_attempt(ctx=ctx, wtp_game=current_game, guess=guess)
            return

        if not current_game and not guess:
            await self._start_game(ctx)


    def _get_game_in_progress(self, guild_id):
        return next((g for g in self.current_games if g.guild_id == guild_id), None)


    async def _start_game(self, ctx):
        print(f'Starting whose that Pokemon.....')

        game = WtpGame(
            guild_id=ctx.guild.id,
            pokemon=self.poke_factory.random(),
            on_complete=self._finish_game,
            channel=ctx.channel,
            loop=self.bot.loop
        )

        self.current_games.append(game)

        await ctx.channel.send(
            content='**Whose that Pokémon?**',
            file=discord.File(
                self.poke_factory.generate_wtp_img_bytes(pokemon=game.pokemon, is_sil=True),
                'whose-that-pokemon.png'
            )
        )

        await self._send_poke_sound(ctx, game)


    async def _finish_game(self, wtp_game, winning_user=None):
        self.current_games.remove(wtp_game)

        if winning_user:
            await wtp_game.channel.send(f'**{winning_user}** is the very best!')

        name_en = wtp_game.pokemon.names['en']
        await wtp_game.channel.send(
            content=f'It was **{name_en.capitalize()}**',
            file=discord.File(
                self.poke_factory.generate_wtp_img_bytes(pokemon=wtp_game.pokemon, is_sil=False),
                f'{name_en}.png'
            )
        )

        print(f'Whose that Pokemon game complete!')


    async def _make_attempt(self, ctx, wtp_game, guess):
        result = wtp_game.make_attempt(
            user_id=ctx.message.author.id,
            guess=guess.lower()
        )

        if result:
            await self._finish_game(
                wtp_game=wtp_game,
                winning_user=ctx.message.author.name
            )
        else:
            await ctx.message.add_reaction('\N{THUMBS DOWN SIGN}')


    async def _send_poke_sound(self, ctx, wtp_game):
        try:
            channel = get_channel_from_ctx(bot=self.bot, ctx=ctx)
            if channel:
                await self.bot.voice.play(channel=channel, source=wtp_game.pokemon.poke_sound_path, title='Whose that pokemon?')
        except Exception as e:
            print(e)