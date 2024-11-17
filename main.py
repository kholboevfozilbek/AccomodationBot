import telebot
import sqlite3
import threading

# Create a connection to the SQLite database
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

# Create a table to store hosts if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS hosts (
        host_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, 
        last_name TEXT NOT NULL,
        id_pass BLOB NOT NULL,
        contact_phone TEXT NOT NULL, 
        contact_email TEXT
    )
''')

# Create a table to store guests if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS guests (
        guest_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, 
        last_name TEXT NOT NULL,
        contact_phone TEXT NOT NULL, 
        contact_email TEXT
    )
''')

# Create a table to store admin if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, 
        last_name TEXT NOT NULL,
        contact_phone TEXT NOT NULL, 
        contact_email TEXT
    )
''')

conn.commit()

BOT_TOKEN = "7581557841:AAG_dusuxWwEk0aZfGLTWZ6fIektZeFajQQ"
bot = telebot.TeleBot(BOT_TOKEN)

# Данные о жилье
accommodations = []

# Хранение состояний пользователей для добавления жилья
user_state = {}


# Команда для добавления жилья
@bot.message_handler(commands=['add_accommodation'])
def add_accommodation(message):
    host_id = message.from_user.id
    host_name = message.from_user.first_name

    user_state[user_id] = {"step": "name"}
    bot.send_message(message.chat.id, "Please enter the name of the accommodation:")


@bot.message_handler(func=lambda message: message.from_user.id in user_state)
def process_accommodation_data(message):
    host_id = message.from_user.id
    state = user_state.get(user_id)

    if state["step"] == "name":
        state["name"] = message.text
        state["step"] = "location"
        bot.send_message(message.chat.id, "Enter the location of the accommodation:")

    elif state["step"] == "location":
        state["location"] = message.text
        state["step"] = "price"
        bot.send_message(message.chat.id, "Enter the price of the accommodation:")

    elif state["step"] == "price":
        try:
            state["price"] = int(message.text)
            state["step"] = "tags"
            bot.send_message(message.chat.id, "Enter tags (separated by spaces, e.g., #dorm #budget):")
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid price (number).")

    elif state["step"] == "tags":
        state["tags"] = message.text.split()
        accommodations.append({
            "name": state["name"],
            "location": state["location"],
            "price": state["price"],
            "tags": state["tags"]
        })

        # we need to start handing for adding the user to the db table
        cursor.execute('INSERT INTO hosts (host_id, goal, completed) VALUES (?, ?, 0)', (user_id, goal))
        conn.commit()

        bot.send_message(message.chat.id, "Accommodation successfully added!")
        user_state.pop(user_id)


# Команда для поиска жилья
@bot.message_handler(commands=['search'])
def search_accommodation(message):
    tag = message.text.split(" ")[1] if len(message.text.split(" ")) > 1 else None
    if not tag:
        bot.reply_to(message, "Please provide a tag for search, e.g., /search #dorm")
        return

    results = [a for a in accommodations if tag in a["tags"]]

    if results:
        response = "Here are the accommodations that match your search:\n"
        for accommodation in results:
            response += (
                f"\nName: {accommodation['name']}\n"
                f"Location: {accommodation['location']}\n"
                f"Price: zl{accommodation['price']}\n"
                f"Tags: {' '.join(accommodation['tags'])}\n"
            )
    else:
        response = f"No accommodations found with the tag {tag}."

    bot.reply_to(message, response)


@bot.message_handler(commands=['list'])
def list_accommodations(message):
    if accommodations:
        response = "Available accommodations:\n"
        for accommodation in accommodations:
            response += (
                f"\nName: {accommodation['name']}\n"
                f"Location: {accommodation['location']}\n"
                f"Price: ${accommodation['price']}\n"
                f"Tags: {' '.join(accommodation['tags'])}\n"
            )
    else:
        response = "No accommodations available."

    bot.reply_to(message, response)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 f'Welcome! Use /add_accommodation to add your accommodation and /search #tag to find accommodations.')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, (
        "/start - Start using bot\n"
        "/help - Helpful list of commands\n"
        "/add_accommodation - Add a new accommodation for rent\n"
        "/search #tag - Search accommodations by tag\n"
        "/list - List all available accommodations\n"
    ))


if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(timeout=10, long_polling_timeout=5)
