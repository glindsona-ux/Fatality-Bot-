import discord
from discord.ext import commands
from discord.ui import Button, View
from config import COR_VERMELHO, COR_VERDE
import json
import os
from datetime import datetime, timedelta

ARQUIVO_PONTOS = "pontos_fatality.json"
ARQUIVO_HISTORICO = "historico_vitorias.json"

def carregar_json(arquivo):
    if not os.path.exists(arquivo):
        with open(arquivo, 'w') as f:
            json.dump({}, f)
    with open(arquivo, 'r') as f:
        return json.load(f)

def salvar_json(arquivo, dados):
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=4)

def adicionar_vitoria(user_id):
    pontos = carregar_json(ARQUIVO_PONTOS)
    historico = carregar_json(ARQUIVO_HISTORICO)
    user_id = str(user_id)
    
    # Pontos gerais
    pontos[user_id] = pontos.get(user_id, 0) + 1
    
    # Histórico pra ranking semanal/mensal
    if user_id not in historico:
        historico[user_id] = []
    historico[user_id].append({
        "data": datetime.now().isoformat(),
        "timestamp": datetime.now().timestamp()
    })
    
    salvar_json(ARQUIVO_PONTOS, pontos)
    salvar_json(ARQUIVO_HISTORICO, historico)
    return pontos[user_id]

def get_ranking_geral():
    pontos = carregar_json(ARQUIVO_PONTOS)
    return sorted(pontos.items(), key=lambda x: x[1], reverse=True)

def get_ranking_periodo(dias):
    historico = carregar_json(ARQUIVO_HISTORICO)
    agora = datetime.now().timestamp()
    limite = agora - (dias * 24 * 60 * 60)
    
    contagem = {}
    for user_id, vitorias in historico.items():
        count = sum(1 for v in vitorias if v["timestamp"] >= limite)
        if count > 0:
            contagem[user_id] = count
    
    return sorted(contagem.items(), key=lambda x: x[1], reverse=True)

