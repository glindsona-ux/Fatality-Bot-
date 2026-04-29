import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from config import COR_VERMELHO, COR_VERDE, COR_VERMELHO_BOTAO, ID_CANAL_TICKET, CARGOS_SUPORTE
from datetime import datetime
import asyncio

def tem_cargo_suporte(member):
    return any(discord.utils.get(member.guild.roles, name=cargo) in member.roles for cargo in CARGOS_SUPORTE)

class BotaoAssumir(Button):
    def __init__(self):
        super().__init__(
            label="Assumir Ticket",
            style=discord.ButtonStyle.green,
            emoji="🫡",
            custom_id="assumir_ticket_fatality_v2"
        )

    async def callback(self, interaction: discord.Interaction):
        if not tem_cargo_suporte(interaction.user):
            return await interaction.response.send_message("❌ Só STAFF ou /SUPORTE pode assumir ticket.", ephemeral=True)

        thread = interaction.channel
        if "assumido-" in thread.name:
            return await interaction.response.send_message("❌ Esse ticket já foi assumido.", ephemeral=True)

        await interaction.response.defer()

        try:
            async for msg in thread.history(limit=5, oldest_first=True):
                if msg.embeds and msg.embeds[0].footer and "ID do autor:" in msg.embeds[0].footer.text:
                    id_autor = int(msg.embeds[0].footer.text.split(": ")[1])
                    break
            else:
                return await interaction.followup.send("❌ Erro ao ler dados do ticket.", ephemeral=True)
        except:
            return await interaction.followup.send("❌ Erro ao ler dados do ticket.", ephemeral=True)

        autor = interaction.guild.get_member(id_autor)
        if not autor:
            return await interaction.followup.send("❌ Autor do ticket não encontrado.", ephemeral=True)

        tipo_ticket = thread.name.split("-")[1] if "-" in thread.name else "suporte"
        novo_nome = f"assumido-{tipo_ticket}-{interaction.user.name}"
        await thread.edit(name=novo_nome)
        await thread.edit(invitable=False)

        embed = discord.Embed(
            title="🫡 TICKET ASSUMIDO",
            description=f"{interaction.user.mention} assumiu o controle deste ticket.\n\nAgora só ele e {autor.mention} podem ver e falar aqui.",
            color=COR_VERMELHO
        )
        await thread.send(embed=embed)
        await interaction.followup.send("✅ Tu assumiu o ticket. Thread renomeada e trancada pra outros STAFF.", ephemeral=True)

class BotaoFechar(Button):
    def __init__(self):
        super().__init__(
            label="Fechar Ticket",
            style=discord.ButtonStyle.red,
            emoji="🔒",
            custom_id="fechar_ticket_fatality_v2"
        )

    async def callback(self, interaction: discord.Interaction):
        thread = interaction.channel
        pode_fechar = False

        if "assumido-" in thread.name:
            staff_nome = thread.name.split("-")[-1]
            pode_fechar = interaction.user.name == staff_nome

        if not pode_fechar:
            async for msg in thread.history(limit=5, oldest_first=True):
                if msg.embeds and msg.embeds[0].footer and "ID do autor:" in msg.embeds[0].footer.text:
                    id_autor = int(msg.embeds[0].footer.text.split(": ")[1])
                    pode_fechar = interaction.user.id == id_autor
                    break

        if not pode_fechar:
            return await interaction.response.send_message("❌ Só quem abriu ou assumiu pode fechar.", ephemeral=True)

        await interaction.response.send_message("🔒 Fechando ticket em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await thread.delete()

class ViewControleTicket(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BotaoAssumir())
        self.add_item(BotaoFechar())

class MenuTicket(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte", description="Dúvidas gerais", emoji="🎫", value="suporte"),
            discord.SelectOption(label="Reembolso", description="Problemas com partidas", emoji="💰", value="reembolso"),
            discord.SelectOption(label="Vagas", description="Seja Staff/Mediador", emoji="📝", value="vagas"),
            discord.SelectOption(label="Denúncia", description="Reportar jogador", emoji="🚨", value="denuncia")
        ]
        super().__init__(
            placeholder="Escolha o tipo de ticket",
            custom_id="menu_ticket_fatality_v2",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        canal_painel = interaction.guild.get_channel(ID_CANAL_TICKET)
        if not canal_painel:
            return await interaction.followup.send("❌ Canal do painel não encontrado.", ephemeral=True)

        tipo_ticket = self.values[0]
        nome_thread = f"ticket-{tipo_ticket}-{interaction.user.name}"

        thread = await canal_painel.create_thread(
            name=nome_thread,
            type=discord.ChannelType.private_thread,
            auto_archive_duration=1440,
            reason=f"Ticket de {tipo_ticket} aberto por {interaction.user}"
        )

        await thread.add_user(interaction.user)

        for nome_cargo in CARGOS_SUPORTE:
            cargo = discord.utils.get(interaction.guild.roles, name=nome_cargo)
            if cargo:
                for membro in cargo.members:
                    try:
                        await thread.add_user(membro)
                    except:
                        pass

        embed = discord.Embed(
            title=f"🎫 TICKET DE {tipo_ticket.upper()}",
            description=f"{interaction.user.mention} descreva seu problema detalhadamente.\n\n**Assunto:** {tipo_ticket.capitalize()}\n**Status:** Aguardando STAFF assumir",
            color=COR_VERMELHO
        )
        embed.add_field(name="Instruções", value="• Explique o ocorrido\n• Mande prints se tiver\n• Aguarde um STAFF assumir", inline=False)
        embed.set_footer(text=f"FATALITY 20CC | ID do autor: {interaction.user.id}")
        embed.timestamp = datetime.now()

        mencoes = " ".join([c.mention for nome_cargo in CARGOS_SUPORTE if (c := discord.utils.get(interaction.guild.roles, name=nome_cargo))])

        await thread.send(content=f"{interaction.user.mention} {mencoes}", embed=embed, view=ViewControleTicket())
        await interaction.followup.send(f"✅ Ticket criado: {thread.mention}", ephemeral=True)

class ViewTicket(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuTicket())

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def painelticket(self, ctx):
        canal = self.bot.get_channel(ID_CANAL_TICKET)
        if not canal:
            return await ctx.send("❌ ID_CANAL_TICKET inválido.", delete_after=10)

        embed = discord.Embed(
            title="🎫 CENTRAL DE ATENDIMENTO FATALITY",
            description="Precisa de ajuda? Selecione abaixo e seu ticket abre automático em uma **thread privada**:\n\n**STAFF ou /SUPORTE: Primeiro a assumir pega o caso.**",
            color=COR_VERMELHO
        )
        embed.add_field(name="🎫 Suporte", value="Dúvidas gerais", inline=True)
        embed.add_field(name="💰 Reembolso", value="Problemas com partidas", inline=True)
        embed.add_field(name="📝 Vagas", value="Seja Staff/Mediador", inline=True)
        embed.add_field(name="🚨 Denúncia", value="Reportar jogador", inline=True)
        embed.set_footer(text="FATALITY 20CC • Atendimento 24h • Thread Privada")
        embed.timestamp = datetime.now()

        await canal.send(content="@here", embed=embed, view=ViewTicket())
        await ctx.send("✅ Painel de ticket postado.", delete_after=5)

async def setup(bot):
    bot.add_view(ViewTicket())
    bot.add_view(ViewControleTicket())
    await bot.add_cog(Tickets(bot))
