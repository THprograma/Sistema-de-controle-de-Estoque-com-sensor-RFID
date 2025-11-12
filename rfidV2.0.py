
import serial
import time
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import scrolledtext
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# =====================================================
# BANCO (já existe, não será modificado aqui)
# =====================================================
def conectar_banco():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="db_rfid"
        )
    except Error as e:
        print(f"[DB] Erro ao conectar: {e}")
        return None

def buscar_ferramenta_por_tag(codigo_tag):
    conn = conectar_banco()
    if not conn:
        return None, None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT f.id_ferramentas, f.nome
            FROM tb_rfid_tags t
            JOIN tb_ferramentas f ON t.id_ferramenta = f.id_ferramentas
            WHERE t.codigo_tag = %s
            LIMIT 1
        """, (codigo_tag,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        if res:
            return res[0], res[1]
        return None, None
    except Error as e:
        print(f"[DB] Erro buscar_ferramenta_por_tag: {e}")
        return None, None

def registrar_movimentacao(id_ferramenta, local, observacao=None, id_usuario=None):
    conn = conectar_banco()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tb_movimentacoes (id_usuario, id_ferramentas, data_retirada, data_devolucao, observacao)
            VALUES (%s, %s, NOW(), NOW(), %s)
        """, (id_usuario or 1, id_ferramenta, observacao or f"Leitura de {local}"))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Error as e:
        print(f"[DB] Erro registrar_movimentacao: {e}")
        return False

def salvar_tag_no_banco(nome, codigo):
    conn = conectar_banco()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO tb_ferramentas (nome) VALUES (%s)", (nome,))
        id_ferramenta = cur.lastrowid
        cur.execute("INSERT INTO tb_rfid_tags (codigo_tag, id_ferramenta) VALUES (%s, %s)", (codigo, id_ferramenta))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Error as e:
        print(f"[DB] Erro ao salvar TAG: {e}")
        return False


# =====================================================
# VARIÁVEIS GLOBAIS
# =====================================================
porta1 = "COM5"
porta2 = "COM6"
baud = 115200
TAG_ALVO = "10000000000000000000000A"
NOME_TAG = "Chave de Fenda"
INTERVALO_EXIBICAO = 5.0

running = [False]
last_display = {"porta1": 0.0, "porta2": 0.0}
pending = {"porta1": False, "porta2": False}
pending_local = {"porta1": None, "porta2": None}
ultimo_registrado = {"Sala de Ferramentas": None, "Sala dos Tornos": None}

TAGS_CADASTRADAS = []
USUARIOS = []  # lista temporária de usuários cadastrados
USUARIO_ATUAL = [None]


# =====================================================
# FUNÇÕES DE LOGIN E CADASTRO
# =====================================================
def mostrar_login():
    for f in frame_container.winfo_children():
        f.pack_forget()
    frame_login.pack(fill="both", expand=True)

def mostrar_cadastro_usuario():
    frame_login.pack_forget()
    frame_cadastro_usuario.pack(fill="both", expand=True)

def registrar_usuario():
    nome = entrada_nome_user.get().strip()
    usuario = entrada_usuario_user.get().strip()
    senha = entrada_senha_user.get().strip()

    if not nome or not usuario or not senha:
        label_status_cadastro_user.configure(text="Preencha todos os campos!", text_color="red")
        return

    conn = conectar_banco()
    if not conn:
        label_status_cadastro_user.configure(text="Erro ao conectar com o banco!", text_color="red")
        return

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id_usuario FROM tb_usuario WHERE matricula = %s", (usuario,))
        if cur.fetchone():
            label_status_cadastro_user.configure(text="Usuário já existe!", text_color="red")
            cur.close()
            conn.close()
            return

        # Insere o novo usuário
        cur.execute("""
            INSERT INTO tb_usuario (nome, cargo, matricula, senha)
            VALUES (%s, %s, %s, %s)
        """, (nome, "Operador", usuario, senha))
        conn.commit()

        # Recupera os dados recém-inseridos
        cur.execute("SELECT * FROM tb_usuario WHERE matricula = %s", (usuario,))
        novo_usuario = cur.fetchone()

        cur.close()
        conn.close()

        # Define como usuário logado e vai direto ao menu
        USUARIO_ATUAL[0] = novo_usuario
        mostrar_menu_inicial()

    except Error as e:
        print(f"[DB] Erro registrar_usuario: {e}")
        label_status_cadastro_user.configure(text="Erro ao salvar no banco!", text_color="red")


