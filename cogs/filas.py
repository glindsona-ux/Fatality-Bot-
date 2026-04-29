import discord
from discord.ext import commands
from discord.ui import Button, View
from config import (
    COR_VERMELHO, IDS_CANAIS_MODALIDADES, TABELA_APOSTAS, VALORES_FILA,
    NOME_CARGO_MED, NOME_CARGO_STAFF
)
import json
import os
import asyncio
from datetime import datetime, timezone

ARQUIVO_FILAS = "filas.json"
ARQUIVO_PARTIDAS = "partidas.json"
ARQUIVO_NICKS = "nicks_ff.json"
ARQUIVO_FILA_MED = "fila_mediadores.json"
ARQUIVO_PIX_MED = "pix_mediadores.json"
ID_CANAL_PARTIDAS = 1494156477978509365 # CANAL #sua-partida-aqui

def carregar_json(arquivo):
    if not os.path.exists(arquivo):
        with open(arquivo, 'w') as f:
            json.dump({} if "fila_med" not in arquivo else [], f)
    with open(arquivo, 'r') as f:
        return json.load(f)

def salvar_json(arquivo, dados):
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=4)

# ================== SISTEMA DE NICK FF ==================
class NickFF(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def setnick(self, ctx, *, nick=None):
        if not nick:
            return await ctx.send("❌ Use: `!setnick SEU_NICK_DO_FF`", delete_after=10)
        nicks = carregar_json(ARQUIVO_NICKS)
        nicks[str(ctx.author.id)] = {"nick": nick, "data": str(datetime.now())}
        salvar_json(ARQUIVO_NICKS, nicks)
        await ctx.message.delete(delay=5)
        await ctx.send(f"✅ {ctx.author.mention} Nick `{nick}` salvo! Já pode jogar.", delete_after=10)

# ================== VIEW FILA ==================
class ViewFila(View):
    def __init__(self, modo, valor):
        self.modo = modo
        self.valor = valor
        super().__init__(timeout=None)
        self.children[0].custom_id = f"jogar_{modo}_{valor}_v2"
        self.children[1].custom_id = f"sair_{modo}_{valor}_v2"

    @discord.ui.button(label="JOGAR", style=discord.ButtonStyle.green) # VERDE = ENTRAR
    async def jogar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        # Anti mediador
        cargo_med = discord.utils.get(interaction.guild.roles, name=NOME_CARGO_MED)
        if cargo_med and cargo_med in interaction.user.roles:
            return await interaction.followup.send("❌ Mediadores não podem jogar. Use a fila de mediadores.", ephemeral=True)

        # Anti fake
        if (datetime.now(timezone.utc) - interaction.user.created_at).days < 7:
            return await interaction.followup.send("❌ Contas com menos de 7 dias não podem apostar. Anti-fake ativado.", ephemeral=True)

        # Verifica nick
        nicks = carregar_json(ARQUIVO_NICKS)
        if str(interaction.user.id) not in nicks:
            return await interaction.followup.send("❌ Cadastre seu nick com `!setnick SEU_NICK` antes de jogar.", ephemeral=True)

        filas = carregar_json(ARQUIVO_FILAS)
        msg_id = str(interaction.message.id)

        if msg_id not in filas:
            filas[msg_id] = {"jogadores": [], "valor": self.valor, "modo": self.modo}

        if interaction.user.id in filas[msg_id]["jogadores"]:
            return await interaction.followup.send("⚠️ Você já está nessa fila.", ephemeral=True)

        if len(filas[msg_id]["jogadores"]) >= 2:
            return await interaction.followup.send("❌ Fila lotada!", ephemeral=True)

        filas[msg_id]["jogadores"].append(interaction.user.id)
        salvar_json(ARQUIVO_FILAS, filas)
        await atualizar_embed_fila(interaction.message)

        if len(filas[msg_id]["jogadores"]) == 2:
            await criar_partida(interaction, msg_id)
        else:
            await interaction.followup.send("✅ Você entrou na fila!", ephemeral=True)

    @discord.ui.button(label="SAIR", style=discord.ButtonStyle.red) # VERMELHO = SAIR
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        filas = carregar_json(ARQUIVO_FILAS)
        msg_id = str(interaction.message.id)

        if msg_id in filas and interaction.user.id in filas[msg_id]["jogadores"]:
            filas[msg_id]["jogadores"].remove(interaction.user.id)
            salvar_json(ARQUIVO_FILAS, filas)
            await atualizar_embed_fila(interaction.message)
            return await interaction.followup.send("✅ Você saiu da fila.", ephemeral=True)
        else:
            return await interaction.followup.send("⚠️ Você não está nessa fila.", ephemeral=True)

async def atualizar_embed_fila(message):
    filas = carregar_json(ARQUIVO_FILAS)
    msg_id = str(message.id)
    dados = filas.get(msg_id, {"jogadores": [], "valor": 0, "modo": ""})

    jogadores = []
    for uid in dados["jogadores"]:
        membro = message.guild.get_member(uid)
        if membro:
            jogadores.append(f"👑 {membro.mention}")

    lista_capitaes = "\n".join(jogadores) if jogadores else "Aguardando capitães..."
    tabela = TABELA_APOSTAS.get(dados["valor"], {})
    qtd_jogadores = len(jogadores)

    if qtd_jogadores == 0:
        status = "🔴 Aguardando jogadores"
    elif qtd_jogadores == 1:
        status = "🟡 Aguardando oponente"
    else:
        status = "🟢 Lotou - Criando partida"

    desc = f"🏆 **Modo:** {dados['modo']}\n\n💰 **Aposta:** R$ {dados['valor']:.2f}\n"
    if tabela:
        desc += f"💵 **Cada paga:** R$ {tabela['paga']:.2f}\n🏆 **Prêmio vencedor:** R$ {tabela['premio']:.2f}\n"
    desc += f"\n👑 **Capitães na fila:** [ {qtd_jogadores}/2 ]\n{lista_capitaes}"

    embed = discord.Embed(
        title=f"{dados['modo']} | FATALITY APOSTAS 24H",
        color=COR_VERMELHO,
        description=desc
    )
    embed.set_footer(text=f"{status} | Taxa ADM: R$ 0,20 cada | FATALITY 20CC")
    await message.edit(embed=embed, view=ViewFila(modo=dados['modo'], valor=dados['valor']))

# ================== MODAL + BOTÕES NOVOS ==================
class ModalIDSenha(discord.ui.Modal, title='ID/SENHA DA PARTIDA'):
    id_sala = discord.ui.TextInput(label='ID DA SALA', placeholder='Ex: 123456', max_length=20)
    senha_sala = discord.ui.TextInput(label='SENHA DA SALA', placeholder='Ex: Fatality20CC', max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔐 DADOS DA PARTIDA • FATALITY 20CC",
            description="**Entrem na sala e se preparem!**",
            color=COR_VERMELHO
        )
        embed.add_field(name="🆔 ID", value=f"```{self.id_sala.value}```", inline=True)
        embed.add_field(name="🔑 SENHA", value=f"```{self.senha_sala.value}```", inline=True)
        embed.add_field(name="⚠️ AVISO", value="• Não vaza pra ninguém\n• Print obrigatório do resultado\n• Boa partida!", inline=False)
        embed.set_footer(text="FATALITY 20CC • Mediador: " + interaction.user.display_name)
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)

