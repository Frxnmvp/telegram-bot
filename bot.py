import json
import os
import re
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8733783250:AAEKLrNpzEPvItVTpJRSTeLv3QDUOXdS0Xg"
ADMIN_ID = 8179362627

USERS_FILE = "users.json"
HISTORY_FILE = "history.json"
REQUESTS_FILE = "recharge_requests.json"

PRODUCTOS = {
    "📅 1 día - $1.50": {
        "precio": 1.50,
        "archivo": "proxy_1dia.txt",
        "nombre": "PROXY 1 DÍA",
        "validez": "1 día"
    },
    "📆 7 días - $5.00": {
        "precio": 5.00,
        "archivo": "proxy_7dias.txt",
        "nombre": "PROXY 7 DÍAS",
        "validez": "7 días"
    },
    "🗓 15 días - $8.00": {
        "precio": 8.00,
        "archivo": "proxy_15dias.txt",
        "nombre": "PROXY 15 DÍAS",
        "validez": "15 días"
    },
    "🗓 30 días - $12.00": {
        "precio": 12.00,
        "archivo": "proxy_30dias.txt",
        "nombre": "PROXY 30 DÍAS",
        "validez": "30 días"
    },
}

PAYMENT_INFO = {
    "💙 Mercado Pago": {
        "titulo": "Mercado Pago",
        "texto": (
            "💙 *Mercado Pago*\n\n"
            "Alias: `Tommydll`\n"
            "Titular: `Francisco Carrizo`\n\n"
            "Después de pagar, envía el *monto*.\n"
            "Luego te pediré una *referencia o comprobante*."
        )
    },
    "🏦 Transferencia": {
        "titulo": "Transferencia",
        "texto": (
            "🏦 *Transferencia bancaria*\n\n"
            "CBU/CVU: `TU_CBU_O_CVU_AQUI`\n"
            "Titular: `TU_NOMBRE_AQUI`\n"
            "Banco: `TU_BANCO_AQUI`\n\n"
            "Después de pagar, envía el *monto*.\n"
            "Luego te pediré una *referencia o comprobante*."
        )
    },
    "🪙 USDT": {
        "titulo": "USDT",
        "texto": (
            "🪙 *USDT*\n\n"
            "Red: `TRC20 o la que uses`\n"
            "Wallet: `TU_WALLET_AQUI`\n\n"
            "Después de pagar, envía el *monto*.\n"
            "Luego te pediré una *referencia o hash*."
        )
    }
}

usuarios = {}
historial = []
solicitudes = []
sesiones = {}


# =========================
# UTILIDADES JSON / ARCHIVOS
# =========================
def ensure_json_file(path, default_value):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_value, f, ensure_ascii=False, indent=2)


def load_json(path, default_value):
    ensure_json_file(path, default_value)
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_value


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cargar_datos():
    global usuarios, historial, solicitudes
    usuarios = load_json(USERS_FILE, {})
    historial = load_json(HISTORY_FILE, [])
    solicitudes = load_json(REQUESTS_FILE, [])


def guardar_usuarios():
    save_json(USERS_FILE, usuarios)


def guardar_historial():
    save_json(HISTORY_FILE, historial)


def guardar_solicitudes():
    save_json(REQUESTS_FILE, solicitudes)


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


def agregar_historial(usuario, tipo, detalle, monto=None):
    historial.append({
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": usuario,
        "tipo": tipo,
        "detalle": detalle,
        "monto": monto
    })
    guardar_historial()


def siguiente_id_solicitud():
    if not solicitudes:
        return 1
    return max(s["id"] for s in solicitudes) + 1


def obtener_solicitudes_pendientes():
    return [s for s in solicitudes if s["estado"] == "pendiente"]


def buscar_solicitud_por_id(req_id):
    for s in solicitudes:
        if s["id"] == req_id:
            return s
    return None


def limpiar_sesion(chat_id):
    if chat_id in sesiones:
        sesiones.pop(chat_id, None)


def usuario_logueado(chat_id):
    if chat_id in sesiones and sesiones[chat_id].get("logueado"):
        return sesiones[chat_id]["usuario"]
    return None


def es_admin(chat_id):
    return chat_id == ADMIN_ID


