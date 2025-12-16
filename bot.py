import os
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ============ SOZLAMALAR ============
TELEGRAM_TOKEN = "7810689974:AAHPi82rDBgexaDG2hmNEGg88Nu6DOwQxRg"
GROQ_API_KEY = "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"  # https://console.groq.com/keys dan oling (BEPUL!)

# GROQ API URL
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ============ MA'LUMOTLAR BAZASI ============
class SimpleDB:
    def __init__(self, filename='bot_data.json'):
        self.filename = filename
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'users': {},
            'reminders': {},
            'conversations': {},
            'code_snippets': {}
        }
    
    def save_data(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_user(self, user_id):
        user_id = str(user_id)
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {
                'name': '',
                'started': datetime.now().isoformat(),
                'message_count': 0,
                'code_count': 0
            }
            self.save_data()
        return self.data['users'][user_id]
    
    def add_reminder(self, user_id, reminder):
        user_id = str(user_id)
        if user_id not in self.data['reminders']:
            self.data['reminders'][user_id] = []
        self.data['reminders'][user_id].append({
            'text': reminder,
            'created': datetime.now().isoformat()
        })
        self.save_data()
    
    def get_reminders(self, user_id):
        return self.data['reminders'].get(str(user_id), [])
    
    def clear_reminders(self, user_id):
        self.data['reminders'][str(user_id)] = []
        self.save_data()
    
    def save_conversation(self, user_id, message, response):
        user_id = str(user_id)
        if user_id not in self.data['conversations']:
            self.data['conversations'][user_id] = []
        self.data['conversations'][user_id].append({
            'user': message,
            'bot': response,
            'time': datetime.now().isoformat()
        })
        self.data['conversations'][user_id] = self.data['conversations'][user_id][-50:]
        self.save_data()
    
    def get_conversation_history(self, user_id):
        return self.data['conversations'].get(str(user_id), [])
    
    def save_code_snippet(self, user_id, code, language):
        user_id = str(user_id)
        if user_id not in self.data['code_snippets']:
            self.data['code_snippets'][user_id] = []
        self.data['code_snippets'][user_id].append({
            'code': code,
            'language': language,
            'created': datetime.now().isoformat()
        })
        self.data['code_snippets'][user_id] = self.data['code_snippets'][user_id][-50:]
        self.save_data()

db = SimpleDB()

# ============ GROQ AI FUNKSIYALARI ============
async def ask_groq(message: str, user_id: str, system_prompt: str = "Sen foydali AI yordamchisan.") -> str:
    """GROQ AI dan javob olish - JUDA TEZ VA BEPUL!"""
    try:
        # Oldingi suhbatlarni olish
        history = db.get_conversation_history(user_id)[-10:]
        
        # Xabarlarni tayyorlash
        messages = [{"role": "system", "content": system_prompt}]
        
        for item in history:
            messages.append({"role": "user", "content": item['user']})
            messages.append({"role": "assistant", "content": item['bot']})
        
        messages.append({"role": "user", "content": message})
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",  # Eng yaxshi model!
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 0.9
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
                return text.strip()
            return "❌ Javob olmadim."
        
        elif response.status_code == 401:
            return "❌ API kalit noto'g'ri! https://console.groq.com/keys dan yangi kalit oling."
        
        elif response.status_code == 429:
            return "⏳ Rate limit! Bir oz kuting va qayta urinib ko'ring."
        
        else:
            return f"❌ Xatolik: {response.status_code}"
    
    except requests.exceptions.Timeout:
        return "⏱️ Vaqt tugadi. Qayta urinib ko'ring."
    except Exception as e:
        return f"❌ Xatolik: {str(e)}"

async def generate_code(task: str, language: str = "python") -> str:
    """Kod yaratish"""
    system_prompt = f"Sen professional dasturchi yordamchisan. {language} tilida kod yoz. Faqat kod, boshqa gap kerak emas."
    return await ask_groq(f"Vazifa: {task}", "code_gen", system_prompt)

async def translate_text(text: str, target_lang: str) -> str:
    """Matnni tarjima qilish"""
    system_prompt = "Sen professional tarjimonsan. Faqat tarjimani yoz, boshqa gap kerak emas."
    return await ask_groq(f"Quyidagi matnni {target_lang} tiliga tarjima qil:\n\n{text}", "translator", system_prompt)

async def summarize_text(text: str) -> str:
    """Matnni qisqacha qilish"""
    system_prompt = "Sen matnlarni qisqartirish mutaxassisisan. Qisqacha va aniq xulosa ber."
    return await ask_groq(f"Quyidagi matnning xulosasini ber:\n\n{text}", "summarizer", system_prompt)

async def get_creative_response(prompt: str) -> str:
    """Ijodiy javoblar"""
    system_prompt = "Sen ijodiy yozuvchi va she'rsonsan. Ijodiy, qiziqarli va original javoblar ber."
    return await ask_groq(prompt, "creative", system_prompt)

async def fix_code(code: str, error: str = "") -> str:
    """Kodni tuzatish"""
    system_prompt = "Sen dasturchi yordamchisan. Koddagi xatolarni top va tuzat."
    prompt = f"Koddagi xatolarni top va tuzat:\n\n```\n{code}\n```"
    if error:
        prompt += f"\n\nXatolik: {error}"
    return await ask_groq(prompt, "debugger", system_prompt)

# ============ MATEMATIK HISOB-KITOB ============
def calculate(expression: str) -> str:
    """Matematik ifodalarni hisoblash"""
    try:
        allowed_chars = "0123456789+-*/()., "
        if not all(c in allowed_chars for c in expression):
            return "❌ Faqat raqamlar va +, -, *, /, () ishlatish mumkin"
        
        result = eval(expression)
        return f"✅ Javob: {result}"
    except Exception as e:
        return f"❌ Hisoblashda xatolik: {str(e)}"

# ============ TELEGRAM BUYRUQLARI ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🤖 AI Chat", callback_data='ai'),
         InlineKeyboardButton("💻 Kod yaratish", callback_data='code')],
        [InlineKeyboardButton("🔧 Kodni tuzatish", callback_data='fix'),
         InlineKeyboardButton("🌍 Tarjima", callback_data='translate')],
        [InlineKeyboardButton("📝 Xulosa", callback_data='summary'),
         InlineKeyboardButton("✨ Ijodiy", callback_data='creative')],
        [InlineKeyboardButton("🧮 Hisob", callback_data='calc'),
         InlineKeyboardButton("📌 Eslatmalar", callback_data='reminders')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats'),
         InlineKeyboardButton("ℹ️ Yordam", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Assalomu alaykum, {user.first_name}!

Men **GROQ AI** yordamchisiman! 

⚡ **ENG TEZ AI!**

🤖 **AI Chat** - Har qanday savol (Llama 3.3 70B)
💻 **Kod yozish** - Har qanday til
🔧 **Debug** - Xatolarni topish va tuzatish
🌍 **Tarjima** - 100+ til
📝 **Xulosa** - Matnni qisqartirish
✨ **Ijodiy** - She'r, hikoya, maqola
🧮 **Hisob-kitob** - Matematik masalalar
📌 **Eslatmalar** - Vazifalarni eslab qolish

💡 Menga xabar yuboring!
🆓 **100% BEPUL va eng tez!**
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 **YORDAM**

**Buyruqlar:**
/start - Boshlash
/help - Yordam
/code [vazifa] - Kod yaratish
/fix [kod] - Kodni tuzatish
/translate [til] [matn] - Tarjima
/summary [matn] - Xulosa
/creative [vazifa] - Ijodiy yozish
/calc [ifoda] - Hisoblash
/reminder [matn] - Eslatma
/myreminders - Eslatmalarni ko'rish
/clear - Eslatmalarni o'chirish
/stats - Statistika

**AI Chat:**
Shunchaki xabar yuboring!

**Misollar:**
• "Python da list nima?"
• "/code calculator dasturi"
• "/translate inglizcha Salom"
• "/creative She'r yoz"

⚡ GROQ AI - Eng tez va bepul!
    """
    await update.message.reply_text(help_text)

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Vazifa kiriting!\n\nMisol: /code calculator")
        return
    
    task = ' '.join(context.args)
    await update.message.chat.send_action(action="typing")
    
    code = await generate_code(task)
    db.save_code_snippet(update.effective_user.id, code, "python")
    
    await update.message.reply_text(f"💻 **Kod:**\n\n{code}")

async def fix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Kodni kiriting!\n\nMisol: /fix print('salom)")
        return
    
    code = ' '.join(context.args)
    await update.message.chat.send_action(action="typing")
    
    fixed = await fix_code(code)
    await update.message.reply_text(f"🔧 **Tuzatildi:**\n\n{fixed}")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Til va matn kiriting!\n\nMisol: /translate inglizcha Salom")
        return
    
    target_lang = context.args[0]
    text = ' '.join(context.args[1:])
    await update.message.chat.send_action(action="typing")
    
    translation = await translate_text(text, target_lang)
    await update.message.reply_text(f"🌍 **Tarjima:**\n\n{translation}")

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Matn kiriting!")
        return
    
    text = ' '.join(context.args)
    await update.message.chat.send_action(action="typing")
    
    summary = await summarize_text(text)
    await update.message.reply_text(f"📝 **Xulosa:**\n\n{summary}")

async def creative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Vazifa kiriting!\n\nMisol: /creative she'r yoz")
        return
    
    prompt = ' '.join(context.args)
    await update.message.chat.send_action(action="typing")
    
    creative = await get_creative_response(prompt)
    await update.message.reply_text(f"✨ **Ijodiy:**\n\n{creative}")

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Ifoda kiriting!\n\nMisol: /calc 2+2*5")
        return
    
    expression = ' '.join(context.args)
    result = calculate(expression)
    await update.message.reply_text(f"🧮 {expression} = {result}")

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Matn kiriting!\n\nMisol: /reminder Darsga borish")
        return
    
    reminder_text = ' '.join(context.args)
    db.add_reminder(update.effective_user.id, reminder_text)
    await update.message.reply_text(f"✅ Saqlandi:\n\n📌 {reminder_text}")

async def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = db.get_reminders(update.effective_user.id)
    
    if not reminders:
        await update.message.reply_text("📝 Eslatmalar yo'q.")
        return
    
    text = "📝 **Eslatmalar:**\n\n"
    for i, rem in enumerate(reminders, 1):
        text += f"{i}. {rem['text']}\n"
    
    await update.message.reply_text(text)

async def clear_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.clear_reminders(update.effective_user.id)
    await update.message.reply_text("✅ O'chirildi!")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = db.get_user(update.effective_user.id)
    reminders = db.get_reminders(update.effective_user.id)
    conversations = db.get_conversation_history(update.effective_user.id)
    
    stats_text = f"""
📊 **STATISTIKA**

👤 {update.effective_user.first_name}
📅 {user_data['started'][:10]}
💬 Xabarlar: {user_data['message_count']}
💻 Kodlar: {user_data.get('code_count', 0)}
📝 Eslatmalar: {len(reminders)}
🗨️ Suhbatlar: {len(conversations)}

🤖 GROQ AI - Llama 3.3 70B
⚡ Eng tez AI!
🆓 100% Bepul
    """
    await update.message.reply_text(stats_text)

# ============ XABARLAR ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    user_data = db.get_user(user_id)
    user_data['message_count'] += 1
    db.save_data()
    
    # Hisob-kitob tekshirish
    if any(op in user_message for op in ['+', '-', '*', '/', '=']):
        calc_expr = user_message.replace('=', '').replace('?', '').strip()
        clean = calc_expr.replace(' ', '').replace('+', '').replace('-', '').replace('*', '').replace('/', '').replace('(', '').replace(')', '').replace('.', '')
        if clean.replace('-', '').isdigit():
            result = calculate(calc_expr)
            await update.message.reply_text(result)
            return
    
    await update.message.chat.send_action(action="typing")
    
    response = await ask_groq(user_message, user_id)
    db.save_conversation(user_id, user_message, response)
    
    await update.message.reply_text(response)

# ============ CALLBACK ============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    responses = {
        'ai': "🤖 Menga savol bering!",
        'code': "💻 /code [vazifa]",
        'fix': "🔧 /fix [kod]",
        'translate': "🌍 /translate [til] [matn]",
        'summary': "📝 /summary [matn]",
        'creative': "✨ /creative [vazifa]",
        'calc': "🧮 /calc [ifoda]",
        'reminders': None,
        'stats': None,
        'help': None
    }
    
    if query.data == 'reminders':
        await show_reminders(update, context)
    elif query.data == 'stats':
        await stats(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    else:
        await query.message.reply_text(responses.get(query.data, "❌"))

# ============ ASOSIY ============
def main():
    print("🚀 GROQ AI Bot ishga tushmoqda...")
    print("⚡ ENG TEZ AI - LLAMA 3.3 70B")
    print("🆓 100% BEPUL!")
    
    if TELEGRAM_TOKEN == "TELEGRAM_BOT_TOKEN_NI_BU_YERGA":
        print("❌ Telegram tokenini kiriting!")
        return
    
    if GROQ_API_KEY == "GROQ_API_KEY_NI_BU_YERGA":
        print("⚠️ GROQ API kaliti kiritilmagan!")
        print("📝 https://console.groq.com/keys dan bepul kalit oling!")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("fix", fix_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("creative", creative_command))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(CommandHandler("reminder", add_reminder))
    app.add_handler(CommandHandler("myreminders", show_reminders))
    app.add_handler(CommandHandler("clear", clear_reminders))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot ishga tushdi!")
    print("📱 Telegram'da /start bosing")
    print("⚡ GROQ - eng tez AI dunyoda!")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
