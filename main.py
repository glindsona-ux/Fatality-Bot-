import discord
from discord.ext import commands
import os
import traceback
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class FatalityBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("=== INICIANDO SETUP_HOOK ===")
        print(f"Pasta atual: {os.getcwd()}")
        print(f"Arquivos na pasta cogs: {os.listdir('./cogs')}")
        
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Cog {filename} carregado')
                except Exception as e:
                    print(f'❌ ERRO no {filename}: {e}')
                    traceback.print_exc()
        
        from cogs.tickets import ViewTicket, ViewControleTicket
        from cogs.fila_med import ViewMediadores, ViewConfiPix
        from cogs.filas import criar_views_filas
        from cogs.ranking import ViewPainelRanking
        
        self.add_view(ViewTicket())
        self.add_view(ViewControleTicket())
        self.add_view(ViewMediadores())
        self.add_view(ViewConfiPix())
        self.add_view(ViewPainelRanking())
        for view in criar_views_filas():
            self.add_view(view)
        
        print("=== FATALITY V2 ONLINE ===")

bot = FatalityBot()

@bot.event
async def on_ready():
    print(f'Logado como {bot.user} | FATALITY 20CC')
    print(f'Comandos carregados: {[cmd.name for cmd in bot.commands]}')
    await bot.change_presence(activity=discord.Game(name="FATALITY 20CC 🔴"))

@bot.event
async def on_message(message):
    print(f"Mensagem detectada: {message.content} | Autor: {message.author}")
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send("PONG! FATALITY V2 ONLINE 💀🔴")

if __name__ == "__main__":
    bot.run(TOKEN)