# =========================
# MENUS
# =========================
def menu_principal(chat_id):
    teclado = [
        ["🛍 Productos", "💰 Mi saldo"],
        ["💳 Recargar saldo", "📜 Historial"],
        ["👤 Mi perfil", "🚪 Cerrar sesión"]
    ]

    if es_admin(chat_id):
        teclado.append(["🛠 Admin"])

    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_productos():
    teclado = [
        ["🌐 Proxy"],
        ["🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_proxy():
    teclado = [
        ["📅 1 día - $1.50", "📆 7 días - $5.00"],
        ["🗓 15 días - $8.00", "🗓 30 días - $12.00"],
        ["⬅️ Volver a productos", "🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_compra():
    teclado = [
        ["✅ Comprar una"],
        ["⬅️ Volver a productos", "🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_recarga():
    teclado = [
        ["💙 Mercado Pago", "🏦 Transferencia"],
        ["🪙 USDT"],
        ["🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_admin():
    teclado = [
        ["📦 Ver stock", "📋 Solicitudes pendientes"],
        ["➕ Crear usuario", "💵 Agregar saldo"],
        ["👥 Ver usuarios", "📜 Historial usuario"],
        ["📥 Subir keys 1 día", "📥 Subir keys 7 días"],
        ["📥 Subir keys 15 días", "📥 Subir keys 30 días"],
        ["🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


# =========================
# MENSAJES
# =========================
def texto_menu_principal(usuario):
    saldo = usuarios[usuario]["saldo"]
    return (
        f"🏠 *Menú Principal*\n\n"
        f"💰 Saldo: *${saldo:.2f} USD*\n"
        f"👤 Usuario: *{usuario}*\n\n"
        "Selecciona una opción:"
    )


def texto_producto(usuario, producto_key):
    producto = PRODUCTOS[producto_key]
    stock = contar_stock(producto["archivo"])
    saldo = usuarios[usuario]["saldo"]

    return (
        f"📦 *{producto['nombre']}*\n\n"
        f"💵 Precio: *${producto['precio']:.2f} USD*\n"
        f"📦 Stock: *{stock} disponibles*\n"
        f"⏱ Validez: *{producto['validez']}*\n\n"
        f"💰 Tu saldo: *${saldo:.2f} USD*\n\n"
        "¿Qué deseas hacer?"
    )


# =========================
# COMANDOS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    usuario = usuario_logueado(chat_id)

    if usuario:
        await update.message.reply_text(
            texto_menu_principal(usuario),
            parse_mode="Markdown",
            reply_markup=menu_principal(chat_id)
        )
        return

    sesiones[chat_id] = {"estado": "esperando_usuario"}
    await update.message.reply_text(
        "👋 Bienvenido a *Tommy Keys*\n\nIngresa tu usuario:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )


async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /adduser usuario contraseña")
        return

    user = context.args[0].strip()
    password = context.args[1].strip()

    if user in usuarios:
        await update.message.reply_text("Ese usuario ya existe.")
        return

    usuarios[user] = {
        "password": password,
        "saldo": 0.0,
        "telegram_id": None
    }
    guardar_usuarios()
    await update.message.reply_text(f"✅ Usuario creado: {user}")


async def addsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /addsaldo usuario monto")
        return

    user = context.args[0].strip()

    try:
        monto = float(context.args[1])
    except ValueError:
        await update.message.reply_text("El monto debe ser un número.")
        return

    if user not in usuarios:
        await update.message.reply_text("Ese usuario no existe.")
        return

    usuarios[user]["saldo"] += monto
    guardar_usuarios()
    agregar_historial(user, "recarga_manual_admin", "Recarga manual por admin", monto)

    await update.message.reply_text(
        f"✅ Saldo agregado a {user}. Nuevo saldo: ${usuarios[user]['saldo']:.2f}"
    )


async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    texto = (
        "📦 *Stock actual*\n\n"
        f"• Proxy 1 día: *{contar_stock('proxy_1dia.txt')}*\n"
        f"• Proxy 7 días: *{contar_stock('proxy_7dias.txt')}*\n"
        f"• Proxy 15 días: *{contar_stock('proxy_15dias.txt')}*\n"
        f"• Proxy 30 días: *{contar_stock('proxy_30dias.txt')}*"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def addproxy1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_1dia.txt", "Proxy 1 día")


async def addproxy7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_7dias.txt", "Proxy 7 días")


async def addproxy15(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_15dias.txt", "Proxy 15 días")


async def addproxy30(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await agregar_key_admin(update, context, "proxy_30dias.txt", "Proxy 30 días")


async def agregar_key_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, archivo: str, nombre: str):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Debes escribir la key.")
        return

    key = " ".join(context.args).strip()

    with open(archivo, "a", encoding="utf-8") as f:
        f.write(key + "\n")

    await update.message.reply_text(f"✅ Key agregada correctamente a {nombre}.")


# =========================
# FLUJO PRINCIPAL
# =========================
async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mensaje = update.message.text.strip()

    # ===== LOGIN =====
    if chat_id in sesiones:
        estado = sesiones[chat_id].get("estado")

        if estado == "esperando_usuario":
            sesiones[chat_id]["usuario_temp"] = mensaje
            sesiones[chat_id]["estado"] = "esperando_password"
            await update.message.reply_text("Ahora ingresa tu contraseña:")
            return

        if estado == "esperando_password":
            user = sesiones[chat_id].get("usuario_temp")

            if user not in usuarios:
                limpiar_sesion(chat_id)
                await update.message.reply_text("Usuario incorrecto.")
                return

            if usuarios[user]["password"] != mensaje:
                limpiar_sesion(chat_id)
                await update.message.reply_text("Contraseña incorrecta.")
                return

            usuarios[user]["telegram_id"] = chat_id
            guardar_usuarios()

            sesiones[chat_id] = {
                "logueado": True,
                "usuario": user
            }

            await update.message.reply_text(
                texto_menu_principal(user),
                parse_mode="Markdown",
                reply_markup=menu_principal(chat_id)
            )
            return

        # ===== ADMIN: crear usuario =====
        if estado == "admin_crear_usuario" and es_admin(chat_id):
            partes = mensaje.split()
            if len(partes) != 2:
                await update.message.reply_text("Envía así:\nusuario contraseña")
                return

            user, password = partes
            if user in usuarios:
                await update.message.reply_text("Ese usuario ya existe.")
            else:
                usuarios[user] = {
                    "password": password,
                    "saldo": 0.0,
                    "telegram_id": None
                }
                guardar_usuarios()
                await update.message.reply_text(f"✅ Usuario creado: {user}")

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ===== ADMIN: agregar saldo =====
        if estado == "admin_agregar_saldo" and es_admin(chat_id):
            partes = mensaje.split()
            if len(partes) != 2:
                await update.message.reply_text("Envía así:\nusuario monto")
                return

            user = partes[0]
            try:
                monto = float(partes[1])
            except ValueError:
                await update.message.reply_text("El monto debe ser un número.")
                return

            if user not in usuarios:
                await update.message.reply_text("Ese usuario no existe.")
            else:
                usuarios[user]["saldo"] += monto
                guardar_usuarios()
                agregar_historial(user, "recarga_manual_admin", "Recarga manual por panel admin", monto)
                await update.message.reply_text(
                    f"✅ Saldo agregado a {user}. Nuevo saldo: ${usuarios[user]['saldo']:.2f}"
                )

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ===== ADMIN: historial usuario =====
        if estado == "admin_historial_usuario" and es_admin(chat_id):
            user = mensaje.strip()
            items = [h for h in historial if h["usuario"] == user][-15:]

            if not items:
                await update.message.reply_text("Ese usuario no tiene historial.")
            else:
                txt = f"📜 Historial de {user}\n\n"
                for h in items:
                    txt += (
                        f"🕒 {h['fecha']}\n"
                        f"🏷 {h['tipo']}\n"
                        f"📝 {h['detalle']}\n"
                        f"💵 {h['monto'] if h['monto'] is not None else '-'}\n\n"
                    )
                await update.message.reply_text(txt)

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ===== ADMIN: subir keys masivas =====
        if estado in {"subir_1dia", "subir_7dias", "subir_15dias", "subir_30dias"} and es_admin(chat_id):
            mapa = {
                "subir_1dia": ("proxy_1dia.txt", "Proxy 1 día"),
                "subir_7dias": ("proxy_7dias.txt", "Proxy 7 días"),
                "subir_15dias": ("proxy_15dias.txt", "Proxy 15 días"),
                "subir_30dias": ("proxy_30dias.txt", "Proxy 30 días"),
            }
            archivo, nombre = mapa[estado]
            lineas = [x.strip() for x in mensaje.splitlines() if x.strip()]

            if not lineas:
                await update.message.reply_text("No enviastes keys.")
                return

            with open(archivo, "a", encoding="utf-8") as f:
                for key in lineas:
                    f.write(key + "\n")

            await update.message.reply_text(f"✅ Se agregaron {len(lineas)} keys a {nombre}.")
            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ===== RECARGA: MONTO =====
        if estado == "recarga_monto":
            monto_txt = mensaje.replace(",", ".").strip()

            try:
                monto = float(monto_txt)
            except ValueError:
                await update.message.reply_text("Ingresa un monto válido. Ejemplo: 10 o 15.50")
                return

            if monto <= 0:
                await update.message.reply_text("El monto debe ser mayor a 0.")
                return

            sesiones[chat_id]["monto_recarga"] = monto
            sesiones[chat_id]["estado"] = "recarga_referencia"

            metodo = sesiones[chat_id]["metodo_pago"]
            await update.message.reply_text(
                f"✅ Monto recibido: ${monto:.2f}\n\n"
                f"Ahora envía la *referencia, hash o comprobante* del pago por {metodo}.",
                parse_mode="Markdown"
            )
            return

        # ===== RECARGA: REFERENCIA =====
        if estado == "recarga_referencia":
            referencia = mensaje
            metodo = sesiones[chat_id]["metodo_pago"]
            monto = sesiones[chat_id]["monto_recarga"]
            user = sesiones[chat_id]["usuario"]

            nueva = {
                "id": siguiente_id_solicitud(),
                "usuario": user,
                "telegram_id": chat_id,
                "metodo": metodo,
                "monto": monto,
                "referencia": referencia,
                "estado": "pendiente",
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            solicitudes.append(nueva)
            guardar_solicitudes()

            sesiones[chat_id]["estado"] = None

            await update.message.reply_text(
                f"✅ Solicitud enviada.\n\n"
                f"ID: #{nueva['id']}\n"
                f"Método: {metodo}\n"
                f"Monto: ${monto:.2f}\n"
                f"Estado: pendiente\n\n"
                "Un administrador la revisará.",
                reply_markup=menu_principal(chat_id)
            )

            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"💳 Nueva solicitud de recarga\n\n"
                    f"ID: #{nueva['id']}\n"
                    f"Usuario: {user}\n"
                    f"Método: {metodo}\n"
                    f"Monto: ${monto:.2f}\n"
                    f"Referencia: {referencia}\n"
                    f"Fecha: {nueva['fecha']}"
                )
            except Exception:
                pass
            return

        # ===== ADMIN: aprobar solicitud =====
        if estado == "admin_aprobar_solicitud" and es_admin(chat_id):
            match = re.search(r"\d+", mensaje)
            if not match:
                await update.message.reply_text("Envía el ID numérico. Ejemplo: 3")
                return

            req_id = int(match.group())
            req = buscar_solicitud_por_id(req_id)

            if not req:
                await update.message.reply_text("No existe esa solicitud.")
                return

            if req["estado"] != "pendiente":
                await update.message.reply_text("Esa solicitud ya no está pendiente.")
                return

            user = req["usuario"]
            if user not in usuarios:
                await update.message.reply_text("El usuario ya no existe.")
                return

            usuarios[user]["saldo"] += float(req["monto"])
            guardar_usuarios()

            req["estado"] = "aprobada"
            req["aprobada_por"] = "admin"
            req["fecha_aprobacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            guardar_solicitudes()

            agregar_historial(
                user,
                "recarga_aprobada",
                f"Recarga aprobada por {req['metodo']} | Ref: {req['referencia']}",
                req["monto"]
            )

            await update.message.reply_text(
                f"✅ Solicitud #{req_id} aprobada.\nSaldo agregado a {user}."
            )

            try:
                await context.bot.send_message(
                    req["telegram_id"],
                    f"✅ Tu recarga fue aprobada.\n\n"
                    f"ID: #{req_id}\n"
                    f"Monto acreditado: ${float(req['monto']):.2f}\n"
                    f"Nuevo saldo: ${usuarios[user]['saldo']:.2f}"
                )
            except Exception:
                pass

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

        # ===== ADMIN: rechazar solicitud =====
        if estado == "admin_rechazar_solicitud" and es_admin(chat_id):
            match = re.search(r"\d+", mensaje)
            if not match:
                await update.message.reply_text("Envía el ID numérico. Ejemplo: 3")
                return

            req_id = int(match.group())
            req = buscar_solicitud_por_id(req_id)

            if not req:
                await update.message.reply_text("No existe esa solicitud.")
                return

            if req["estado"] != "pendiente":
                await update.message.reply_text("Esa solicitud ya no está pendiente.")
                return

            req["estado"] = "rechazada"
            req["rechazada_por"] = "admin"
            req["fecha_rechazo"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            guardar_solicitudes()

            await update.message.reply_text(f"❌ Solicitud #{req_id} rechazada.")

            try:
                await context.bot.send_message(
                    req["telegram_id"],
                    f"❌ Tu recarga fue rechazada.\n\nID: #{req_id}\n"
                    "Si fue un error, contacta al administrador."
                )
            except Exception:
                pass

            sesiones[chat_id]["estado"] = None
            await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
            return

    # ===== USUARIO LOGUEADO =====
    user = usuario_logueado(chat_id)
    if not user:
        return

    # menú
    if mensaje == "🏠 Menú":
        await update.message.reply_text(
            texto_menu_principal(user),
            parse_mode="Markdown",
            reply_markup=menu_principal(chat_id)
        )
        return

    if mensaje == "🛍 Productos":
        await update.message.reply_text(
            "🛍 Productos\n\nSelecciona una categoría:",
            reply_markup=menu_productos()
        )
        return

    if mensaje == "🌐 Proxy":
        await update.message.reply_text(
            "🌐 Proxy\n\nSelecciona un plan:",
            reply_markup=menu_proxy()
        )
        return

    if mensaje == "⬅️ Volver a productos":
        await update.message.reply_text(
            "🛍 Productos\n\nSelecciona una categoría:",
            reply_markup=menu_productos()
        )
        return

    if mensaje == "💰 Mi saldo":
        await update.message.reply_text(
            f"💰 Tu saldo actual es: ${usuarios[user]['saldo']:.2f} USD"
        )
        return

    if mensaje == "👤 Mi perfil":
        await update.message.reply_text(
            f"👤 Usuario: {user}\n"
            f"💰 Saldo: ${usuarios[user]['saldo']:.2f} USD"
        )
        return

    if mensaje == "📜 Historial":
        items = [h for h in historial if h["usuario"] == user][-10:]

        if not items:
            await update.message.reply_text("📜 No tienes historial aún.")
            return

        txt = "📜 Últimos movimientos:\n\n"
        for h in items:
            txt += (
                f"🕒 {h['fecha']}\n"
                f"🏷 {h['tipo']}\n"
                f"📝 {h['detalle']}\n"
                f"💵 {h['monto'] if h['monto'] is not None else '-'}\n\n"
            )
        await update.message.reply_text(txt)
        return

    if mensaje == "🚪 Cerrar sesión":
        limpiar_sesion(chat_id)
        await update.message.reply_text(
            "Sesión cerrada.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # ===== RECARGA =====
    if mensaje == "💳 Recargar saldo":
        await update.message.reply_text(
            "💳 Selecciona un método de pago:",
            reply_markup=menu_recarga()
        )
        return

    if mensaje in PAYMENT_INFO:
        sesiones[chat_id]["metodo_pago"] = mensaje
        sesiones[chat_id]["estado"] = "recarga_monto"

        await update.message.reply_text(
            PAYMENT_INFO[mensaje]["texto"],
            parse_mode="Markdown",
            reply_markup=menu_recarga()
        )
        await update.message.reply_text("Ahora envía el monto que pagaste. Ejemplo: 10 o 15.50")
        return

    # ===== ADMIN PANEL =====
    if mensaje == "🛠 Admin" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = None
        await update.message.reply_text("🛠 Panel admin", reply_markup=menu_admin())
        return

    if mensaje == "📦 Ver stock" and es_admin(chat_id):
        texto_stock = (
            "📦 *Stock actual*\n\n"
            f"• Proxy 1 día: *{contar_stock('proxy_1dia.txt')}*\n"
            f"• Proxy 7 días: *{contar_stock('proxy_7dias.txt')}*\n"
            f"• Proxy 15 días: *{contar_stock('proxy_15dias.txt')}*\n"
            f"• Proxy 30 días: *{contar_stock('proxy_30dias.txt')}*"
        )
        await update.message.reply_text(texto_stock, parse_mode="Markdown")
        return

    if mensaje == "👥 Ver usuarios" and es_admin(chat_id):
        if not usuarios:
            await update.message.reply_text("No hay usuarios.")
            return

        txt = "👥 Usuarios:\n\n"
        for uname, data in usuarios.items():
            txt += f"• {uname} — ${data['saldo']:.2f}\n"
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

    if mensaje == "📥 Subir keys 1 día" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_1dia"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Subir keys 7 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_7dias"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Subir keys 15 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_15dias"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📥 Subir keys 30 días" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "subir_30dias"
        await update.message.reply_text("Pega las keys, una por línea.")
        return

    if mensaje == "📋 Solicitudes pendientes" and es_admin(chat_id):
        pendientes = obtener_solicitudes_pendientes()

        if not pendientes:
            await update.message.reply_text("No hay solicitudes pendientes.")
            return

        txt = "📋 Solicitudes pendientes:\n\n"
        for s in pendientes[:20]:
            txt += (
                f"ID: #{s['id']}\n"
                f"Usuario: {s['usuario']}\n"
                f"Método: {s['metodo']}\n"
                f"Monto: ${float(s['monto']):.2f}\n"
                f"Referencia: {s['referencia']}\n"
                f"Fecha: {s['fecha']}\n\n"
            )

        await update.message.reply_text(txt)
        await update.message.reply_text(
            "Para aprobar, envía el ID.\n"
            "Primero escribe: *aprobar* o *rechazar*",
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "Escribe:\n✅ aprobar\n❌ rechazar"
        )
        return

    if mensaje.lower() == "aprobar" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "admin_aprobar_solicitud"
        await update.message.reply_text("Envía el ID de la solicitud a aprobar.")
        return

    if mensaje.lower() == "rechazar" and es_admin(chat_id):
        sesiones[chat_id]["estado"] = "admin_rechazar_solicitud"
        await update.message.reply_text("Envía el ID de la solicitud a rechazar.")
        return

    # ===== DETALLE PRODUCTO =====
    if mensaje in PRODUCTOS:
        sesiones[chat_id]["producto_actual"] = mensaje
        await update.message.reply_text(
            texto_producto(user, mensaje),
            parse_mode="Markdown",
            reply_markup=menu_compra()
        )
        return

    # ===== COMPRAR =====
    if mensaje == "✅ Comprar una":
        producto_key = sesiones.get(chat_id, {}).get("producto_actual")

        if not producto_key or producto_key not in PRODUCTOS:
            await update.message.reply_text("Primero selecciona un producto.")
            return

        producto = PRODUCTOS[producto_key]
        precio = producto["precio"]
        archivo = producto["archivo"]
        nombre = producto["nombre"]

        if usuarios[user]["saldo"] < precio:
            await update.message.reply_text(
                f"Saldo insuficiente.\n\n"
                f"Precio: ${precio:.2f}\n"
                f"Tu saldo: ${usuarios[user]['saldo']:.2f}"
            )
            return

        stock_actual = contar_stock(archivo)
        if stock_actual <= 0:
            await update.message.reply_text("No hay stock disponible para este producto.")
            return

        key = sacar_primera_key(archivo)
        if not key:
            await update.message.reply_text("No hay stock disponible para este producto.")
            return

        usuarios[user]["saldo"] -= precio
        guardar_usuarios()

        agregar_historial(
            user,
            "compra",
            f"Compra de {nombre} | Key entregada: {key}",
            precio
        )

        await update.message.reply_text(
            f"✅ Compra exitosa\n\n"
            f"📦 Producto: {nombre}\n"
            f"🔑 Tu key:\n{key}\n\n"
            f"💰 Saldo restante: ${usuarios[user]['saldo']:.2f}",
            reply_markup=menu_principal(chat_id)
        )
        return


# =========================
# INICIO
# =========================
cargar_datos()

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("adduser", adduser))
app.add_handler(CommandHandler("addsaldo", addsaldo))
app.add_handler(CommandHandler("stock", stock))
app.add_handler(CommandHandler("addproxy1", addproxy1))
app.add_handler(CommandHandler("addproxy7", addproxy7))
app.add_handler(CommandHandler("addproxy15", addproxy15))
app.add_handler(CommandHandler("addproxy30", addproxy30))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto))

app.run_polling()
