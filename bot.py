import os
import sqlite3
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "8733783250:AAEKLrNpzEPvItVTpJRSTeLv3QDUOXdS0Xg"
ADMIN_ID = 8179362627
DB_PATH = "bot_data.db"

PRODUCTOS = {
    # PROXY
    "📅 Proxy 1 día - $1.50": {
        "precio": 1.50,
        "archivo": "proxy_1dia.txt",
        "nombre": "PROXY 1 DÍA",
        "validez": "1 día",
        "categoria": "Proxy",
    },
    "📆 Proxy 7 días - $5.00": {
        "precio": 5.00,
        "archivo": "proxy_7dias.txt",
        "nombre": "PROXY 7 DÍAS",
        "validez": "7 días",
        "categoria": "Proxy",
    },
    "🗓 Proxy 15 días - $8.00": {
        "precio": 8.00,
        "archivo": "proxy_15dias.txt",
        "nombre": "PROXY 15 DÍAS",
        "validez": "15 días",
        "categoria": "Proxy",
    },
    "🗓 Proxy 30 días - $12.00": {
        "precio": 12.00,
        "archivo": "proxy_30dias.txt",
        "nombre": "PROXY 30 DÍAS",
        "validez": "30 días",
        "categoria": "Proxy",
    },

    # FLOURITE IOS
    "📱 Flourite iOS 7 días - $10.00": {
        "precio": 10.00,
        "archivo": "flourite_7dias.txt",
        "nombre": "FLOURITE IOS 7 DÍAS",
        "validez": "7 días",
        "categoria": "Flourite iOS",
    },
    "📱 Flourite iOS 30 días - $15.00": {
        "precio": 15.00,
        "archivo": "flourite_30dias.txt",
        "nombre": "FLOURITE IOS 30 DÍAS",
        "validez": "30 días",
        "categoria": "Flourite iOS",
    },

    # CUBAN MODS
    "🧩 Cuban Mods 1 día - $1.00": {
        "precio": 1.00,
        "archivo": "cuban_1dia.txt",
        "nombre": "CUBAN MODS 1 DÍA",
        "validez": "1 día",
        "categoria": "Cuban Mods",
    },
    "🧩 Cuban Mods 7 días - $3.50": {
        "precio": 3.50,
        "archivo": "cuban_7dias.txt",
        "nombre": "CUBAN MODS 7 DÍAS",
        "validez": "7 días",
        "categoria": "Cuban Mods",
    },
    "🧩 Cuban Mods 15 días - $7.00": {
        "precio": 7.00,
        "archivo": "cuban_15dias.txt",
        "nombre": "CUBAN MODS 15 DÍAS",
        "validez": "15 días",
        "categoria": "Cuban Mods",
    },
    "🧩 Cuban Mods 30 días - $10.00": {
        "precio": 10.00,
        "archivo": "cuban_30dias.txt",
        "nombre": "CUBAN MODS 30 DÍAS",
        "validez": "30 días",
        "categoria": "Cuban Mods",
    },
}

PAYMENT_INFO = {
    "🇦🇷 Mercado Pago": (
        "🇦🇷 *Mercado Pago Argentina*\n\n"
        "Alias: `Tommydll`\n"
        "Titular: `Francisco Carrizo`\n\n"
        "Después de pagar envía el monto."
    ),
    "🇲🇽 Mercado Pago MX": (
        "🇲🇽 *Mercado Pago México*\n\n"
        "CLABE / Cuenta: `728969000160835127`\n"
        "Titular: `Esteban Jael Bonilla Sosa`\n\n"
        "Después de pagar envía el monto."
    ),
    "🪙 Binance": (
        "🪙 *Binance*\n\n"
        "ID Binance: `889752057`\n"
        "Red: `BINANCE`\n\n"
        "Después de pagar envía el monto."
    ),
    "🇺🇸 Zelle (USA)": (
        "🇺🇸 *Zelle (USA)*\n\n"
        "Email / Phone: `+1 862 453 7997`\n"
        "Name: `Edy daheri Sáenz López`\n\n"
        "Después de pagar envía el monto."
    ),
    "🏦 Transferencia": (
        "🏦 *Transferencia bancaria*\n\n"
        "CBU / CVU: `TU_CBU_O_CVU`\n"
        "Titular: `TU_NOMBRE`\n"
        "Banco: `TU_BANCO`\n\n"
        "Después de pagar envía el monto."
    ),
}