# ================== VIEW PAINEL RANKING ==================
class ViewPainelRanking(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Meu Perfil", 
        style=discord.ButtonStyle.green, # VERDE = POSITIVO
        emoji="👤", 
        custom_id="meu_perfil_fatality_v2"
    )
    async def meu_perfil(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        pontos = carregar_json(ARQUIVO_PONTOS)
        historico = carregar_json(ARQUIVO_HISTORICO)
        
        total = pontos.get(user_id, 0)
        semanal = sum(1 for v in historico.get(user_id, []) if v["timestamp"] >= (datetime.now().timestamp() - 7*24*60*60))
        mensal = sum(1 for v in historico.get(user_id, []) if v["timestamp"] >= (datetime.now().timestamp() - 30*24*60*60))
        
        # Posição no ranking
        rank_geral = get_ranking_geral()
        posicao = next((i+1 for i, (uid, _) in enumerate(rank_geral) if uid == user_id), None)
        
        embed = discord.Embed(
            title=f"👤 PERFIL FATALITY - {interaction.user.display_name}",
            color=COR_VERMELHO
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🏆 Vitórias Totais", value=f"**{total}**", inline=True)
        embed.add_field(name="📅 Semana", value=f"**{semanal}**", inline=True)
        embed.add_field(name="📆 Mês", value=f"**{mensal}**", inline=True)
        embed.add_field(name="🥇 Posição Ranking", value=f"**#{posicao}**" if posicao else "**Sem rank**", inline=True)
        embed.add_field(name="⚔️ Status", value="**Lenda da FATALITY**" if total >= 50 else "**Guerreiro**" if total >= 20 else "**Novato**", inline=True)
        embed.set_footer(text="FATALITY 20CC • Continue farmando")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================== COG RANKING ==================
class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def win(self, ctx, vencedor: discord.Member):
        """ADM dá vitória:!win @vencedor"""
        total = adicionar_vitoria(vencedor.id)
        
        embed = discord.Embed(
            title="🏆 VITÓRIA REGISTRADA!",
            description=f"**{vencedor.mention}** venceu a partida!\n\n**Pontos totais:** {total}\n**Status:** +1 WIN na conta",
            color=COR_VERMELHO
        )
        embed.set_footer(text="FATALITY 20CC • Use!rank pra ver o top 10")
        await ctx.send(embed=embed)
        
        # Apaga a thread se tiver numa
        if isinstance(ctx.channel, discord.Thread):
            await asyncio.sleep(3)
            await ctx.send("🔒 Fechando thread em 5 segundos...")
            await asyncio.sleep(5)
            try:
                await ctx.channel.delete()
            except:
                pass

    @commands.command()
    async def rank(self, ctx):
        """Mostra top 10 geral"""
        ranking = get_ranking_geral()[:10]
        if not ranking:
            return await ctx.send("❌ Ninguém pontuou ainda.")
        
        desc = ""
        medalhas = ["🥇", "🥈", "🥉"]
        for i, (user_id, pts) in enumerate(ranking):
            membro = ctx.guild.get_member(int(user_id))
            nome = membro.display_name if membro else "User saiu"
            emoji = medalhas[i] if i < 3 else f"**{i+1}º**"
            desc += f"{emoji} {nome} - **{pts}** vitória(s)\n"
        
        embed = discord.Embed(title="🏆 TOP 10 FATALITY - GERAL", description=desc, color=COR_VERMELHO)
        embed.set_footer(text="FATALITY 20CC • Use!painelranking pra ver semanal/mensal")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def painelranking(self, ctx):
        """Posta o painel de ranking com botão Meu Perfil"""
        
        # Ranking Geral
        rank_geral = get_ranking_geral()[:5]
        desc_geral = ""
        medalhas = ["🥇", "🥈", "🥉"]
        for i, (user_id, pts) in enumerate(rank_geral):
            membro = ctx.guild.get_member(int(user_id))
            nome = membro.display_name if membro else "User saiu"
            emoji = medalhas[i] if i < 3 else f"**{i+1}º**"
            desc_geral += f"{emoji} {nome} - **{pts}**\n"
        if not desc_geral:
            desc_geral = "Ninguém pontuou ainda"
        
        # Ranking Semanal
        rank_semanal = get_ranking_periodo(7)[:5]
        desc_semanal = ""
        for i, (user_id, pts) in enumerate(rank_semanal):
            membro = ctx.guild.get_member(int(user_id))
            nome = membro.display_name if membro else "User saiu"
            emoji = medalhas[i] if i < 3 else f"**{i+1}º**"
            desc_semanal += f"{emoji} {nome} - **{pts}**\n"
        if not desc_semanal:
            desc_semanal = "Ninguém pontuou essa semana"
        
        # Ranking Mensal
        rank_mensal = get_ranking_periodo(30)[:5]
        desc_mensal = ""
        for i, (user_id, pts) in enumerate(rank_mensal):
            membro = ctx.guild.get_member(int(user_id))
            nome = membro.display_name if membro else "User saiu"
            emoji = medalhas[i] if i < 3 else f"**{i+1}º**"
            desc_mensal += f"{emoji} {nome} - **{pts}**\n"
        if not desc_mensal:
            desc_mensal = "Ninguém pontuou esse mês"
        
        embed = discord.Embed(
            title="🏆 RANKING FATALITY 20CC",
            description="**Clique em Meu Perfil pra ver tuas stats**",
            color=COR_VERMELHO
        )
        embed.add_field(name="🥇 TOP 5 GERAL", value=desc_geral, inline=True)
        embed.add_field(name="📅 TOP 5 SEMANAL", value=desc_semanal, inline=True)
        embed.add_field(name="📆 TOP 5 MENSAL", value=desc_mensal, inline=True)
        embed.set_footer(text="FATALITY 20CC • Atualizado em tempo real")
        
        await ctx.send(embed=embed, view=ViewPainelRanking())
        await ctx.message.delete()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetranking(self, ctx, tipo=None):
        """Reseta ranking:!resetranking geral/semanal/mensal"""
        if tipo == "geral":
            salvar_json(ARQUIVO_PONTOS, {})
            salvar_json(ARQUIVO_HISTORICO, {})
            await ctx.send("✅ Ranking geral resetado!")
        elif tipo == "semanal":
            historico = carregar_json(ARQUIVO_HISTORICO)
            limite = datetime.now().timestamp() - (7*24*60*60)
            for uid in historico:
                historico[uid] = [v for v in historico[uid] if v["timestamp"] < limite]
            salvar_json(ARQUIVO_HISTORICO, historico)
            await ctx.send("✅ Ranking semanal resetado!")
        elif tipo == "mensal":
            historico = carregar_json(ARQUIVO_HISTORICO)
            limite = datetime.now().timestamp() - (30*24*60*60)
            for uid in historico:
                historico[uid] = [v for v in historico[uid] if v["timestamp"] < limite]
            salvar_json(ARQUIVO_HISTORICO, historico)
            await ctx.send("✅ Ranking mensal resetado!")
        else:
            await ctx.send("❌ Use: `!resetranking geral/semanal/mensal`")

async def setup(bot):
    await bot.add_cog(Ranking(bot))
