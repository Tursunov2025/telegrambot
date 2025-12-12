import time
import json
import os
import telebot
from telebot import types

# ==========================
#  SOZLAMALAR
# ==========================
TOKEN = "8206184834:AAEPOLU65BRFOcmxzTYgLyvzmd_a6klr-qI"
BOT_NAME = "2D 3D chizmalar"

ACCESS_CODES = {
    "2d": "1111",
    "3d": "2222",
    "chz": "3333",
}

ADMIN_CODE = "9999"

bot = telebot.TeleBot(TOKEN)

# ==========================
#  DB FAYL (JSON)
# ==========================
if os.name == "nt":  # Windows
    DB_PATH = r"C:\telegrambot\db.json"
else:
    DB_PATH = "db.json"

folder = os.path.dirname(DB_PATH)
if folder and not os.path.exists(folder):
    os.makedirs(folder, exist_ok=True)


def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # eski strukturalarni to'g'rilab olamiz
            for pid, p in data.items():
                p.setdefault("name", pid)
                p.setdefault("files_2d", [])
                p.setdefault("files_3d", [])
                p.setdefault("profil", {str(i): [] for i in range(1, 11)})
                p.setdefault("listovoy", {str(i): [] for i in range(1, 11)})
            return data
        except Exception as e:
            print("DB ni o‘qishda xato:", e)
    return {}


def save_db():
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(PRODUCTS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("DB ni yozishda xato:", e)


PRODUCTS = load_db()

# ==========================
#  HOLATLAR
# ==========================
authorized_sections = {}  # chat_id -> set(["2d","3d","chz"])
authorized_admins = set()
waiting_for_code = {}  # chat_id -> section
admin_state = {}       # chat_id -> dict


# ==========================
#  YORDAMCHI FUNKSIYALAR
# ==========================
def is_admin(chat_id):
    return chat_id in authorized_admins


def build_main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📦 Izdeliyalar", callback_data="menu:products"))
    markup.add(types.InlineKeyboardButton("📐 2D", callback_data="menu:2d"))
    markup.add(types.InlineKeyboardButton("🧱 3D", callback_data="menu:3d"))
    markup.add(types.InlineKeyboardButton("📑 Chizmalar", callback_data="menu:chz"))
    return markup


def send_main_menu(chat_id):
    bot.send_message(chat_id, "👇 Bo‘limni tanlang:", reply_markup=build_main_menu())


def send_products_list(chat_id, text="📦 Izdeliyalar ro‘yxati:"):
    if not PRODUCTS:
        bot.send_message(chat_id, "📭 Hozircha izdeliyalar yo‘q.\n/admin → ➕ Izdelie qo‘shing.")
        return
    markup = types.InlineKeyboardMarkup()
    for pid, pdata in PRODUCTS.items():
        markup.add(types.InlineKeyboardButton(pdata["name"], callback_data=f"prod:{pid}"))
    markup.add(types.InlineKeyboardButton("⬅ Asosiy menyu", callback_data="back:main"))
    bot.send_message(chat_id, text, reply_markup=markup)


def build_product_menu(pid):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📐 2D", callback_data=f"view:2d:{pid}"),
        types.InlineKeyboardButton("🧱 3D", callback_data=f"view:3d:{pid}")
    )
    markup.add(types.InlineKeyboardButton("📑 Chizmalar", callback_data=f"view:chz:{pid}"))
    markup.add(types.InlineKeyboardButton("⬅ Izdeliyalar ro‘yxati", callback_data="menu:products"))
    return markup


def build_chz_menu(pid):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📊 Profil", callback_data=f"chz:profil:{pid}"),
        types.InlineKeyboardButton("📄 Listovoy", callback_data=f"chz:listovoy:{pid}")
    )
    markup.add(types.InlineKeyboardButton("⬅ Orqaga", callback_data=f"prod:{pid}"))
    return markup


def build_number_menu(pid, section):
    markup = types.InlineKeyboardMarkup()
    row = []
    for i in range(1, 11):
        row.append(types.InlineKeyboardButton(str(i), callback_data=f"chznum:{section}:{pid}:{i}"))
        if len(row) == 5:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    markup.add(types.InlineKeyboardButton("⬅ Orqaga", callback_data=f"chz:{section}:{pid}"))
    return markup