sesiones = {}


# =========================
# DATABASE
# =========================
def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            saldo REAL NOT NULL DEFAULT 0,
            telegram_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            detalle TEXT NOT NULL,
            monto REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recharge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            telegram_id INTEGER NOT NULL,
            metodo TEXT NOT NULL,
            monto REAL NOT NULL,
            referencia TEXT,
            photo_file_id TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def user_exists(username: str) -> bool:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def create_user(username: str, password: str):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password, saldo, telegram_id) VALUES (?, ?, 0, NULL)",
        (username, password),
    )
    conn.commit()
    conn.close()


def check_login(username: str, password: str) -> bool:
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def set_user_telegram_id(username: str, telegram_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET telegram_id = ? WHERE username = ?",
        (telegram_id, username),
    )
    conn.commit()
    conn.close()


def get_user_saldo(username: str) -> float:
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT saldo FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0


def add_user_saldo(username: str, monto: float):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET saldo = saldo + ? WHERE username = ?",
        (monto, username),
    )
    conn.commit()
    conn.close()


def list_users():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT username, saldo FROM users ORDER BY username ASC")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_history(username: str, tipo: str, detalle: str, monto=None):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history (username, fecha, tipo, detalle, monto) VALUES (?, ?, ?, ?, ?)",
        (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo, detalle, monto),
    )
    conn.commit()
    conn.close()


