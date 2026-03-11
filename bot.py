from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime

TOKEN = "8733783250:AAEKLrNpzEPvItVTpJRSTeLv3QDUOXdS0Xg"
ADMIN_ID = 8179362627

usuarios = {}
sesiones = {}

PRODUCTOS = {
    "📅 1 día - $1.50": {
        "precio": 1.50,
        "archivo": "proxy_1dia.txt",
        "nombre": "PROXY 1 DÍA",
        "validez": "1 día"
    },
    "📆 7 días - $5": {
        "precio": 5.00,
        "archivo": "proxy_7dias.txt",
        "nombre": "PROXY 7 DÍAS",
        "validez": "7 días"
    },
    "🗓 15 días - $8": {
        "precio": 8.00,
        "archivo": "proxy_15dias.txt",
        "nombre": "PROXY 15 DÍAS",
        "validez": "15 días"
    },
    "🗓 30 días - $12": {
        "precio": 12.00,
        "archivo": "proxy_30dias.txt",
        "nombre": "PROXY 30 DÍAS",
        "validez": "30 días"
    },
}


def menu_principal():
    teclado = [
        ["🛍 Productos", "💰 Mi saldo"],
        ["📜 Historial", "👤 Mi perfil"],
        ["🚪 Cerrar sesión"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_productos():
    teclado = [
        ["🌐 Proxy"],
        ["🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_proxy():
    teclado = [
        ["📅 1 día - $1.50", "📆 7 días - $5"],
        ["🗓 15 días - $8", "🗓 30 días - $12"],
        ["⬅️ Volver a productos", "🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def menu_compra():
    teclado = [
        ["✅ Comprar una"],
        ["⬅️ Volver a productos", "🏠 Menú"]
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


def guardar_usuarios():
    with open("users.txt", "w", encoding="utf-8") as f:
        for user, data in usuarios.items():
            telegram_id = data["telegram_id"] if data["telegram_id"] is not None else ""
            f.write(f'{user}|{data["password"]}|{data["saldo"]}|{telegram_id}\n')


def cargar_usuarios():
    global usuarios
    usuarios = {}

    try:
        with open("users.txt", "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue

                partes = linea.split("|")
                if len(partes) != 4:
                    continue

                user, password, saldo, telegram_id = partes
                usuarios[user] = {
                    "password": password,
                    "saldo": float(saldo),
                    "telegram_id": int(telegram_id) if telegram_id else None
                }
    except FileNotFoundError:
        pass


def sacar_primera_key(archivo):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            keys = [k.strip() for k in f.readlines() if k.strip()]

        if not keys:
            return None

        primera = keys[0]

        with open(archivo, "w", encoding="utf-8") as f:
            for key in keys[1:]:
                f.write(key + "\n")

        return primera
    except FileNotFoundError:
        return None


def contar_stock(archivo):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            keys = [k.strip() for k in f.readlines() if k.strip()]
        return len(keys)
    except FileNotFoundError:
        return 0


def guardar_historial(usuario, producto, precio, key):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("history.txt", "a", encoding="utf-8") as f:
        f.write(f"{fecha}|{usuario}|{producto}|{precio}|{key}\n")


def obtener_historial_usuario(usuario):
    historial = []
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue

                partes = linea.split("|")
                if len(partes) != 5:
                    continue

                fecha, user, producto, precio, key = partes
                if user == usuario:
                    historial.append({
                        "fecha": fecha,
                        "producto": producto,
                        "precio": precio,
                        "key": key
                    })
    except FileNotFoundError:
        pass

    return historial[-10:]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in sesiones and sesiones[chat_id].get("logueado"):
        usuario = sesiones[chat_id]["usuario"]
        saldo = usuarios[usuario]["saldo"]

        mensaje = (
            f"🏠 Menú Principal\n\n"
            f"💰 Saldo: ${saldo:.2f} USD\n"
            f"👤 Usuario: {usuario}\n\n"
            f"Selecciona una opción:"
        )

        await update.message.reply_text(
            mensaje,
            reply_markup=menu_principal()
        )
        return

    sesiones[chat_id] = {"estado": "esperando_usuario"}

    await update.message.reply_text(
        "👋 Bienvenido a Tommy Keys\n\nIngresa tu usuario:",
        reply_markup=ReplyKeyboardRemove()
    )


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
            usuario = sesiones[chat_id].get("usuario_temp")

            if usuario not in usuarios:
                sesiones.pop(chat_id, None)
                await update.message.reply_text("Usuario incorrecto.")
                return

            if usuarios[usuario]["password"] != mensaje:
                sesiones.pop(chat_id, None)
                await update.message.reply_text("Contraseña incorrecta.")
                return

            usuarios[usuario]["telegram_id"] = chat_id
            guardar_usuarios()

            sesiones[chat_id] = {
                "logueado": True,
                "usuario": usuario,
                "menu": "principal"
            }

            saldo = usuarios[usuario]["saldo"]

            mensaje_bienvenida = (
                f"🏠 Menú Principal\n\n"
                f"💰 Saldo: ${saldo:.2f} USD\n"
                f"👤 Usuario: {usuario}\n\n"
                f"Selecciona una opción:"
            )

            await update.message.reply_text(
                mensaje_bienvenida,
                reply_markup=menu_principal()
            )
            return

    # USUARIO LOGUEADO
    if chat_id in sesiones and sesiones[chat_id].get("logueado"):
        usuario = sesiones[chat_id]["usuario"]

        if mensaje == "🏠 Menú":
            sesiones[chat_id]["menu"] = "principal"
            saldo = usuarios[usuario]["saldo"]

            await update.message.reply_text(
                f"🏠 Menú Principal\n\n"
                f"💰 Saldo: ${saldo:.2f} USD\n"
                f"👤 Usuario: {usuario}\n\n"
                f"Selecciona una opción:",
                reply_markup=menu_principal()
            )
            return

        if mensaje == "🛍 Productos":
            sesiones[chat_id]["menu"] = "productos"
            await update.message.reply_text(
                "🛍 Productos\n\nSelecciona una categoría:",
                reply_markup=menu_productos()
            )
            return

        if mensaje == "🌐 Proxy":
            sesiones[chat_id]["menu"] = "proxy"
            await update.message.reply_text(
                "🌐 Proxy\n\nSelecciona un plan:",
                reply_markup=menu_proxy()
            )
            return

        if mensaje == "⬅️ Volver a productos":
            sesiones[chat_id]["menu"] = "productos"
            await update.message.reply_text(
                "🛍 Productos\n\nSelecciona una categoría:",
                reply_markup=menu_productos()
            )
            return

        if mensaje == "💰 Mi saldo":
            await update.message.reply_text(
                f"💰 Tu saldo actual es: ${usuarios[usuario]['saldo']:.2f} USD"
            )
            return

        if mensaje == "👤 Mi perfil":
            await update.message.reply_text(
                f"👤 Usuario: {usuario}\n💰 Saldo: ${usuarios[usuario]['saldo']:.2f} USD"
            )
            return

        if mensaje == "📜 Historial":
            historial = obtener_historial_usuario(usuario)

            if not historial:
                await update.message.reply_text("📜 No tienes compras en tu historial.")
                return

            texto_historial = "📜 Últimas compras:\n\n"
            for item in historial:
                texto_historial += (
                    f"🕒 {item['fecha']}\n"
                    f"📦 {item['producto']}\n"
                    f"💵 ${item['precio']}\n\n"
                )

            await update.message.reply_text(texto_historial)
            return

        if mensaje == "🚪 Cerrar sesión":
            sesiones.pop(chat_id, None)
            await update.message.reply_text(
                "Sesión cerrada.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # MOSTRAR DETALLE DEL PRODUCTO CON STOCK
        if mensaje in PRODUCTOS:
            producto = PRODUCTOS[mensaje]
            precio = producto["precio"]
            archivo = producto["archivo"]
            nombre_producto = producto["nombre"]
            validez = producto["validez"]

            stock = contar_stock(archivo)
            saldo_usuario = usuarios[usuario]["saldo"]

            sesiones[chat_id]["producto_actual"] = mensaje
            sesiones[chat_id]["menu"] = "detalle_producto"

            texto_producto = (
                f"📦 {nombre_producto}\n\n"
                f"💵 Precio: ${precio:.2f} USD\n"
                f"📦 Stock: {stock} disponibles\n"
                f"⏱ Validez: {validez}\n\n"
                f"💰 Tu saldo: ${saldo_usuario:.2f} USD\n\n"
                f"¿Qué deseas hacer?"
            )

            await update.message.reply_text(
                texto_producto,
                reply_markup=menu_compra()
            )
            return

        # COMPRAR UNA
        if mensaje == "✅ Comprar una":
            if "producto_actual" not in sesiones[chat_id]:
                await update.message.reply_text("Primero selecciona un producto.")
                return

            producto_boton = sesiones[chat_id]["producto_actual"]
            producto = PRODUCTOS[producto_boton]
            precio = producto["precio"]
            archivo = producto["archivo"]
            nombre_producto = producto["nombre"]

            if usuarios[usuario]["saldo"] < precio:
                await update.message.reply_text(
                    f"Saldo insuficiente.\n\n"
                    f"Precio: ${precio:.2f}\n"
                    f"Tu saldo: ${usuarios[usuario]['saldo']:.2f}"
                )
                return

            stock = contar_stock(archivo)
            if stock <= 0:
                await update.message.reply_text("No hay stock disponible para este producto.")
                return

            key = sacar_primera_key(archivo)
            if not key:
                await update.message.reply_text("No hay stock disponible para este producto.")
                return

            usuarios[usuario]["saldo"] -= precio
            guardar_usuarios()
            guardar_historial(usuario, nombre_producto, f"{precio:.2f}", key)

            await update.message.reply_text(
                f"✅ Compra exitosa\n\n"
                f"📦 Producto: {nombre_producto}\n"
                f"🔑 Tu key:\n{key}\n\n"
                f"💰 Saldo restante: ${usuarios[usuario]['saldo']:.2f}",
                reply_markup=menu_principal()
            )
            sesiones[chat_id]["menu"] = "principal"
            return


# COMANDOS ADMIN SOLO POR TEXTO
async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /adduser usuario contraseña")
        return

    user = context.args[0]
    password = context.args[1]

    if user in usuarios:
        await update.message.reply_text("Ese usuario ya existe.")
        return

    usuarios[user] = {
        "password": password,
        "saldo": 0.0,
        "telegram_id": None
    }
    guardar_usuarios()

    await update.message.reply_text(f"Usuario creado: {user}")


async def addsaldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Uso: /addsaldo usuario monto")
        return

    user = context.args[0]

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

    await update.message.reply_text(
        f"Saldo agregado a {user}. Nuevo saldo: ${usuarios[user]['saldo']:.2f}"
    )


async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return

    texto_stock = (
        f"📦 Stock actual:\n\n"
        f"Proxy 1 día: {contar_stock('proxy_1dia.txt')}\n"
        f"Proxy 7 días: {contar_stock('proxy_7dias.txt')}\n"
        f"Proxy 15 días: {contar_stock('proxy_15dias.txt')}\n"
        f"Proxy 30 días: {contar_stock('proxy_30dias.txt')}"
    )
    await update.message.reply_text(texto_stock)


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

    await update.message.reply_text(f"Key agregada correctamente a {nombre}.")


cargar_usuarios()

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