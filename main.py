import telebot
import sqlite3
import json
import threading
import utility_functions

# Create a connection to the SQLite database
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

json_supported_countries = "support_for_country-city.json"
json_supported_country_data = utility_functions.load_json(json_supported_countries)

user_search_response = {}

# Create a table to store hosts if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS hosts (
        host_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, 
        last_name TEXT NOT NULL,
        id_pass BLOB,
        contact_phone TEXT NOT NULL, 
        contact_email TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        photo BLOB NOT NULL,
        place_id_for INTEGER NOT NULL,
        FOREIGN KEY(place_id_for) REFERENCES places(place_id)
    )
''')

# Create a table to store accommodations if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS places (
        place_id INTEGER PRIMARY KEY NOT NULL,
        host_id_foreign INTEGER NOT NULL, 
        place_country TEXT NOT NULL,
        place_city TEXT NOT NULL,
        place_municipality TEXT NOT NULL,
        place_street TEXT NOT NULL,
        place_building_number TEXT NOT NULL,
        place_postcode TEXT NOT NULL,
        place_house_number TEXT NOT NULL,
        place_floor INTEGER NOT NULL,
        place_type TEXT NOT NULL,
        place_size TEXT NOT NULL,
        place_price TEXT NOT NULL, 
        place_rooms INTEGER NOT NULL,
        place_room_equipment TEXT,
        place_kitchen TEXT,
        place_bathroom TEXT,
        place_garden INTEGER,
        place_reception_security INTEGER,
        place_balcony INTEGER,
        place_smoking INTEGER,
        place_pets INTEGER,
        place_music_party INTEGER,
        place_parking TEXT,
        place_near_bus_lines TEXT,
        place_near_tram_lines TEXT,
        place_near_train_station TEXT,
        place_near_touristic_places TEXT,
        place_near_groceries_stores TEXT,
        place_tags TEXT,
        place_features TEXT,
        place_added_date TEXT,
        place_update_date TEXT,
        place_verified INTEGER, 
        place_available INTEGER NOT NULL,
        FOREIGN KEY(host_id_foreign) REFERENCES hosts(host_id)
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
        admin_id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL, 
        last_name TEXT NOT NULL,
        contact_phone TEXT NOT NULL, 
        contact_email TEXT
    )
''')

conn.commit()

BOT_TOKEN = "7581557841:AAFGswC5d2Q3tPTcp2f7t6mGIYs1eojhnrk"
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

    user_state[host_id] = {"step": "name"}
    bot.send_message(message.chat.id, "Please enter the name of the accommodation:")


@bot.message_handler(func=lambda message: message.from_user.id in user_state)
def process_accommodation_data(message):
    host_id = message.from_user.id
    state = user_state.get(host_id)

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

        tags_to_text = ""
        for tag in state["tags"]:
            tags_to_text += tag + " "

        print(tags_to_text)

        cursor.execute(
            'INSERT INTO places (host, place_name, place_location, place_price, place_tags, place_verified) VALUES (?, ?, ?, ?, ?, ?)',
            (host_id, state["name"], state["location"], state["price"], tags_to_text, 0))
        conn.commit()

        bot.send_message(message.chat.id, "Your request to add an accommodation is being reviewed by our admins! ⏳")

        # verify function
        verify_accommodation_data(host_id, utility_functions.get_admin_id())

        user_state.pop(host_id)