def get_user_history(username: str, limit: int = 10):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT fecha, tipo, detalle, monto FROM history WHERE username = ? ORDER BY id DESC LIMIT ?",
        (username, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def create_recharge_request(username: str, telegram_id: int, metodo: str, monto: float):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO recharge_requests (username, telegram_id, metodo, monto, referencia, photo_file_id, estado, fecha)
        VALUES (?, ?, ?, ?, '', '', 'pendiente', ?)
        """,
        (username, telegram_id, metodo, monto, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    req_id = cur.lastrowid
    conn.commit()
    conn.close()
    return req_id


def set_recharge_reference(req_id: int, referencia: str):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE recharge_requests SET referencia = ? WHERE id = ?",
        (referencia, req_id),
    )
    conn.commit()
    conn.close()


def set_recharge_photo(req_id: int, photo_file_id: str):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE recharge_requests SET photo_file_id = ? WHERE id = ?",
        (photo_file_id, req_id),
    )
    conn.commit()
    conn.close()


def get_pending_requests():
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, telegram_id, metodo, monto, referencia, photo_file_id, fecha
        FROM recharge_requests
        WHERE estado = 'pendiente'
        ORDER BY id DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_request(req_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, telegram_id, metodo, monto, referencia, photo_file_id, estado, fecha
        FROM recharge_requests
        WHERE id = ?
        """,
        (req_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def approve_request(req_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, monto FROM recharge_requests WHERE id = ? AND estado = 'pendiente'",
        (req_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    username, monto = row
    bonus = 0.0

    cur.execute(
        "SELECT metodo FROM recharge_requests WHERE id = ?",
        (req_id,),
    )
    metodo_row = cur.fetchone()
    if metodo_row and metodo_row[0] == "🪙 Binance (+15% Bonus)":
        bonus = float(monto) * 0.15

    total = float(monto) + bonus

    cur.execute(
        "UPDATE users SET saldo = saldo + ? WHERE username = ?",
        (total, username),
    )
    cur.execute(
        "UPDATE recharge_requests SET estado = 'aprobada' WHERE id = ?",
        (req_id,),
    )
    conn.commit()
    conn.close()
    return username, float(monto), float(total), float(bonus)


def reject_request(req_id: int):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username FROM recharge_requests WHERE id = ? AND estado = 'pendiente'",
        (req_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    username = row[0]
    cur.execute(
        "UPDATE recharge_requests SET estado = 'rechazada' WHERE id = ?",
        (req_id,),
    )
    conn.commit()
    conn.close()
    return username


# =========================
# STOCK
# =========================
def contar_stock(archivo):
    if not os.path.exists(archivo):
        return 0
    with open(archivo, "r", encoding="utf-8") as f:
        keys = [x.strip() for x in f.readlines() if x.strip()]
    return len(keys)


def sacar_primera_key(archivo):
    if not os.path.exists(archivo):
        return None

    with open(archivo, "r", encoding="utf-8") as f:
        keys = [x.strip() for x in f.readlines() if x.strip()]

    if not keys:
        return None

    primera = keys[0]

    with open(archivo, "w", encoding="utf-8") as f:
        for key in keys[1:]:
            f.write(key + "\n")

    return primera


def agregar_keys_archivo(archivo, lineas):
    with open(archivo, "a", encoding="utf-8") as f:
        for key in lineas:
            if key.strip():
                f.write(key.strip() + "\n")


# =========================
# HELPERS
# =========================
def es_admin(chat_id):
    return chat_id == ADMIN_ID


def usuario_logueado(chat_id):
    if chat_id in sesiones and sesiones[chat_id].get("logueado"):
        return sesiones[chat_id]["usuario"]
    return None


def limpiar_sesion(chat_id):
    sesiones.pop(chat_id, None)


# =========================
# MENUS
# =========================
def menu_principal(chat_id):
    rows = [
        ["🛍 Productos", "💰 Mi saldo"],
        ["💳 Recargar saldo", "📜 Historial"],
        ["👤 Mi perfil", "🚪 Cerrar sesión"],
    ]
    if es_admin(chat_id):
        rows.append(["🛠 Admin"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def menu_productos():
    return ReplyKeyboardMarkup(
        [
            ["🌐 Proxy", "📱 Flourite iOS"],
            ["🧩 Cuban Mods"],
            ["🏠 Menú"],
        ],
        resize_keyboard=True,
    )


def menu_proxy():
    return ReplyKeyboardMarkup(
        [
            ["📅 Proxy 1 día - $1.50", "📆 Proxy 7 días - $5.00"],
            ["🗓 Proxy 15 días - $8.00", "🗓 Proxy 30 días - $12.00"],
            ["⬅️ Volver a productos", "🏠 Menú"],
        ],
        resize_keyboard=True,
    )


def menu_flourite():
    return ReplyKeyboardMarkup(
        [
            ["📱 Flourite iOS 7 días - $10.00"],
            ["📱 Flourite iOS 30 días - $15.00"],
            ["⬅️ Volver a productos", "🏠 Menú"],
        ],
        resize_keyboard=True,
    )


def menu_cuban():
    return ReplyKeyboardMarkup(
        [
            ["🧩 Cuban Mods 1 día - $1.00", "🧩 Cuban Mods 7 días - $3.50"],
            ["🧩 Cuban Mods 15 días - $7.00", "🧩 Cuban Mods 30 días - $10.00"],
            ["⬅️ Volver a productos", "🏠 Menú"],
        ],
        resize_keyboard=True,
    )


def menu_compra():
    return ReplyKeyboardMarkup(
        [["✅ Comprar una"], ["⬅️ Volver a productos", "🏠 Menú"]],
        resize_keyboard=True,
    )


def menu_recarga():
    return ReplyKeyboardMarkup(
        [
            ["🇦🇷 Mercado Pago", "🇲🇽 Mercado Pago MX"],
            ["🪙 Binance (+15% Bonus)", "🇺🇸 Zelle (USA)"],
            ["🏦 Transferencia"],
            ["🏠 Menú"],
        ],
        resize_keyboard=True,
    )


def menu_admin():
    return ReplyKeyboardMarkup(
        [
            ["📦 Ver stock", "👥 Ver usuarios"],
            ["➕ Crear usuario", "💵 Agregar saldo"],
            ["📋 Solicitudes pendientes", "📜 Historial usuario"],
            ["📥 Proxy 1 día", "📥 Proxy 7 días"],
            ["📥 Proxy 15 días", "📥 Proxy 30 días"],
            ["📥 Flourite 7 días", "📥 Flourite 30 días"],
            ["📥 Cuban 1 día", "📥 Cuban 7 días"],
            ["📥 Cuban 15 días", "📥 Cuban 30 días"],
            ["🏠 Menú"],
        ],
        resize_keyboard=True,
    )


# =========================
# TEXTOS
# =========================
def texto_menu_principal(username):
    saldo = get_user_saldo(username)
    return (
        f"🏠 *Menú Principal*\n\n"
        f"💰 Saldo: *${saldo:.2f} USD*\n"
        f"👤 Usuario: *{username}*\n\n"
        "Selecciona una opción:"
    )


def texto_producto(username, key_producto):
    p = PRODUCTOS[key_producto]
    stock = contar_stock(p["archivo"])
    saldo = get_user_saldo(username)
    return (
        f"📦 *{p['nombre']}*\n\n"
        f"💵 Precio: *${p['precio']:.2f} USD*\n"
        f"📦 Stock: *{stock} disponibles*\n"
        f"⏱ Validez: *{p['validez']}*\n\n"
        f"💰 Tu saldo: *${saldo:.2f} USD*\n\n"
        "¿Qué deseas hacer?"
    )


# =========================
# COMANDOS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = usuario_logueado(chat_id)

    if username:
        await update.message.reply_text(
            texto_menu_principal(username),
            parse_mode="Markdown",
            reply_markup=menu_principal(chat_id),
        )
        return

    sesiones[chat_id] = {"estado": "esperando_usuario"}
    await update.message.reply_text(
        "👋 Bienvenido a *Tommy Keys*\n\nIngresa tu usuario:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /adduser usuario contraseña")
        return

    username = context.args[0].strip()
    password = context.args[1].strip()

    if user_exists(username):
        await update.message.reply_text("Ese usuario ya existe.")
        return

    create_user(username, password)
    await update.message.reply_text(f"✅ Usuario creado: {username}")


async def addsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /addsaldo usuario monto")
        return

    username = context.args[0].strip()
    try:
        monto = float(context.args[1])
    except ValueError:
        await update.message.reply_text("El monto debe ser un número.")
        return

    if not user_exists(username):
        await update.message.reply_text("Ese usuario no existe.")
        return

    add_user_saldo(username, monto)
    add_history(username, "recarga_manual_admin", "Recarga manual por admin", monto)
    await update.message.reply_text(
        f"✅ Saldo agregado a {username}. Nuevo saldo: ${get_user_saldo(username):.2f}"
    )


async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    txt = (
        "📦 *Stock actual*\n\n"
        f"• Proxy 1 día: *{contar_stock('proxy_1dia.txt')}*\n"
        f"• Proxy 7 días: *{contar_stock('proxy_7dias.txt')}*\n"
        f"• Proxy 15 días: *{contar_stock('proxy_15dias.txt')}*\n"
        f"• Proxy 30 días: *{contar_stock('proxy_30dias.txt')}*\n\n"
        f"• Flourite iOS 7 días: *{contar_stock('flourite_7dias.txt')}*\n"
        f"• Flourite iOS 30 días: *{contar_stock('flourite_30dias.txt')}*\n\n"
        f"• Cuban Mods 1 día: *{contar_stock('cuban_1dia.txt')}*\n"
        f"• Cuban Mods 7 días: *{contar_stock('cuban_7dias.txt')}*\n"
        f"• Cuban Mods 15 días: *{contar_stock('cuban_15dias.txt')}*\n"
        f"• Cuban Mods 30 días: *{contar_stock('cuban_30dias.txt')}*"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")


async def addproxy1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_1dia.txt", "Proxy 1 día")


async def addproxy7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_7dias.txt", "Proxy 7 días")


async def addproxy15(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_15dias.txt", "Proxy 15 días")


async def addproxy30(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_30dias.txt", "Proxy 30 días")


async def agregar_key_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, archivo, nombre):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Debes escribir la key.")
        return

    key = " ".join(context.args).strip()
    agregar_keys_archivo(archivo, [key])
    await update.message.reply_text(f"✅ Key agregada correctamente a {nombre}.")


# =========================
# CALLBACKS
# =========================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if not es_admin(query.from_user.id):
        await query.edit_message_text("No autorizado.")
        return

    if data.startswith("aprobar_"):
        req_id = int(data.split("_")[1])
        result = approve_request(req_id)

        if not result:
            await query.edit_message_text("Esa solicitud ya no está pendiente.")
            return

        username, monto_base, total_creditado, bonus = result

        detalle = f"Solicitud #{req_id} aprobada"
        if bonus > 0:
            detalle += f" | Bonus Binance +${bonus:.2f}"

        add_history(username, "recarga_aprobada", detalle, total_creditado)

        req = get_request(req_id)
        if req:
            telegram_id = req[2]
            try:
                mensaje_bonus = f"\n🎁 Bonus: ${bonus:.2f}" if bonus > 0 else ""
                await context.bot.send_message(
                    telegram_id,
                    f"✅ Tu recarga fue aprobada.\n\n"
                    f"ID: #{req_id}\n"
                    f"Monto base: ${monto_base:.2f}{mensaje_bonus}\n"
                    f"Total acreditado: ${total_creditado:.2f}\n"
                    f"Nuevo saldo: ${get_user_saldo(username):.2f}"
                )
            except Exception:
                pass

        await query.edit_message_text(f"✅ Solicitud #{req_id} aprobada.")

    elif data.startswith("rechazar_"):
        req_id = int(data.split("_")[1])
        username = reject_request(req_id)

        if not username:
            await query.edit_message_text("Esa solicitud ya no está pendiente.")
            return

        req = get_request(req_id)
        if req:
            telegram_id = req[2]
            try:
                await context.bot.send_message(
                    telegram_id,
                    f"❌ Tu recarga fue rechazada.\n\nID: #{req_id}"
                )
            except Exception:
                pass

        await query.edit_message_text(f"❌ Solicitud #{req_id} rechazada.")


# =========================
# MENSAJES DE TEXTO
# =========================
async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mensaje = update.message.text.strip()

    # LOGIN
    if chat_id in sesiones:
        estado = sesiones[chat_id].get("estado")

        if estado == "esperando_usuario":
            sesiones[chat_id]["usuario_temp"] = mensaje
            sesiones[chat_id]["estado"] = "esperando_password"
            await update.message.reply_text("Ahora ingresa tu contraseña:")
            return

        if estado == "esperando_password":
            username = sesiones[chat_id]["usuario_temp"]

            if not user_exists(username):
                limpiar_sesion(chat_id)
                await update.message.reply_text("Usuario incorrecto.")
                return

            if not check_login(username, mensaje):
                limpiar_sesion(chat_id)
                await update.message.reply_text("Contraseña incorrecta.")
                return

            set_user_telegram_id(username, chat_id)
            sesiones[chat_id] = {"logueado": True, "usuario": username}

            await update.message.reply_text(
                texto_menu_principal(username),
                parse_mode="Markdown",
                reply_markup=menu_principal(chat_id),
            )
            return

        # ADMIN CREAR USUARIO
        if estado == "admin_crear_usuario" and es_admin(chat_id):
            partes = mensaje.split()
            if len(partes) != 2:
                await update.message.reply_text("Envía así:\nusuario contraseña")
                return

            username, password = partes
            if user_exists(username):
                await update.message.reply_text("Ese usuario ya existe.")
            else:
                create_user(username, password)
                await update.message.reply_text(f"✅ Usuario creado: {username}")

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ADMIN AGREGAR SALDO
        if estado == "admin_agregar_saldo" and es_admin(chat_id):
            partes = mensaje.split()
            if len(partes) != 2:
                await update.message.reply_text("Envía así:\nusuario monto")
                return

            username = partes[0]
            try:
                monto = float(partes[1])
            except ValueError:
                await update.message.reply_text("El monto debe ser un número.")
                return

            if not user_exists(username):
                await update.message.reply_text("Ese usuario no existe.")
            else:
                add_user_saldo(username, monto)
                add_history(username, "recarga_manual_admin", "Recarga manual por panel admin", monto)
                await update.message.reply_text(
                    f"✅ Saldo agregado a {username}. Nuevo saldo: ${get_user_saldo(username):.2f}"
                )

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ADMIN HISTORIAL USUARIO
        if estado == "admin_historial_usuario" and es_admin(chat_id):
            username = mensaje
            rows = get_user_history(username, 15)

            if not rows:
                await update.message.reply_text("Ese usuario no tiene historial.")
            else:
                txt = f"📜 Historial de {username}\n\n"
                for fecha, tipo, detalle, monto in rows:
                    txt += (
                        f"🕒 {fecha}\n"
                        f"🏷 {tipo}\n"
                        f"📝 {detalle}\n"
                        f"💵 {monto if monto is not None else '-'}\n\n"
                    )
                await update.message.reply_text(txt)

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # SUBIR KEYS
        mapa_subidas = {
            "subir_proxy_1": ("proxy_1dia.txt", "Proxy 1 día"),
            "subir_proxy_7": ("proxy_7dias.txt", "Proxy 7 días"),
            "subir_proxy_15": ("proxy_15dias.txt", "Proxy 15 días"),
            "subir_proxy_30": ("proxy_30dias.txt", "Proxy 30 días"),
            "subir_flourite_7": ("flourite_7dias.txt", "Flourite iOS 7 días"),
            "subir_flourite_30": ("flourite_30dias.txt", "Flourite iOS 30 días"),
            "subir_cuban_1": ("cuban_1dia.txt", "Cuban Mods 1 día"),
            "subir_cuban_7": ("cuban_7dias.txt", "Cuban Mods 7 días"),
            "subir_cuban_15": ("cuban_15dias.txt", "Cuban Mods 15 días"),
            "subir_cuban_30": ("cuban_30dias.txt", "Cuban Mods 30 días"),
        }

        if estado in mapa_subidas and es_admin(chat_id):
            archivo, nombre = mapa_subidas[estado]
            keys = [x.strip() for x in mensaje.splitlines() if x.strip()]

            if not keys:
                await update.message.reply_text("No enviaste keys.")
                return

            agregar_keys_archivo(archivo, keys)
            await update.message.reply_text(f"✅ Se agregaron {len(keys)} keys a {nombre}.")
            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # RECARGA MONTO
        if estado == "recarga_monto":
            try:
                monto = float(mensaje.replace(",", "."))
            except ValueError:
                await update.message.reply_text("Ingresa un monto válido. Ejemplo: 10 o 15.50")
                return

            if monto <= 0:
                await update.message.reply_text("El monto debe ser mayor a 0.")
                return

            req_id = create_recharge_request(
                sesiones[chat_id]["usuario"],
                chat_id,
                sesiones[chat_id]["metodo_pago"],
                monto,
            )
            sesiones[chat_id]["req_id_actual"] = req_id
            sesiones[chat_id]["estado"] = "recarga_referencia"

            await update.message.reply_text(
                f"✅ Monto recibido: ${monto:.2f}\n\n"
                "Ahora envía una referencia, alias, número de operación o texto del comprobante."
            )
            return

        # RECARGA REFERENCIA
        if estado == "recarga_referencia":
            req_id = sesiones[chat_id]["req_id_actual"]
            set_recharge_reference(req_id, mensaje)
            sesiones[chat_id]["estado"] = "esperando_foto_comprobante"

            await update.message.reply_text(
                "Ahora envía la *foto del comprobante*.",
                parse_mode="Markdown"
            )
            return

    # USUARIO LOGUEADO
    username = usuario_logueado(chat_id)
    if not username:
        return

    if mensaje == "🏠 Menú":
        await update.message.reply_text(
            texto_menu_principal(username),
            parse_mode="Markdown",
            reply_markup=menu_principal(chat_id),
        )
        return

    if mensaje == "🛍 Productos":
        await update.message.reply_text(
            "🛍 Productos\n\nSelecciona una categoría:",
            reply_markup=menu_productos(),
        )
        return

    if mensaje == "🌐 Proxy":
        await update.message.reply_text(
            "🌐 Proxy\n\nSelecciona un plan:",
            reply_markup=menu_proxy(),
        )
        return

    if mensaje == "📱 Flourite iOS":
        await update.message.reply_text(
            "📱 Flourite iOS\n\nSelecciona un plan:",
            reply_markup=menu_flourite(),
        )
        return

    if mensaje == "🧩 Cuban Mods":
        await update.message.reply_text(
            "🧩 Cuban Mods\n\nSelecciona un plan:",
            reply_markup=menu_cuban(),
        )
        return

    if mensaje == "⬅️ Volver a productos":
        await update.message.reply_text(
            "🛍 Productos\n\nSelecciona una categoría:",
            reply_markup=menu_productos(),
        )
        return

    if mensaje == "💰 Mi saldo":
        await update.message.reply_text(
            f"💰 Tu saldo actual es: ${get_user_saldo(username):.2f} USD"
        )
        return

    if mensaje == "👤 Mi perfil":
        await update.message.reply_text(
            f"👤 Usuario: {username}\n💰 Saldo: ${get_user_saldo(username):.2f} USD"
        )
        return

    if mensaje == "📜 Historial":
        rows = get_user_history(username, 10)
        if not rows:
            await update.message.reply_text("📜 No tienes historial aún.")
            return

        txt = "📜 Últimos movimientos:\n\n"
        for fecha, tipo, detalle, monto in rows:
            txt += (
                f"🕒 {fecha}\n"
                f"🏷 {tipo}\n"
                f"📝 {detalle}\n"
                f"💵 {monto if monto is not None else '-'}\n\n"
            )
        await update.message.reply_text(txt)
        return

    if mensaje == "🚪 Cerrar sesión":
        limpiar_sesion(chat_id)
        await update.message.reply_text(
            "Sesión cerrada.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if mensaje == "💳 Recargar saldo":
        await update.message.reply_text(
            "💳 Selecciona un método de pago:",
            reply_markup=menu_recarga(),
        )
        return

    if mensaje in PAYMENT_INFO:
        sesiones[chat_id]["metodo_pago"] = mensaje
        sesiones[chat_id]["estado"] = "recarga_monto"

        await update.message.reply_text(
            PAYMENT_INFO[mensaje],
            parse_mode="Markdown",
            reply_markup=menu_recarga(),
        )
        await update.message.reply_text("Ahora envía el monto que pagaste.")
        return

    if mensaje == "🛠 Admin" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = None
        await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
        return

    if mensaje == "📦 Ver stock" and es_admin(chat_id):
        txt = (
            "📦 *Stock actual*\n\n"
            f"• Proxy 1 día: *{contar_stock('proxy_1dia.txt')}*\n"
            f"• Proxy 7 días: *{contar_stock('proxy_7dias.txt')}*\n"
            f"• Proxy 15 días: *{contar_stock('proxy_15dias.txt')}*\n"
            f"• Proxy 30 días: *{contar_stock('proxy_30dias.txt')}*\n\n"
            f"• Flourite iOS 7 días: *{contar_stock('flourite_7dias.txt')}*\n"
            f"• Flourite iOS 30 días: *{contar_stock('flourite_30dias.txt')}*\n\n"
            f"• Cuban Mods 1 día: *{contar_stock('cuban_1dia.txt')}*\n"
            f"• Cuban Mods 7 días: *{contar_stock('cuban_7dias.txt')}*\n"
            f"• Cuban Mods 15 días: *{contar_stock('cuban_15dias.txt')}*\n"
            f"• Cuban Mods 30 días: *{contar_stock('cuban_30dias.txt')}*"
        )
        await update.message.reply_text(txt, parse_mode="Markdown")
        return

    if mensaje == "👥 Ver usuarios" and es_admin(chat_id):
        rows = list_users()
        if not rows:
            await update.message.reply_text("No hay usuarios.")
            return
        txt = "👥 Usuarios:\n\n"
        for uname, saldo in rows:
            txt += f"• {uname} — ${float(saldo):.2f}\n"
        await update.message.reply_text(txt)
        return

    if mensaje == "➕ Crear usuario" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "admin_crear_usuario"
        await update.message.reply_text("Envía así:\nusuario contraseña")
        return

    if mensaje == "💵 Agregar saldo" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "admin_agregar_saldo"
        await update.message.reply_text("Envía así:\nusuario monto")
        return

    if mensaje == "📜 Historial usuario" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "admin_historial_usuario"
        await update.message.reply_text("Envía el usuario para ver su historial.")
        return

    if mensaje == "📥 Proxy 1 día" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_proxy_1"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Proxy 7 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_proxy_7"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Proxy 15 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_proxy_15"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Proxy 30 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_proxy_30"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Flourite 7 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_flourite_7"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Flourite 30 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_flourite_30"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Cuban 1 día" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_cuban_1"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Cuban 7 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_cuban_7"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Cuban 15 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_cuban_15"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Cuban 30 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_cuban_30"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📋 Solicitudes pendientes" and es_admin(chat_id):
        rows = get_pending_requests()
        if not rows:
            await update.message.reply_text("No hay solicitudes pendientes.")
            return

        for req_id, uname, telegram_id, metodo, monto, referencia, photo_file_id, fecha in rows[:20]:
            texto_req = (
                f"💳 *Solicitud pendiente*\n\n"
                f"ID: *#{req_id}*\n"
                f"Usuario: *{uname}*\n"
                f"Método: *{metodo}*\n"
                f"Monto: *${float(monto):.2f}*\n"
                f"Referencia: *{referencia or '-'}*\n"
                f"Fecha: *{fecha}*"
            )
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_{req_id}"),
                    InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{req_id}")
                ]
            ])

            if photo_file_id:
                try:
                    await update.message.reply_photo(
                        photo=photo_file_id,
                        caption=texto_req,
                        parse_mode="Markdown",
                        reply_markup=kb,
                    )
                except Exception:
                    await update.message.reply_text(
                        texto_req,
                        parse_mode="Markdown",
                        reply_markup=kb,
                    )
            else:
                await update.message.reply_text(
                    texto_req,
                    parse_mode="Markdown",
                    reply_markup=kb,
                )
        return

    if mensaje in PRODUCTOS:
        sesiones[chat_id]["producto_actual"] = mensaje
        await update.message.reply_text(
            texto_producto(username, mensaje),
            parse_mode="Markdown",
            reply_markup=menu_compra(),
        )
        return

    if mensaje == "✅ Comprar una":
        producto_key = sesiones.get(chat_id, {}).get("producto_actual")
        if not producto_key or producto_key not in PRODUCTOS:
            await update.message.reply_text("Primero selecciona un producto.")
            return

        p = PRODUCTOS[producto_key]
        saldo = get_user_saldo(username)

        if saldo < p["precio"]:
            await update.message.reply_text(
                f"Saldo insuficiente.\n\nPrecio: ${p['precio']:.2f}\nTu saldo: ${saldo:.2f}"
            )
            return

        if contar_stock(p["archivo"]) <= 0:
            await update.message.reply_text("No hay stock disponible para este producto.")
            return

        key = sacar_primera_key(p["archivo"])
        if not key:
            await update.message.reply_text("No hay stock disponible para este producto.")
            return

        add_user_saldo(username, -p["precio"])
        add_history(username, "compra", f"Compra de {p['nombre']} | Key: {key}", p["precio"])

        await update.message.reply_text(
            f"✅ Compra exitosa\n\n"
            f"📦 Producto: {p['nombre']}\n"
            f"🔑 Tu key:\n{key}\n\n"
            f"💰 Saldo restante: ${get_user_saldo(username):.2f}",
            reply_markup=menu_principal(chat_id),
        )
        return


async def fotos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in sesiones:
        return

    if sesiones[chat_id].get("estado") != "esperando_foto_comprobante":
        return

    req_id = sesiones[chat_id].get("req_id_actual")
    username = sesiones[chat_id].get("usuario")
    metodo = sesiones[chat_id].get("metodo_pago")

    if not req_id:
        await update.message.reply_text("No hay solicitud activa.")
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id
    set_recharge_photo(req_id, file_id)

    req = get_request(req_id)
    monto = req[4] if req else 0
    referencia = req[5] if req else ""

    await update.message.reply_text(
        f"✅ Solicitud enviada.\n\n"
        f"ID: #{req_id}\n"
        f"Método: {metodo}\n"
        f"Monto: ${float(monto):.2f}\n"
        f"Estado: pendiente\n\n"
        f"El admin la revisará.",
        reply_markup=menu_principal(chat_id),
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_{req_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{req_id}")
        ]
    ])

    try:
        await context.bot.send_photo(
            ADMIN_ID,
            photo=file_id,
            caption=(
                f"💳 *Nueva solicitud de recarga*\n\n"
                f"ID: *#{req_id}*\n"
                f"Usuario: *{username}*\n"
                f"Método: *{metodo}*\n"
                f"Monto: *${float(monto):.2f}*\n"
                f"Referencia: *{referencia or '-'}*"
            ),
            parse_mode="Markdown",
            reply_markup=kb,
        )
    except Exception:
        await context.bot.send_message(
            ADMIN_ID,
            f"Nueva solicitud #{req_id} de {username}"
        )

    sesiones[chat_id]["estado"] = None
    sesiones[chat_id].pop("req_id_actual", None)


# =========================
# MAIN
# =========================
init_db()

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("adduser", adduser))
app.add_handler(CommandHandler("addsaldo", addsaldo))
app.add_handler(CommandHandler("stock", stock))
app.add_handler(CommandHandler("addproxy1", addproxy1))
app.add_handler(CommandHandler("addproxy7", addproxy7))
app.add_handler(CommandHandler("addproxy15", addproxy15))
app.add_handler(CommandHandler("addproxy30", addproxy30))

app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.PHOTO, fotos))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto))

app.run_polling()