class BotaoIDSenha(Button):
    def __init__(self):
        super().__init__(label="ID/Senha", style=discord.ButtonStyle.blurple, emoji="🔐", custom_id="id_senha_fatality")

    async def callback(self, interaction: discord.Interaction):
        partidas = carregar_json(ARQUIVO_PARTIDAS)
        dados = partidas.get(str(interaction.channel.id))
        if not dados or interaction.user.id!= dados["mediador"]:
            return await interaction.response.send_message("❌ Só o mediador da partida pode enviar ID/Senha.", ephemeral=True)
        await interaction.response.send_modal(ModalIDSenha())

class BotaoCancelar(Button):
    def __init__(self):
        super().__init__(label="Cancelar Partida", style=discord.ButtonStyle.red, emoji="❌", custom_id="cancelar_partida_fatality")

    async def callback(self, interaction: discord.Interaction):
        partidas = carregar_json(ARQUIVO_PARTIDAS)
        dados = partidas.get(str(interaction.channel.id))
        if not dados:
            return await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)

        if interaction.user.id not in [dados["cap1"], dados["cap2"], dados["mediador"]]:
            return await interaction.response.send_message("❌ Só players ou mediador podem cancelar.", ephemeral=True)

        await interaction.response.send_message("❌ Partida cancelada por " + interaction.user.mention + ". Canal será deletado em 10s.", ephemeral=False)
        await asyncio.sleep(10)
        await interaction.channel.delete()

class ViewPartidaConfirmada(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BotaoCancelar())
        self.add_item(BotaoIDSenha())