def require_access(chat_id, section):
    allowed = authorized_sections.get(chat_id, set())
    if section in allowed:
        return True
    waiting_for_code[chat_id] = section
    title = {"2d": "2D", "3d": "3D", "chz": "Chizmalar"}.get(section, section)
    bot.send_message(chat_id, f"🔐 {title} bo‘limi uchun kodni kiriting:")
    return False


def send_files(chat_id, title, files):
    if not files:
        bot.send_message(chat_id, f"{title} uchun fayl biriktirilmagan.")
        return
    bot.send_message(chat_id, f"{title} fayllari yuborilmoqda...")
    for f in files:
        try:
            bot.send_document(chat_id, f["id"])
        except Exception as e:
            print("Fayl yuborishda xato:", e)


def send_admin_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Izdelie qo‘shish", callback_data="admin:add_product"))
    markup.add(types.InlineKeyboardButton("📎 Fayl qo‘shish", callback_data="admin:add_file"))
    markup.add(types.InlineKeyboardButton("🧹 Fayl o‘chirish", callback_data="admin:del_file"))
    markup.add(types.InlineKeyboardButton("🗑 Izdelie o‘chirish", callback_data="admin:del_product"))
    markup.add(types.InlineKeyboardButton("⬅ Asosiy menyu", callback_data="back:main"))
    bot.send_message(chat_id, "🛠 Admin panel:", reply_markup=markup)


def build_delete_files_markup(pid, section, num=None):
    """
    section: "2d", "3d", "profil", "listovoy"
    """
    markup = types.InlineKeyboardMarkup()

    product = PRODUCTS.get(pid)
    if not product:
        return None

    if section == "2d":
        files = product["files_2d"]
    elif section == "3d":
        files = product["files_3d"]
    elif section == "profil":
        files = product["profil"].get(str(num), [])
    else:
        files = product["listovoy"].get(str(num), [])

    if not files:
        return None

    for idx, f in enumerate(files):
        label = f"📄 {f.get('name', 'No name')}"
        cb = f"adm_delfile:{pid}:{section}:{num if num is not None else 0}:{idx}"
        markup.add(types.InlineKeyboardButton(label, callback_data=cb))

    markup.add(types.InlineKeyboardButton("⬅ Bekor qilish", callback_data="back:admin"))
    return markup


# ==========================
#  COMMAND HANDLERS
# ==========================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        f"Assalomu alaykum!\n{BOT_NAME} botiga xush kelibsiz.",
        reply_markup=build_main_menu()
    )


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    chat_id = message.chat.id
    if is_admin(chat_id):
        send_admin_menu(chat_id)
    else:
        admin_state[chat_id] = {"mode": "wait_admin_code"}
        bot.send_message(chat_id, "🔐 Admin kodini kiriting:")


# ==========================
#  DOCUMENT HANDLER
# ==========================
@bot.message_handler(content_types=["document"])
def handle_document(message):
    chat_id = message.chat.id
    st = admin_state.get(chat_id)

    # Admin fayl qo'shish jarayonida
    if st and st.get("mode") == "wait_file_upload":
        pid = st["pid"]
        section = st["section"]
        num = st.get("num")
        fname = st["fname"]

        product = PRODUCTS.get(pid)
        if not product:
            bot.send_message(chat_id, "❌ Izdeliya topilmadi. Jarayon bekor qilindi.")
            admin_state.pop(chat_id, None)
            return

        file_obj = {"id": message.document.file_id, "name": fname}

        if section == "2d":
            product["files_2d"].append(file_obj)
            title = "2D"
        elif section == "3d":
            product["files_3d"].append(file_obj)
            title = "3D"
        elif section == "profil":
            product["profil"].setdefault(str(num), []).append(file_obj)
            title = f"Profil {num}"
        else:
            product["listovoy"].setdefault(str(num), []).append(file_obj)
            title = f"Listovoy {num}"

        save_db()
        admin_state.pop(chat_id, None)
        bot.send_message(chat_id, f"📎 Fayl '{fname}' {title} bo‘limiga saqlandi.")
        return

    # Oddiy holatda – faqat file_id ko‘rsatamiz
    bot.send_message(chat_id, "FILE ID:\n" + message.document.file_id)