def login_usuario():
    usuario = entrada_usuario_login.get().strip()
    senha = entrada_senha_login.get().strip()

    if not usuario or not senha:
        label_status_login.configure(text="Preencha todos os campos!", text_color="red")
        return

    conn = conectar_banco()
    if not conn:
        label_status_login.configure(text="Erro ao conectar com o banco!", text_color="red")
        return

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM tb_usuario WHERE matricula = %s AND senha = %s", (usuario, senha))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            USUARIO_ATUAL[0] = user
            frame_login.pack_forget()
            frame_inicial.pack(fill="both", expand=True)
        else:
            label_status_login.configure(text="Usuário ou senha incorretos!", text_color="red")

    except Error as e:
        print(f"[DB] Erro login_usuario: {e}")
        label_status_login.configure(text="Erro ao consultar banco!", text_color="red")


# =====================================================
# INTERFACE INICIAL (LOGIN)
# =====================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

janela_inicial = ctk.CTk()
janela_inicial.attributes('-fullscreen', True)
janela_inicial.title("Sistema RFID com Login")

frame_container = ctk.CTkFrame(janela_inicial)
frame_container.pack(fill="both", expand=True)

# TELA DE LOGIN
frame_login = ctk.CTkFrame(frame_container)

titulo_login = ctk.CTkLabel(frame_login, text="Login de Usuário", font=("Arial", 38, "bold"))
titulo_login.pack(pady=60)

entrada_usuario_login = ctk.CTkEntry(frame_login, placeholder_text="Usuário", width=400, height=40, font=("Arial", 16))
entrada_usuario_login.pack(pady=10)

entrada_senha_login = ctk.CTkEntry(frame_login, placeholder_text="Senha", show="*", width=400, height=40, font=("Arial", 16))
entrada_senha_login.pack(pady=10)

botao_login = ctk.CTkButton(frame_login, text="Entrar", command=login_usuario, width=200, height=45, fg_color="#27ae60", hover_color="#219150")
botao_login.pack(pady=15)

botao_ir_cadastro = ctk.CTkButton(frame_login, text="Criar nova conta", command=mostrar_cadastro_usuario, width=200, height=40, fg_color="#2980b9", hover_color="#1f5f8a")
botao_ir_cadastro.pack(pady=10)

label_status_login = ctk.CTkLabel(frame_login, text="", font=("Arial", 16))
label_status_login.pack(pady=10)

# TELA DE CADASTRO DE USUÁRIO
frame_cadastro_usuario = ctk.CTkFrame(frame_container)

titulo_cadastro_user = ctk.CTkLabel(frame_cadastro_usuario, text="Cadastro de Novo Usuário", font=("Arial", 32, "bold"))
titulo_cadastro_user.pack(pady=40)

entrada_nome_user = ctk.CTkEntry(frame_cadastro_usuario, placeholder_text="Nome Completo", width=400, height=40, font=("Arial", 16))
entrada_nome_user.pack(pady=10)

entrada_usuario_user = ctk.CTkEntry(frame_cadastro_usuario, placeholder_text="Usuário", width=400, height=40, font=("Arial", 16))
entrada_usuario_user.pack(pady=10)

entrada_senha_user = ctk.CTkEntry(frame_cadastro_usuario, placeholder_text="Senha", show="*", width=400, height=40, font=("Arial", 16))
entrada_senha_user.pack(pady=10)

botao_registrar_user = ctk.CTkButton(frame_cadastro_usuario, text="Registrar", command=registrar_usuario, width=200, height=45, fg_color="#27ae60", hover_color="#219150")
botao_registrar_user.pack(pady=15)

botao_voltar_login = ctk.CTkButton(frame_cadastro_usuario, text="Voltar ao Login", command=mostrar_login, width=200, height=45, fg_color="#c0392b", hover_color="#992d22")
botao_voltar_login.pack(pady=15)

label_status_cadastro_user = ctk.CTkLabel(frame_cadastro_usuario, text="", font=("Arial", 16))
label_status_cadastro_user.pack(pady=10)

# =====================================================
# TELA INICIAL (MENU APÓS LOGIN)
# =====================================================
frame_inicial = ctk.CTkFrame(frame_container)

titulo_inicial = ctk.CTkLabel(frame_inicial, text="Bem-vindo ao Sistema RFID", font=("Arial", 38, "bold"))
titulo_inicial.pack(pady=60)