# ================== CRIAR PARTIDA + THREAD CORRIGIDA ==================
async def criar_partida(interaction, msg_id):
    filas = carregar_json(ARQUIVO_FILAS)
    fila_med = carregar_json(ARQUIVO_FILA_MED)

    if not fila_med:
        await interaction.followup.send("❌ **SEM MEDIADORES!** Nenhum mediador na fila. Chame um /MEDIADOR.", ephemeral=False)
        return

    dados = filas[msg_id]
    cap1_id, cap2_id = dados["jogadores"]
    med_id = fila_med.pop(0)
    salvar_json(ARQUIVO_FILA_MED, fila_med)

    cap1 = interaction.guild.get_member(cap1_id)
    cap2 = interaction.guild.get_member(cap2_id)
    med = interaction.guild.get_member(med_id)

    # CRIA THREAD NO #sua-partida-aqui SEMPRE
    canal_partidas = interaction.guild.get_channel(ID_CANAL_PARTIDAS)
    if not canal_partidas:
        return await interaction.followup.send("❌ Canal #sua-partida-aqui não encontrado. Configura o ID.", ephemeral=True)

    thread = await canal_partidas.create_thread(
        name=f"{dados['modo']} | {cap1.display_name} vs {cap2.display_name}",
        type=discord.ChannelType.private_thread,
        auto_archive_duration=1440
    )

    partidas = carregar_json(ARQUIVO_PARTIDAS)
    partidas[str(thread.id)] = {
        "cap1": cap1_id, "cap2": cap2_id, "mediador": med_id,
        "valor": dados["valor"], "modo": dados["modo"],
        "confirmados": [], "canal_fila": interaction.channel.id
    }
    salvar_json(ARQUIVO_PARTIDAS, partidas)

    await thread.add_user(cap1)
    await thread.add_user(cap2)
    await thread.add_user(med)

    # PRIMEIRO MANDA SÓ A CONFIRMAÇÃO - ORDEM CORRIGIDA
    embed = discord.Embed(
        title="⚔️ PARTIDA CRIADA - CONFIRMAÇÃO OBRIGATÓRIA",
        description=f"**Modo:** {dados['modo']}\n**Valor:** R$ {dados['valor']:.2f}\n\n👑 **Capitães:**\n{cap1.mention} vs {cap2.mention}\n\n👨‍⚖️ **Mediador:** {med.mention}\n\n⚠️ **AMBOS OS CAPITÃES PRECISAM CONFIRMAR PARA LIBERAR O PIX!**",
        color=COR_VERMELHO
    )
    embed.set_footer(text="Clique em CONFIRMAR PARTIDA abaixo")
    view_confirmar = ViewConfirmar(cap1_id, cap2_id, dados["valor"], med_id)
    await thread.send(embed=embed, view=view_confirmar)

    await interaction.followup.send(f"✅ Partida criada: {thread.mention}", ephemeral=False)

    # Reseta a fila pra 0/2 em vez de deletar ← CORRIGIDO AQUI
    filas[msg_id]["jogadores"] = []
    salvar_json(ARQUIVO_FILAS, filas)
    await atualizar_embed_fila(interaction.message)