def verify_accommodation_data(host_id, admin_id):
    state = user_state.get(host_id)
    accommodation_name = state["name"]

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ Verified", callback_data=f"verified_{accommodation_name}"),
        telebot.types.InlineKeyboardButton("❌ Not Verified", callback_data=f"not_verified_{accommodation_name}")
    )

    bot.send_message(
        admin_id,
        f"Please verify the accommodation: {accommodation_name}",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    accommodation = call.data.split("_", 1)[1]
    cursor.execute(
        'SELECT host FROM places WHERE place_name = ?',
        (accommodation,)  # Use parameterized query for safety
    )
    host_id = cursor.fetchone()
    print(host_id)
    state = user_state.get(host_id)

    if call.data.startswith("verified_"):
        cursor.execute(
            'UPDATE places SET place_verified = 1 WHERE place_name = ?',
            (accommodation,)
        )
        conn.commit()

        bot.send_message(call.message.chat.id, f"Admin, you have verified Accommodation Adding Request ✅")
        bot.send_message(host_id, f"Your request for Adding Accommodation has been verified ✅")


    elif call.data.startswith("not_verified_"):
        cursor.execute(
            'DELETE FROM places WHERE place_name = ?',
            (accommodation,)  # Use a tuple to pass the parameter
        )
        conn.commit()

        bot.send_message(call.message.chat.id,
                         f"Admin, you have rejected verification for Accommodation Adding Request ❌")
        bot.send_message(host_id, f"Your request for Adding Accommodation has been rejected ❌")


@bot.message_handler(commands=['search'])
def search_accommodation(message):
    host_id = message.from_user.id
    if host_id not in user_search_response:
        user_search_response[host_id] = {  # Initialize with the base structure
            "selection_state": {  # Temporary state for selection
                "step": None,  # Default step
                "options": []  # Empty options initially
            },
            "country": None,
            "city": None,
            "municipality": {
                "district": None,
                "part": None
            },
            "floor": None,
            "type": None,
            "size": None,
            "price": {
                "base": None,
                "deposit": None,
                "additional-fees": None,
                "additional-fees-list": {
                    "utilities": None,
                    "internet": None
                }
            },
            "rooms": None,
            "room-equipment": [],
            "kitchen": {
                "separate": None,
                "shared": None,
                "equipment": []
            },
            "bathroom": {
                "shared": None
            },
            "garden": None,
            "reception_security": None,
            "balcony": None,
            "smoking": None,
            "pets": None,
            "music-party": None,
            "parking": {
                "available": None,
                "price": None,
                "type": None
            },
            "near-bus-lines": {
                "address": None,
                "lines": [],
                "distance": None
            },
            "near-tram-lines": {
                "address": None,
                "lines": [],
                "distance": None
            },
            "near-train-station": {},
            "near-touristic-places": {},
            "near-groceries-stores": {},
            "tags": [],
            "features": [],
            "added-date": None,
            "update-date": None,
            "verified": None,
            "available": None,
            "energy-efficiency":{
                "energy_rating": None, #(e.g, A+,B+,etc.)
                "heating_type": None,  #(central,electric,underfloor)
                "cooling_type": None,  #(air conditioning, ceiling fans)
            },
            "property-features":{
                "view": None, #city,mountain,sea
                "elevator": None, #yes/no
                "fireplace": None,
                "alarm_system": None,
                "smart_home_technology": None,
            },
            "outdoor-features":{
                "swimming_pool": None,
                "jacuzzi": None,
                "sauna": None,
                "grill_area": None,
                "private_entrance": None,
            },
            "location-specific-features":{
                "neighborhood_quality": None,  #safe,upscale,developing
                "crime_rate": None,  #low,medium,high
                "noise_level": None,  #quiet,moderate,noisy
            }
        }
    user_search_response[host_id]["selection_state"] = {"step": "country"}

    msg = bot.reply_to(
        message,
        "We will ask your input to filter out best matching apartment for your needs!\n\n"
    )

    bot.register_next_step_handler(msg, process_country_step)


def process_country_step(message):

    host_id = message.from_user.id
    countries_list = utility_functions.supported_countries_list(json_supported_country_data)
    numbered_country_list = "\n".join([f"{i + 1}. {country}" for i, country in enumerate(countries_list)])

    msg = bot.reply_to(
        message,
        'Which country would you like to search for an apartment? 🌎\nHere is the list of supported countries:\n' +
        numbered_country_list +
        "\n\nPlease reply with the number corresponding to your choice: \n\n"
    )

    user_search_response[host_id]["selection_state"]["options"] = countries_list

    bot.register_next_step_handler(msg, process_city_step)


def process_city_step(message):
    host_id = message.from_user.id

    user_country_selection = int(message.text)
    country_options_list = user_search_response[host_id]["selection_state"]["options"]

    # Validate the user's choice
    if user_country_selection < 1 or user_country_selection > len(country_options_list):
        msg = bot.reply_to(
            message,
            "Incorrect option entered! Please select available options!😡😡😡"
        )

        bot.register_next_step_handler(msg, process_country_step)
    else:
        user_search_response[host_id]["country"] = country_options_list[user_country_selection - 1]
        print(f"User {host_id} selected: {country_options_list[user_country_selection - 1]}")

        cities_list = utility_functions.supported_cities_list(json_supported_country_data,
                                                              country_options_list[user_country_selection - 1])
        numbered_city_list = "\n".join([f"{i + 1}. {city}" for i, city in enumerate(cities_list)])

        user_search_response[host_id]["selection_state"] = {"step": "city"}
        user_search_response[host_id]["selection_state"]["options"] = cities_list

        msg = bot.reply_to(
            message,
            'Which city would you like to search for an apartment?\n' +
            'Here is the list of supported cities within the country you have selected:\n' +
            numbered_city_list +
            "\n\nPlease reply with the number corresponding to your choice: \n\n"
        )
        bot.register_next_step_handler(msg, process_municipality_step)


def process_municipality_step(message):
    host_id = message.from_user.id

    user_city_selection = int(message.text)
    city_options_list = user_search_response[host_id]["selection_state"]["options"]

    # Validate the user's choice
    if user_city_selection < 1 or user_city_selection > len(city_options_list):

        msg = bot.reply_to(
            message,
            "Incorrect option entered! Please select available options!😡😡😡"
        )

        bot.register_next_step_handler(msg, process_city_step)
    else:
        user_search_response[host_id]["city"] = city_options_list[user_city_selection - 1]
        print(f"User {host_id} selected: {city_options_list[user_city_selection - 1]}")

        municipality_list = utility_functions.supported_municipalities_list(json_supported_country_data,
                                                                            user_search_response[host_id]["country"],
                                                                            user_search_response[host_id]["city"])

        numbered_municipality_list = "\n".join([f"{i + 1}. {municipality}" for i, municipality in enumerate(municipality_list)])

        user_search_response[host_id]["selection_state"] = {"step": "municipality"}
        user_search_response[host_id]["selection_state"]["options"] = municipality_list

        # maybe display an image describing districts of the city

        msg = bot.reply_to(
            message,
            'Which district would you like to search for an apartment?\n' +
            'Here is the list of supported districts:\n' +
            numbered_municipality_list +
            "\n\nPlease reply with the number corresponding to your choice: \n\n"
        )

        utility_functions.send_photo_via_telegram(BOT_TOKEN, message.chat.id,
                                                  f"images/{user_search_response[host_id]['city']}_SIM.png")

        bot.register_next_step_handler(msg, process_district_part_step)


def process_district_part_step(message):
    host_id = message.from_user.id

    user_municipality_selection = int(message.text)
    municipality_options_list = user_search_response[host_id]["selection_state"]["options"]

    # Validate the user's choice
    if user_municipality_selection < 1 or user_municipality_selection > len(municipality_options_list):
        msg = bot.reply_to(
            message,
            "Incorrect option entered! Please select available options!😡😡😡"
        )

        bot.register_next_step_handler(msg, process_district_part_step)
    else:
        user_search_response[host_id]["municipality"]["district"] = municipality_options_list[user_municipality_selection - 1]
        print(f"User {host_id} selected: {municipality_options_list[user_municipality_selection - 1]}")

        district_parts_list = utility_functions.supported_parts_list(json_supported_country_data,
                                                                            user_search_response[host_id]["country"],
                                                                            user_search_response[host_id]["city"],
                                                                            user_search_response[host_id]["municipality"]["district"])

        numbered_district_parts_list = "\n".join([f"{i + 1}. {parts}" for i, parts in enumerate(district_parts_list)])

        user_search_response[host_id]["selection_state"] = {"step": "part"}
        user_search_response[host_id]["selection_state"]["options"] = district_parts_list

        msg = bot.reply_to(
            message,
            'Which parts of the district would you like to search for an apartment?\n' +
            'Here is the list of supported parts of the chosen district:\n' +
            numbered_district_parts_list +
            "\n\nPlease reply with the number corresponding to your choice: \n\n"
        )

        bot.register_next_step_handler(msg, process_user_flow_choice_step)


def process_user_flow_choice_step(message):
    host_id = message.from_user.id

    user_district_part_selection = int(message.text)
    district_part_options_list = user_search_response[host_id]["selection_state"]["options"]

    # Validate the user's choice
    if user_district_part_selection < 1 or user_district_part_selection > len(district_part_options_list):
        msg = bot.reply_to(
            message,
            "Incorrect option entered! Please select available options!😡😡😡"
        )

        bot.register_next_step_handler(msg, process_user_flow_choice_step)
    else:
        user_search_response[host_id]["municipality"]["part"] = district_part_options_list[user_district_part_selection - 1]
        print(f"User {host_id} selected: {district_part_options_list[user_district_part_selection - 1]}")

        ### NOW WE NEED TO ASK THE USER IF HE WANTS TO GET ALL THE ENTRIES FOR HIS GIVEN PARAMETERS
        ### OR HE WANTS TO USE OUR HOUSING EXPERTISE

        user_search_response[host_id]["selection_state"] = {"step": "user_choice_program_flow"}
        user_search_response[host_id]["selection_state"]["options"] = [1, 2]

        msg = bot.reply_to(
            message,
            'Thanks for the input.\n' +
            '1. Would you like me to return all the accommodations for your given parameters?\n' +
            '2. or Would you like to use our housing expertise to find best match for your needs?'
            "\n\nPlease reply with the number corresponding to your choice: \n\n"
        )

        bot.register_next_step_handler(msg, process_user_flow_choice2_step)


def process_user_flow_choice2_step(message):

    host_id = message.from_user.id
    user_flow_selection = int(message.text)

    match user_flow_selection:
        case 1:
            print("PLEASE HANDLE RETURNING ALL THE ENTRIES FOR THE PARAMETERS TAKEN THUS FAR")
            query, values = utility_functions.build_query(user_search_response[message.from_user.id],
                                                          ["country", "city", "municipality"])
            if query:
                cursor.execute(query, values)
                results = cursor.fetchall()

                if results:
                    count = len(results)
                    msg = bot.reply_to(
                        message,
                        f"We found {count} matching apartments for your input parameters.\n"
                        "Would you like to see them or narrow down your search further? Reply with:\n"
                        "1. See the listings\n"
                        "2. Narrow down the options"
                    )
                    bot.register_next_step_handler(msg, process_display_results_step, results, process_type_apartment_step)
                else:
                    msg = bot.reply_to(message, f"No matching entries found for your parameters,"
                                                f"\nCountry: {user_search_response[host_id]['country']}"
                                                f"\nCity: {user_search_response[host_id]['city']}"
                                                f"\nDistrict: {user_search_response[host_id]['municipality']['district']}"
                                                f"\nPart of city: {user_search_response[host_id]['municipality']['part']}"
                                                f"\n\nSorry 😭\n\n")
                    bot.register_next_step_handler(msg, process_country_step)

        case 2:
            print("OK WE NEED TO CONTINUE ASKING MORE PARAMETERS TO NARROW DOWN THE OPTIONS")
            supported_apartment_types_list = utility_functions.supported_apartment_types("type_apartments.json")
            numbered_apartment_types_list = "\n".join(
                [f"{i + 1}. {types}" for i, types in enumerate(supported_apartment_types_list)])

            user_search_response[host_id]["selection_state"] = {"step": "type"}
            user_search_response[host_id]["selection_state"]["options"] = supported_apartment_types_list

            msg = bot.reply_to(
                message,
                'Thanks for using our housing expertise.\n' +
                'What type of apartment you are looking for\n' +
                '\n\nhere is the type of apartments supported: \n' +
                numbered_apartment_types_list +
                "\n\nPlease reply with the number corresponding to your choice: \n\n"
            )
            bot.register_next_step_handler(msg, process_type_apartment_step)
        case _:
            # Fallback for invalid inputs
            error_msg = bot.reply_to(
                message,
                "Invalid selection. Please reply with either:\n"
                "1: To see all entries for the parameters taken so far\n"
                "2: To continue narrowing down your search"
            )
            bot.register_next_step_handler(error_msg, process_user_flow_choice2_step)


def process_type_apartment_step(message):
    host_id = message.from_user.id
    apartment_type_selection = int(message.text)

    supported_apartment_types_list = user_search_response[host_id]["selection_state"]["options"]

    # Validate the user's choice
    if apartment_type_selection < 1 or apartment_type_selection > len(supported_apartment_types_list):
        msg = bot.reply_to(
            message,
            "Incorrect option entered! Please select available options!😡😡😡"
        )

        bot.register_next_step_handler(msg, process_type_apartment_step)

    else:
        user_search_response[host_id]["type"] = supported_apartment_types_list[apartment_type_selection-1]

        query, values = utility_functions.build_query(user_search_response[message.from_user.id],
                                                      ["country", "city", "municipality", "type"])

        if query:
            cursor.execute(query, values)
            results = cursor.fetchall()

            if results:
                count = len(results)
                msg = bot.reply_to(
                    message,
                    f"We found {count} matching apartments for your input parameters.\n"
                    "Would you like to see them or narrow down your search further? Reply with:\n"
                    "1. See the listings\n"
                    "2. Narrow down the options"
                )
                bot.register_next_step_handler(msg, process_display_results_step, results, process_price_step, "Enter your budget min-max")
            else:
                msg = bot.reply_to(message, "No matches found. Please adjust your search criteria.")
                bot.register_next_step_handler(msg, process_price_step)
        else:
            msg = bot.reply_to(message, "Please provide your budget min-max")
            bot.register_next_step_handler(msg, process_price_step)


def process_display_results_step(message, results, next_step_name, msg):
    host_id = message.chat.id
    user_choice = int(message.text)

    match user_choice:

        case 1:
            # Display the first 10 results
            for i, result in enumerate(results[:10], start=1): # so here we are displaying the complete info about the apartment
                additional_fees = json.loads(result[12]).get("additional-fees-list", {})
                additional_fees_list = "\n".join(
                    [f"{i + 1}. {fee}" for i, fee in enumerate(additional_fees)]) if json.loads(result[12]).get(
                    "additional-fees") == 1 else "No additional fees."
                msg = bot.reply_to(
                    message,
                    "Added on: " + utility_functions.format_date(result[31]) +
                    "\nLast Update on: " + utility_functions.format_date(result[32]) +
                    "\nAvailable?: " + utility_functions.convert_to_yes_no(result[34]) +
                    "\nVerified?: " + utility_functions.convert_to_yes_no(result[33]) +
                    "\n\nCountry: " + str(result[2]) +
                    "\nCity: " + str(result[3]) +
                    "\nDistrict of the city: " + json.loads(result[4]).get("district", "N/A") +
                    "\nPart of the city: " + json.loads(result[4]).get("part", "N/A") +
                    "\nStreet: " + str(result[5]) +
                    "\nBuilding number: " + str(result[6]) +
                    "\nPost-code: " + str(result[7]) +
                    "\nApartment number: " + str(result[8]) +
                    "\nFloor: " + str(result[9]) +
                    "\nApartment Type: " + str(result[10]) +
                    "\nApartment Size: " + str(result[11]) +
                    "\nApartment Price: \n\t" +
                    str(json.loads(result[12]).get("base", "0")) + " PLN\n\t" +
                    str(json.loads(result[12]).get("deposit", "0")) + " PLN\n\t" +
                    "Additional Fees:\n\t\t" + additional_fees_list +
                    "\nNumber of rooms: " + str(result[13]) +
                    "\n\nKitchen: " + utility_functions.get_kitchen_info(json.loads(result[15])) +
                    "\nBathroom: " + utility_functions.get_bathroom_info(json.loads(result[16])) +
                    "\nDoes it have balcony?: " + utility_functions.convert_to_yes_no(result[19]) +
                    "\nDoes it have a garden?:" + utility_functions.convert_to_yes_no(result[17]) +
                    "\nReception/Security: " + utility_functions.convert_to_yes_no(result[18]) +
                    "\nSmoking allowed?: " + utility_functions.convert_to_yes_no(result[20]) +
                    "\nPets allowed?: " + utility_functions.convert_to_yes_no(result[21]) +
                    "\nParty/Music allowed?: " + utility_functions.convert_to_yes_no(result[22]) +
                    "\nParking: " + utility_functions.get_parking_info(json.loads(result[23])) +
                    "\n\nTransportation Access: " + utility_functions.get_bus_lines_info(json.loads(result[24])) +
                    utility_functions.get_tram_lines_info(json.loads(result[25])) +
                    utility_functions.get_train_station_info(json.loads(result[26])) +
                    "\n\nTouristic Attractions Nearby" + utility_functions.get_touristic_places_info(json.loads(result[27])) +
                    "\n\nGrocery Stores Nearby:" + utility_functions.get_grocery_stores_info(json.loads(result[28])) +
                    f"\n{utility_functions.format_tags(json.loads(result[29]))}" +
                    "\nFeatures:\n" + utility_functions.format_features(json.loads(result[30])) +
                    "\nWould you like to continue?" + msg
                )

                ### we also need to display apartment pictures

                # Retrieve and send images for the current apartment
                place_id = result[0]
                cursor.execute("SELECT photo FROM images WHERE place_id_for = ?", (place_id,))
                images = cursor.fetchall()  # Retrieve all images for the current place_id

                if images:
                    for image in images:
                        photo_blob = image[0]
                        # Save the image temporarily to send it
                        with open("temp_image.jpg", "wb") as temp_image:
                            temp_image.write(photo_blob)
                        # Send the image
                        with open("temp_image.jpg", "rb") as temp_image:
                            utility_functions.send_photo_via_telegram(BOT_TOKEN, message.chat.id, "temp_image.jpg")

                bot.register_next_step_handler(msg, next_step_name)

        case 2:
            msg = bot.reply_to(
                message,
                "Please provide your budget: min-max"
            )
            bot.register_next_step_handler(msg, next_step_name)

        case _:
            # Fallback for invalid inputs
            error_msg = bot.reply_to(
                message,
                "Invalid selection. Please reply with either:\n"
                "1: To see all entries for the parameters taken so far\n"
                "2: To continue narrowing down your search"
            )
            bot.register_next_step_handler(error_msg, process_display_results_step, results, next_step_name)


def process_price_step(message):
    host_id = message.from_user.id
    price_selection = message.text

    budget = price_selection.split("-")

    # check

    # db query



def process_number_rooms_step(message):
    print("hehe")


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
                 f'Welcome to AccommodationFinder, how can I help you?' +
                 '\n 1. I am looking for apartment: /search' +
                 '\n 2. I want to list an apartment /add'
                 )


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
    json_file_path = "large_data.json"
    db_name = "users.db"
    photos = ["images/1.jpg", "images/2.jpg", "images/3.jpg", "images/4.jpg", "images/5.jpg"]
    # utility_functions.parse_and_store(json_file_path, db_name, photos)
    utility_functions.fetch_and_display_all_data("users.db")
    bot.polling(timeout=10, long_polling_timeout=5)