# ==========================
#  TEXT HANDLER
# ==========================
@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # ---------- ADMIN STATE ----------
    if chat_id in admin_state:
        st = admin_state[chat_id]
        mode = st.get("mode")

        # Admin kod
        if mode == "wait_admin_code":
            if text == ADMIN_CODE:
                authorized_admins.add(chat_id)
                admin_state.pop(chat_id, None)
                bot.send_message(chat_id, "✅ Admin sifatida kirdingiz.")
                send_admin_menu(chat_id)
            else:
                bot.send_message(chat_id, "❌ Admin kodi noto‘g‘ri.")
            return

        # Izdeliya qo'shish: ID
        if mode == "add_product_id":
            pid = text.lower()
            if " " in pid:
                bot.send_message(chat_id, "ID ichida bo‘sh joy bo‘lmasin. Masalan: ss18_z3_mbu")
                return
            if pid in PRODUCTS:
                bot.send_message(chat_id, "Bu ID mavjud. Boshqa ID yozing:")
                return
            st["pid"] = pid
            st["mode"] = "add_product_name"
            bot.send_message(chat_id, "Yangi izdelie nomini kiriting:")
            return

        # Izdeliya qo'shish: nom
        if mode == "add_product_name":
            pid = st["pid"]
            name = text
            PRODUCTS[pid] = {
                "name": name,
                "files_2d": [],
                "files_3d": [],
                "profil": {str(i): [] for i in range(1, 11)},
                "listovoy": {str(i): [] for i in range(1, 11)},
            }
            save_db()
            admin_state.pop(chat_id, None)
            bot.send_message(chat_id, f"✅ Izdeliya qo‘shildi:\nID: {pid}\nNomi: {name}")
            return

        # Fayl qo'shish: ID
        if mode == "add_file_pid":
            pid = text.lower()
            if pid not in PRODUCTS:
                bot.send_message(chat_id, "❌ Bunaqa ID yo‘q. Qayta kiriting:")
                return
            st["pid"] = pid
            st["mode"] = "add_file_section"
            bot.send_message(
                chat_id,
                "Qaysi bo‘limga fayl qo‘shamiz?\nYozing: 2D, 3D, profil, listovoy"
            )
            return

        # Fayl qo'shish: bo'lim
        if mode == "add_file_section":
            sec = text.lower()
            if sec in ["2d", "2d chizma"]:
                st["section"] = "2d"
                st["mode"] = "add_file_name"
                bot.send_message(chat_id, "Fayl nomini kiriting (masalan: Stol 2D):")
                return
            if sec in ["3d", "3d chizma"]:
                st["section"] = "3d"
                st["mode"] = "add_file_name"
                bot.send_message(chat_id, "Fayl nomini kiriting (masalan: Stol 3D):")
                return
            if sec in ["profil", "profilniy"]:
                st["section"] = "profil"
                st["mode"] = "add_file_number"
                bot.send_message(chat_id, "Profil raqamini kiriting (1–10):")
                return
            if sec in ["list", "listovoy", "list chizma", "listovoy chizma"]:
                st["section"] = "listovoy"
                st["mode"] = "add_file_number"
                bot.send_message(chat_id, "Listovoy raqamini kiriting (1–10):")
                return
            bot.send_message(chat_id, "❌ Noto‘g‘ri bo‘lim. 2D / 3D / profil / listovoy deb yozing.")
            return

        # Fayl qo'shish: profil/list raqami
        if mode == "add_file_number":
            try:
                num = int(text)
            except ValueError:
                bot.send_message(chat_id, "Raqam kiriting (1–10).")
                return
            if not (1 <= num <= 10):
                bot.send_message(chat_id, "Raqam 1 dan 10 gacha bo‘lishi kerak.")
                return
            st["num"] = num
            st["mode"] = "add_file_name"
            bot.send_message(chat_id, "Fayl nomini kiriting:")
            return

        # Fayl qo'shish: nom
        if mode == "add_file_name":
            st["fname"] = text
            st["mode"] = "wait_file_upload"
            bot.send_message(chat_id, "📎 Faylni document ko‘rinishida yuboring.")
            return

        # Izdeliya o'chirish: ID
        if mode == "del_product_id":
            pid = text.lower()
            if pid not in PRODUCTS:
                bot.send_message(chat_id, "❌ Bunaqa ID yo‘q. Qayta kiriting:")
                return
            st["pid"] = pid
            st["mode"] = "del_product_confirm"
            bot.send_message(
                chat_id,
                f"🗑 Haqiqatan ham '{PRODUCTS[pid]['name']}' (ID: {pid}) ni o‘chiraymi?\n"
                "Javob: ha / yoq"
            )
            return

        # Izdeliya o'chirish: tasdiq
        if mode == "del_product_confirm":
            ans = text.lower()
            pid = st["pid"]
            if ans in ["ha", "xa", "yes", "да"]:
                PRODUCTS.pop(pid, None)
                save_db()
                bot.send_message(chat_id, "✅ Izdeliya o‘chirildi.")
            else:
                bot.send_message(chat_id, "Bekor qilindi.")
            admin_state.pop(chat_id, None)
            return

        # Fayl o'chirish: ID
        if mode == "del_file_pid":
            pid = text.lower()
            if pid not in PRODUCTS:
                bot.send_message(chat_id, "❌ Bunaqa ID yo‘q. Qayta kiriting:")
                return
            st["pid"] = pid
            st["mode"] = "del_file_section"
            bot.send_message(
                chat_id,
                "Qaysi bo‘limdan fayl o‘chiramiz?\nYozing: 2D, 3D, profil, listovoy"
            )
            return

        # Fayl o'chirish: bo'lim
        if mode == "del_file_section":
            sec = text.lower()
            if sec in ["2d", "2d chizma"]:
                st["section"] = "2d"
                markup = build_delete_files_markup(st["pid"], "2d")
                if markup is None:
                    bot.send_message(chat_id, "Bu bo‘limda fayl yo‘q.")
                    admin_state.pop(chat_id, None)
                else:
                    admin_state[chat_id] = {"mode": "idle"}  # keyingi bosqich callback orqali
                    bot.send_message(chat_id, "O‘chirish uchun faylni tanlang:", reply_markup=markup)
                return
            if sec in ["3d", "3d chizma"]:
                st["section"] = "3d"
                markup = build_delete_files_markup(st["pid"], "3d")
                if markup is None:
                    bot.send_message(chat_id, "Bu bo‘limda fayl yo‘q.")
                    admin_state.pop(chat_id, None)
                else:
                    admin_state[chat_id] = {"mode": "idle"}
                    bot.send_message(chat_id, "O‘chirish uchun faylni tanlang:", reply_markup=markup)
                return
            if sec in ["profil", "profilniy"]:
                st["section"] = "profil"
                st["mode"] = "del_file_number"
                bot.send_message(chat_id, "Profil raqamini kiriting (1–10):")
                return
            if sec in ["list", "listovoy", "list chizma", "listovoy chizma"]:
                st["section"] = "listovoy"
                st["mode"] = "del_file_number"
                bot.send_message(chat_id, "Listovoy raqamini kiriting (1–10):")
                return
            bot.send_message(chat_id, "❌ Noto‘g‘ri bo‘lim. 2D / 3D / profil / listovoy deb yozing.")
            return

        # Fayl o'chirish: profil/list raqami
        if mode == "del_file_number":
            try:
                num = int(text)
            except ValueError:
                bot.send_message(chat_id, "Raqam kiriting (1–10).")
                return
            if not (1 <= num <= 10):
                bot.send_message(chat_id, "Raqam 1 dan 10 gacha bo‘lishi kerak.")
                return
            pid = st["pid"]
            section = st["section"]
            markup = build_delete_files_markup(pid, section, num)
            if markup is None:
                bot.send_message(chat_id, "Bu raqamda fayl yo‘q.")
                admin_state.pop(chat_id, None)
            else:
                admin_state[chat_id] = {"mode": "idle"}  # keyingi bosqich callback
                bot.send_message(chat_id, "O‘chirish uchun faylni tanlang:", reply_markup=markup)
            return

        # Fayl o'chirish tasdiq
        if mode == "del_file_confirm":
            ans = text.lower()
            if ans in ["ha", "xa", "yes", "да"]:
                pid = st["pid"]
                section = st["section"]
                num = st.get("num")
                idx = st["idx"]
                product = PRODUCTS.get(pid)
                if product:
                    if section == "2d":
                        if 0 <= idx < len(product["files_2d"]):
                            del product["files_2d"][idx]
                    elif section == "3d":
                        if 0 <= idx < len(product["files_3d"]):
                            del product["files_3d"][idx]
                    elif section == "profil":
                        arr = product["profil"].get(str(num), [])
                        if 0 <= idx < len(arr):
                            del arr[idx]
                    else:
                        arr = product["listovoy"].get(str(num), [])
                        if 0 <= idx < len(arr):
                            del arr[idx]
                    save_db()
                    bot.send_message(chat_id, "✅ Fayl o‘chirildi.")
                else:
                    bot.send_message(chat_id, "Izdeliya topilmadi.")
            else:
                bot.send_message(chat_id, "Bekor qilindi.")
            admin_state.pop(chat_id, None)
            return

        # boshqa admin mode larni hozircha e'tibordan chetda qoldiramiz
        # shuning uchun return
        return

    # ---------- ACCESS KODI ----------
    if chat_id in waiting_for_code:
        section = waiting_for_code[chat_id]
        if text == ACCESS_CODES.get(section):
            allowed = authorized_sections.get(chat_id, set())
            allowed.add(section)
            authorized_sections[chat_id] = allowed
            waiting_for_code.pop(chat_id, None)
            title = {"2d": "2D", "3d": "3D", "chz": "Chizmalar"}.get(section, section)
            bot.send_message(chat_id, f"✅ Kod to‘g‘ri. Endi {title} bo‘limiga kira olasiz.")
        else:
            bot.send_message(chat_id, "❌ Kod noto‘g‘ri.")
        return

    # ---------- QIDIRUV ----------
    query = text.lower()
    results = []
    for pid, pdata in PRODUCTS.items():
        if query in pid.lower() or query in pdata["name"].lower():
            results.append((pid, pdata["name"]))

    if not results:
        bot.send_message(chat_id, "Topilmadi!")
        return

    markup = types.InlineKeyboardMarkup()
    for pid, name in results:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"prod:{pid}"))
    bot.send_message(chat_id, "Topilgan izdeliyalar:", reply_markup=markup)