class ViewConfirmar(View):
    def __init__(self, cap1_id, cap2_id, valor, med_id):
        super().__init__(timeout=None)
        self.cap1_id = cap1_id
        self.cap2_id = cap2_id
        self.valor = valor
        self.med_id = med_id

    @discord.ui.button(label="✅ CONFIRMAR PARTIDA", style=discord.ButtonStyle.green, custom_id="confirmar_cap_v2")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        partidas = carregar_json(ARQUIVO_PARTIDAS)
        thread_id = str(interaction.channel.id)
        if thread_id not in partidas:
            return await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)

        dados = partidas[thread_id]
        if interaction.user.id not in [self.cap1_id, self.cap2_id]:
            return await interaction.response.send_message("❌ Só os capitães podem confirmar.", ephemeral=True)

        if "confirmados" not in dados:
            dados["confirmados"] = []

        if interaction.user.id in dados["confirmados"]:
            return await interaction.response.send_message("⚠️ Você já confirmou.", ephemeral=True)

        dados["confirmados"].append(interaction.user.id)
        salvar_json(ARQUIVO_PARTIDAS, partidas)

        if len(dados["confirmados"]) == 2:
            # AMBOS CONFIRMARAM = LIBERA PIX + BOTÕES NOVOS
            await interaction.response.edit_message(content="✅ **Ambos confirmaram!** PIX liberado abaixo.", view=None)

            # MANDA O PIX SÓ AGORA
            med = interaction.guild.get_member(self.med_id)
            pix_data = carregar_json(ARQUIVO_PIX_MED)
            pix_med = pix_data.get(str(self.med_id))
            paga_cada = TABELA_APOSTAS[self.valor]["paga"]
            premio = TABELA_APOSTAS[self.valor]["premio"]

            embed_pix = discord.Embed(
                title="💰 PAGAMENTO LIBERADO • FATALITY 20CC",
                color=COR_VERMELHO,
                description=f"**💵 Cada capitão paga:** R$ {paga_cada:.2f}\n**🏆 Prêmio pro vencedor:** R$ {premio:.2f}\n**⚠️ Taxa ADM:** R$ 0,20 de cada\n\n---\n**PIX DO MEDIADOR:**"
            )
            if pix_med:
                embed_pix.add_field(name="👤 Nome", value=pix_med["nome"], inline=True)
                embed_pix.add_field(name="🏦 Banco", value=pix_med["banco"], inline=True)
                embed_pix.add_field(name="🔑 Chave PIX", value=f"`{pix_med['chave']}`", inline=False)
            else:
                embed_pix.add_field(name="⚠️ ATENÇÃO", value=f"{med.mention} ainda não cadastrou o PIX!", inline=False)

            await interaction.channel.send(embed=embed_pix, view=ViewPartidaConfirmada())
        else:
            await interaction.response.send_message(f"✅ {interaction.user.mention} confirmou! Aguardando o outro capitão...", ephemeral=False)

def criar_views_filas():
    """Cria todas as views imortais pras 11 filas"""
    views = []
    for modo in IDS_CANAIS_MODALIDADES.keys():
        for valor in VALORES_FILA:
            views.append(ViewFila(modo=modo, valor=valor))
    return views

class Filas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setupfilas(self, ctx):
        """Posta filas em todos os 11 canais - ORDEM 100 → 0,50"""
        await ctx.message.delete()

        for modo, canal_id in IDS_CANAIS_MODALIDADES.items():
            canal = self.bot.get_channel(canal_id)
            if not canal:
                continue

            # ORDEM DECRESCENTE: 100, 50, 20, 10... 0,50
            for valor_fila in sorted(VALORES_FILA, reverse=True):
                dados_tabela = TABELA_APOSTAS[valor_fila]
                embed = discord.Embed(
                    title=f"{modo} | FATALITY APOSTAS 24H",
                    color=COR_VERMELHO,
                    description=f"🏆 **Modo:** {modo}\n\n💰 **Aposta:** R$ {valor_fila:.2f}\n💵 **Cada paga:** R$ {dados_tabela['paga']:.2f}\n🏆 **Prêmio vencedor:** R$ {dados_tabela['premio']:.2f}\n\n👑 **Capitães na fila:** [ 0/2 ]\nAguardando capitães..."
                )
                embed.set_footer(text="🔴 Aguardando jogadores | Taxa ADM: R$ 0,20 cada | FATALITY 20CC")
                msg = await canal.send(embed=embed, view=ViewFila(modo=modo, valor=valor_fila))

            filas = carregar_json(ARQUIVO_FILAS)
            filas[str(msg.id)] = {
                "jogadores": [], "valor": valor_fila, "modo": modo,
                "canal_modalidade": canal_id
            }
            salvar_json(ARQUIVO_FILAS, filas)
            await asyncio.sleep(0.3)

            await ctx.send("✅ Filas criadas em todos os 11 canais! Ordem: 100 → 0,50", delete_after=10)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def limparfilas(self, ctx):
        """Limpa filas do canal atual"""
        filas = carregar_json(ARQUIVO_FILAS)
        filas_filtradas = {}
        deletadas = 0

        for msg_id in list(filas.keys()):
            try:
                canal_id = filas[msg_id].get("canal_modalidade")
                if canal_id == ctx.channel.id:
                    canal = self.bot.get_channel(canal_id)
                    if canal:
                        msg = await canal.fetch_message(int(msg_id))
                        await msg.delete()
                    deletadas += 1
                else:
                    filas_filtradas[msg_id] = filas[msg_id]
            except:
                pass

        salvar_json(ARQUIVO_FILAS, filas_filtradas)

        if deletadas > 0:
            await ctx.send(f"✅ {deletadas} fila(s) deste canal foram limpas!", delete_after=10)
        else:
            await ctx.send("⚠️ Nenhuma fila ativa neste canal.", delete_after=10)

async def setup(bot):
    await bot.add_cog(NickFF(bot))
    await bot.add_cog(Filas(bot))
