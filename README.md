# Telegram Bot — VS Code Ready

## Tez start (VS Code)
1) **Zipni oching** va papkani VS Code’da `File → Open Folder…` bilan oching.
2) `.env.example` faylini nusxa ko‘chiring va nomini `.env` qilib, quyidagilarni to‘ldiring:
   - `BOT_TOKEN` — BotFather tokeni
   - `ADMIN_IDS` — admin IDlar (vergul bilan)
   - `MASTER_PIN`, `FILE_PIN` — parollar
3) **Python extension** o‘rnatilgan bo‘lsin (MS Python).
4) VS Code pastda `Python` interpreterni tanlab, `./.venv`dagi interpreterni belgilang (agar yo‘q bo‘lsa, quyida venv yaratish bo‘limiga qarang).
5) `Run and Debug` (Ctrl+Shift+D) → **Run Bot** ni tanlang → **Start Debugging** (F5).

## Venv yaratish (agar avtomatik aniqlanmasa)
**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Qo'lda ishga tushirish
```bash
python bot.py
```

## Admin
`/admin` orqali kategoriya/fayl/PIN/Statistika/Ishchilar nazorati boshqariladi.

> Fayl qo'shish: admin panel → kategoriya → tur (2D/3D/Listovoy/Profilniy) → hujjatni **document** sifatida yuboring.
