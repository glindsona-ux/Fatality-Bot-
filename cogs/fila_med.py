import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
from config import COR_VERMELHO, ID_CANAL_FILA_MED, ID_CANAL_PIX_MED, NOME_CARGO_MED
import json
import os

ARQUIVO_FILA_MED = "fila_mediadores.json"
ARQUIVO_PIX_MED = "pix_mediadores.json"

def carregar_json(arquivo):
    if not os.path.exists(arquivo):
        with open(arquivo, 'w') as f:
            json.dump([] if "fila" in arquivo else {}, f)
    with open(arquivo, 'r') as f:
        return json.load(f)

def salvar_json(arquivo, dados):
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=4)

# ================== POPUP PIX ==================
class ModalConfiPix(Modal, title="💳 Configurar PIX - Mediador FATALITY"):
    def __init__(self):
        super().__init__()

    nome_completo = TextInput(
        label="Nome Completo",
        placeholder="Ex: Glindson Silva Santos",
        max_length=50,
        required=True
    )
    
    banco = TextInput(
        label="Banco",
        placeholder="Ex: Nubank, Inter, Bradesco, Caixa",
        max_length=30,
        required=True
    )
    
    chave_pix = TextInput(
        label="Chave PIX",
        placeholder="CPF, Email, Telefone ou Aleatória",
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        pix_data = carregar_json(ARQUIVO_PIX_MED)
        user_id = str(interaction.user.id)
        
        pix_data[user_id] = {
            "nome": str(self.nome_completo.value),
            "banco": str(self.banco.value),
            "chave": str(self.chave_pix.value),
            "discord": str(interaction.user)
        }
        salvar_json(ARQUIVO_PIX_MED, pix_data)
        
        embed = discord.Embed(
            title="✅ PIX CONFIGURADO COM SUCESSO!",
            description=f"**Nome:** {self.nome_completo.value}\n**Banco:** {self.banco.value}\n**Chave:** ||{self.chave_pix.value}||\n\n**Seu PIX vai aparecer automático nas partidas.**\n\n⚠️ **SEM PIX = SEM MEDIAÇÃO**",
            color=COR_VERMELHO
        )
        embed.set_footer(text="FATALIDADE 20CC • Pode alterar quando quiser")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ViewConfiPix(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Configurar meu PIX", 
        style=discord.ButtonStyle.green, # VERDE = ENTRAR/CONFIRMAR
        emoji="💳", 
        custom_id="botao_confi_pix_v2"
    )
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargo_med = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_MED)
        if not cargo_med or cargo_med not in interaction.user.roles:
            return await interaction.response.send_message("❌ Só /MEDIADOR pode configurar PIX.", ephemeral=True)
        
        await interaction.response.send_modal(ModalConfiPix())

# ================== FILA MEDIADORES ==================
class ViewMediadores(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ENTRAR NA FILA", 
        style=discord.ButtonStyle.green, # VERDE = ENTRAR
        custom_id="entrar_fila_med_v2"
    )
    async def entrar_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargo_med = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_MED)
        if not cargo_med or cargo_med not in interaction.user.roles:
            return await interaction.response.send_message("❌ Você não tem o cargo /MEDIADOR.", ephemeral=True)
        
        # Verifica se tem PIX cadastrado
        pix_data = carregar_json(ARQUIVO_PIX_MED)
        if str(interaction.user.id) not in pix_data:
            return await interaction.response.send_message("❌ **Cadastra teu PIX primeiro!**\nVai no <#{}> e clica em **Configurar meu PIX**".format(ID_CANAL_PIX_MED), ephemeral=True)
        
        fila = carregar_json(ARQUIVO_FILA_MED)
        if interaction.user.id in fila:
            return await interaction.response.send_message("⚠️ Você já está na fila.", ephemeral=True)
        
        fila.append(interaction.user.id)
        salvar_json(ARQUIVO_FILA_MED, fila)
        await atualizar_embed_fila_med(interaction.message)
        await interaction.response.send_message("✅ Você entrou na fila de mediadores!", ephemeral=True)

    @discord.ui.button(
        label="SAIR DA FILA", 
        style=discord.ButtonStyle.red, # VERMELHO = SAIR
        custom_id="sair_fila_med_v2"
    )
    async def sair_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        fila = carregar_json(ARQUIVO_FILA_MED)
        if interaction.user.id not in fila:
            return await interaction.response.send_message("⚠️ Você não está na fila.", ephemeral=True)
        
        fila.remove(interaction.user.id)
        salvar_json(ARQUIVO_FILA_MED, fila)
        await atualizar_embed_fila_med(interaction.message)
        await interaction.response.send_message("✅ Você saiu da fila!", ephemeral=True)