label_usuario = ctk.CTkLabel(frame_inicial, text="", font=("Arial", 20))
label_usuario.pack(pady=10)

def atualizar_usuario_logado():
    if USUARIO_ATUAL[0]:
        label_usuario.configure(text=f"Usuário logado: {USUARIO_ATUAL[0]['nome']} ({USUARIO_ATUAL[0]['matricula']})")

# --- Botões principais ---
botoes_frame = ctk.CTkFrame(frame_inicial)
botoes_frame.pack(pady=40)

botao_cadastro_tag = ctk.CTkButton(
    botoes_frame, text="Cadastro de TAGs", width=250, height=50,
    command=lambda: mostrar_cadastro()
)
botao_cadastro_tag.grid(row=0, column=0, padx=20, pady=10)

botao_leitura = ctk.CTkButton(
    botoes_frame, text="Leitura RFID", width=250, height=50,
    command=lambda: mostrar_leitura()
)
botao_leitura.grid(row=0, column=1, padx=20, pady=10)

botao_sair = ctk.CTkButton(
    frame_inicial, text="Sair", width=200, height=45,
    fg_color="#c0392b", hover_color="#992d22",
    command=mostrar_login
)
botao_sair.pack(pady=20)

def mostrar_leitura():
    for f in frame_container.winfo_children():
        f.pack_forget()
    frame_leitura.pack(fill="both", expand=True)

# =====================================================
# TELA DE CADASTRO DE TAGS (COM LEITURA AUTOMÁTICA)
# =====================================================
frame_cadastro = ctk.CTkFrame(frame_container)

label_cadastro = ctk.CTkLabel(frame_cadastro, text="Cadastro de TAGs", font=("Arial", 32, "bold"))
label_cadastro.pack(pady=40)

entrada_nome_tag = ctk.CTkEntry(frame_cadastro, placeholder_text="Nome da Ferramenta", width=400, height=40)
entrada_nome_tag.pack(pady=10)

entrada_codigo_tag = ctk.CTkEntry(frame_cadastro, placeholder_text="Código da TAG", width=400, height=40)
entrada_codigo_tag.pack(pady=10)

status_cadastro = ctk.CTkLabel(frame_cadastro, text="", font=("Arial", 16))
status_cadastro.pack(pady=10)

def preencher_codigo_detectado(codigo):
    entrada_codigo_tag.delete(0, tk.END)
    entrada_codigo_tag.insert(0, codigo)
    status_cadastro.configure(text=f"TAG detectada: {codigo}", text_color="lightgreen")

capturando_tag = [False]
thread_leitura_tag = [None]

def normalizar_tag(raw):
    return "".join(ch for ch in raw if ch.isalnum()).upper()

def ler_tag_cadastro():
    try:
        ser = serial.Serial(porta1, baud, timeout=0.1)
    except Exception as e:
        print(f"[ERRO SERIAL] {e}")
        return

    while capturando_tag[0]:
        try:
            if ser.in_waiting > 0:
                raw = ser.readline().decode(errors="ignore").strip()
                codigo = normalizar_tag(raw)
                if len(codigo) > 5:
                    frame_cadastro.after(0, preencher_codigo_detectado, codigo)
            time.sleep(0.1)
        except Exception:
            time.sleep(0.05)
    ser.close()

def iniciar_leitura_tag():
    if not capturando_tag[0]:
        capturando_tag[0] = True
        thread_leitura_tag[0] = threading.Thread(target=ler_tag_cadastro, daemon=True)
        thread_leitura_tag[0].start()

def parar_leitura_tag():
    capturando_tag[0] = False
    if thread_leitura_tag[0]:
        thread_leitura_tag[0].join(timeout=0.5)

def salvar_tag():
    nome = entrada_nome_tag.get().strip()
    codigo = entrada_codigo_tag.get().strip()

    if not nome or not codigo:
        status_cadastro.configure(text="Preencha todos os campos!", text_color="red")
        return

    if salvar_tag_no_banco(nome, codigo):
        status_cadastro.configure(text="TAG cadastrada com sucesso!", text_color="lightgreen")
        entrada_nome_tag.delete(0, tk.END)
        entrada_codigo_tag.delete(0, tk.END)
    else:
        status_cadastro.configure(text="TAG já cadastrada!", text_color="red")

botao_salvar_tag = ctk.CTkButton(frame_cadastro, text="Salvar TAG", command=salvar_tag, width=200, height=45, fg_color="#27ae60", hover_color="#219150")
botao_salvar_tag.pack(pady=15)