# ==========================
#  CALLBACK HANDLER
# ==========================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data.split(":")

    try:
        # Asosiy menyuga qaytish
        if data[0] == "back":
            if data[1] == "main":
                send_main_menu(chat_id)
            elif data[1] == "admin":
                send_admin_menu(chat_id)
            bot.answer_callback_query(call.id)
            return

        # Asosiy menyu tugmalari
        if data[0] == "menu":
            section = data[1]
            if section == "products":
                send_products_list(chat_id)
            elif section in ["2d", "3d", "chz"]:
                if not require_access(chat_id, section):
                    pass
                else:
                    send_products_list(chat_id, "📦 Izdeliya tanlang:")
            bot.answer_callback_query(call.id)
            return

        # Admin panel tugmalari
        if data[0] == "admin":
            if not is_admin(chat_id):
                bot.answer_callback_query(call.id, "Siz admin emassiz.")
                return

            action = data[1]
            if action == "add_product":
                admin_state[chat_id] = {"mode": "add_product_id"}
                bot.send_message(chat_id, "🆕 Yangi izdelie ID sini kiriting (masalan: ss18_z3_mbu):")
            elif action == "add_file":
                admin_state[chat_id] = {"mode": "add_file_pid"}
                bot.send_message(chat_id, "Qaysi izdeliega fayl qo‘shamiz? ID sini kiriting:")
            elif action == "del_product":
                admin_state[chat_id] = {"mode": "del_product_id"}
                bot.send_message(chat_id, "O‘chirmoqchi bo‘lgan izdelie ID sini kiriting:")
            elif action == "del_file":
                admin_state[chat_id] = {"mode": "del_file_pid"}
                bot.send_message(chat_id, "Qaysi izdeliedan fayl o‘chiramiz? ID sini kiriting:")
            bot.answer_callback_query(call.id)
            return

        # Izdelie tanlandi
        if data[0] == "prod":
            pid = data[1]
            product = PRODUCTS.get(pid)
            if not product:
                bot.answer_callback_query(call.id, "Izdeliya topilmadi.")
                return
            bot.send_message(chat_id, product["name"], reply_markup=build_product_menu(pid))
            bot.answer_callback_query(call.id)
            return

        # 2D / 3D / Chizmalar ko'rsatish
        if data[0] == "view":
            section = data[1]
            pid = data[2]
            product = PRODUCTS.get(pid)
            if not product:
                bot.answer_callback_query(call.id, "Izdeliya topilmadi.")
                return

            if not require_access(chat_id, section):
                bot.answer_callback_query(call.id)
                return

            if section == "2d":
                send_files(chat_id, f"{product['name']} – 2D", product["files_2d"])
            elif section == "3d":
                send_files(chat_id, f"{product['name']} – 3D", product["files_3d"])
            else:
                bot.send_message(
                    chat_id,
                    f"{product['name']} – chizmalar turini tanlang:",
                    reply_markup=build_chz_menu(pid)
                )
            bot.answer_callback_query(call.id)
            return

        # Chizmalar bo'limi tanlash (profil/listovoy)
        if data[0] == "chz":
            section = data[1]
            pid = data[2]
            product = PRODUCTS.get(pid)
            if not product:
                bot.answer_callback_query(call.id, "Izdeliya topilmadi.")
                return

            if not require_access(chat_id, "chz"):
                bot.answer_callback_query(call.id)
                return

            bot.send_message(
                chat_id,
                f"{product['name']} – {section} raqamini tanlang:",
                reply_markup=build_number_menu(pid, section)
            )
            bot.answer_callback_query(call.id)
            return

        # Profil / Listovoy raqam fayllarini yuborish
        if data[0] == "chznum":
            section = data[1]
            pid = data[2]
            num = data[3]
            product = PRODUCTS.get(pid)
            if not product:
                bot.answer_callback_query(call.id, "Izdeliya topilmadi.")
                return

            if not require_access(chat_id, "chz"):
                bot.answer_callback_query(call.id)
                return

            if section == "profil":
                files = product["profil"].get(num, [])
                title = f"{product['name']} – Profil {num}"
            else:
                files = product["listovoy"].get(num, [])
                title = f"{product['name']} – Listovoy {num}"

            send_files(chat_id, title, files)
            bot.answer_callback_query(call.id)
            return

        # Admin – fayl o'chirish tugmasi bosilgan
        if data[0] == "adm_delfile":
            pid = data[1]
            section = data[2]
            num = int(data[3]) if data[3] != "0" else None
            idx = int(data[4])

            product = PRODUCTS.get(pid)
            if not product:
                bot.answer_callback_query(call.id, "Izdeliya topilmadi.")
                return

            # Fayl nomini topamiz
            if section == "2d":
                arr = product["files_2d"]
            elif section == "3d":
                arr = product["files_3d"]
            elif section == "profil":
                arr = product["profil"].get(str(num), [])
            else:
                arr = product["listovoy"].get(str(num), [])

            if not (0 <= idx < len(arr)):
                bot.answer_callback_query(call.id, "Fayl topilmadi.")
                return

            fname = arr[idx].get("name", "no-name")
            admin_state[chat_id] = {
                "mode": "del_file_confirm",
                "pid": pid,
                "section": section,
                "num": num,
                "idx": idx,
                "fname": fname,
            }
            bot.send_message(chat_id, f"🧹 '{fname}' faylini o‘chiraymi?\nJavob: ha / yoq")
            bot.answer_callback_query(call.id)
            return

    except Exception as e:
        print("Callback xato:", e)
        try:
            bot.answer_callback_query(call.id, "Xato yuz berdi.")
        except Exception:
            pass


# ==========================
#  BOTNI ISHGA TUSHIRISH
# ==========================
while True:
    try:
        print("Bot ishga tushdi...")
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print("Polling xato:", e)
        time.sleep(5)