async def atualizar_embed_fila_med(message):
    fila_ids = carregar_json(ARQUIVO_FILA_MED)
    membros = []
    for uid in fila_ids:
        membro = message.guild.get_member(uid)
        if membro:
            membros.append(f"👑 {membro.mention}")
    
    lista = "\n".join(membros) if membros else "Nenhum mediador na fila."
    
    embed = discord.Embed(
        title="👑 FILA DE MEDIADORES ATIVOS", 
        description=f"**Mediadores disponíveis para mediar apostas:**\n\n{lista}", 
        color=COR_VERMELHO
    )
    embed.set_footer(text=f"Total: {len(membros)} mediadores • FATALITY 20CC")
    embed.add_field(
        name="⚠️ IMPORTANTE", 
        value="Só entra na fila quem tem PIX cadastrado no <#{}>".format(ID_CANAL_PIX_MED), 
        inline=False
    )
    await message.edit(embed=embed, view=ViewMediadores())

class FilaMed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setupfilamed(self, ctx):
        canal = self.bot.get_channel(ID_CANAL_FILA_MED)
        if not canal:
            return await ctx.send("❌ ID_CANAL_FILA_MED inválido.", delete_after=10)
        
        embed = discord.Embed(
            title="👑 FILA DE MEDIADORES ATIVOS", 
            description="**Mediadores disponíveis para mediar apostas:**\n\nNenhum mediador na fila.", 
            color=COR_VERMELHO
        )
        embed.set_footer(text="Total: 0 mediadores • FATALITY 20CC")
        embed.add_field(
            name="⚠️ IMPORTANTE", 
            value="Só entra na fila quem tem PIX cadastrado no <#{}>".format(ID_CANAL_PIX_MED), 
            inline=False
        )
        await canal.send(embed=embed, view=ViewMediadores())
        salvar_json(ARQUIVO_FILA_MED, [])
        await ctx.send("✅ Painel fila mediadores postado.", delete_after=5)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setuppix(self, ctx):
        canal = self.bot.get_channel(ID_CANAL_PIX_MED)
        if not canal:
            return await ctx.send("❌ ID_CANAL_PIX_MED inválido.", delete_after=10)
        
        embed = discord.Embed(
            title="💀 CONFIGURAÇÃO DE PIX - MEDIADORES FATALITY",
            description="**PASSO A PASSO RÁPIDO:**\n\n**1.** Clique no botão verde abaixo\n**2.** Preencha: Nome Completo | Banco | Chave PIX\n**3.** Pronto.\n\n**Bot salva seus dados. Seu PIX aparece automático nas partidas.**\n\n**REGRAS:**\n✅ **Vale:** CPF, CNPJ, Email, Telefone, Chave aleatória\n❌ **Não vale:** Campo vazio, PIX de outro\n\n**⚠️ SEM PIX = SEM MEDIAÇÃO**\n\nDúvida? 🤝 Abre ticket",
            color=COR_VERMELHO
        )
        embed.set_footer(text="FATALITY 20CC • 24H")
        
        await canal.send(embed=embed, view=ViewConfiPix())
        await ctx.send("✅ Painel configurar PIX postado.", delete_after=5)

    @commands.command()
    async def verpix(self, ctx):
        """Mediador vê o próprio PIX cadastrado"""
        pix_data = carregar_json(ARQUIVO_PIX_MED)
        user_id = str(ctx.author.id)
        
        if user_id not in pix_data:
            return await ctx.send("❌ Você não cadastrou seu PIX ainda. Use o painel no <#{}>".format(ID_CANAL_PIX_MED), ephemeral=True)
        
        dados = pix_data[user_id]
        embed = discord.Embed(
            title="💳 Seu PIX Cadastrado",
            description=f"**Nome:** {dados['nome']}\n**Banco:** {dados['banco']}\n**Chave:** ||{dados['chave']}||",
            color=COR_VERMELHO
        )
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(FilaMed(bot))