botao_voltar_menu = ctk.CTkButton(frame_cadastro, text="Voltar ao Menu", command=lambda: [parar_leitura_tag(), mostrar_menu_inicial()], width=200, height=45, fg_color="#c0392b", hover_color="#992d22")
botao_voltar_menu.pack(pady=15)
# =====================================================
# TELA DE LEITURA RFID (MONITORAMENTO AO VIVO)
# =====================================================
frame_leitura = ctk.CTkFrame(frame_container)

titulo_leitura = ctk.CTkLabel(frame_leitura, text="Leitura de Tags RFID", font=("Arial", 32, "bold"))
titulo_leitura.pack(pady=40)

texto_leitura = scrolledtext.ScrolledText(frame_leitura, width=100, height=20, font=("Consolas", 12))
texto_leitura.pack(pady=10)

status_leitura = ctk.CTkLabel(frame_leitura, text="", font=("Arial", 16))
status_leitura.pack(pady=10)

capturando_leitura = [False]
threads_leitura = []

def registrar_leitura(porta, codigo):
    id_ferramenta, nome = buscar_ferramenta_por_tag(codigo)
    local = "Sala de Ferramentas" if porta == porta1 else "Sala dos Tornos"

    if id_ferramenta:
        registrar_movimentacao(id_ferramenta, local)
        msg = f"[{datetime.now().strftime('%H:%M:%S')}] {local} -> {nome} ({codigo}) registrado.\n"
    else:
        msg = f"[{datetime.now().strftime('%H:%M:%S')}] {local} -> TAG desconhecida ({codigo}).\n"

    texto_leitura.insert(tk.END, msg)
    texto_leitura.see(tk.END)

def ler_porta_serial(porta):
    try:
        ser = serial.Serial(porta, baud, timeout=0.1)
    except Exception as e:
        texto_leitura.insert(tk.END, f"[ERRO] Falha ao abrir {porta}: {e}\n")
        return

    while capturando_leitura[0]:
        try:
            if ser.in_waiting > 0:
                raw = ser.readline().decode(errors="ignore").strip()
                codigo = normalizar_tag(raw)
                if len(codigo) > 5:
                    frame_leitura.after(0, registrar_leitura, porta, codigo)
            time.sleep(0.1)
        except Exception:
            time.sleep(0.05)
    ser.close()

def iniciar_leitura_rfid():
    capturando_leitura[0] = True
    texto_leitura.delete(1.0, tk.END)
    status_leitura.configure(text="Leitura em andamento...", text_color="lightgreen")
    threads_leitura.clear()
    for porta in [porta1, porta2]:
        t = threading.Thread(target=ler_porta_serial, args=(porta,), daemon=True)
        t.start()
        threads_leitura.append(t)

def parar_leitura_rfid():
    capturando_leitura[0] = False
    for t in threads_leitura:
        t.join(timeout=0.5)
    status_leitura.configure(text="Leitura encerrada.", text_color="red")

botao_iniciar_leitura = ctk.CTkButton(frame_leitura, text="Iniciar Leitura", command=iniciar_leitura_rfid, width=200, height=45, fg_color="#27ae60", hover_color="#219150")
botao_iniciar_leitura.pack(pady=10)

botao_parar_leitura = ctk.CTkButton(frame_leitura, text="Parar Leitura", command=parar_leitura_rfid, width=200, height=45, fg_color="#e67e22", hover_color="#ca6f1e")
botao_parar_leitura.pack(pady=10)

botao_voltar_menu_leitura = ctk.CTkButton(frame_leitura, text="Voltar ao Menu", command=lambda: [parar_leitura_rfid(), mostrar_menu_inicial()], width=200, height=45, fg_color="#c0392b", hover_color="#992d22")
botao_voltar_menu_leitura.pack(pady=15)

# =====================================================
# FUNÇÕES DE TROCA DE TELA
# =====================================================
def mostrar_menu_inicial():
    for f in frame_container.winfo_children():
        f.pack_forget()
    frame_inicial.pack(fill="both", expand=True)
    atualizar_usuario_logado()

def mostrar_cadastro():
    for f in frame_container.winfo_children():
        f.pack_forget()
    frame_cadastro.pack(fill="both", expand=True)
    iniciar_leitura_tag()

# =====================================================
# INÍCIO DO PROGRAMA
# =====================================================
mostrar_login()
janela_inicial.mainloop()