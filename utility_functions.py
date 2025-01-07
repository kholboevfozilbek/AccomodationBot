import sqlite3
import json
import requests
from datetime import datetime

def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData

def insert_data(connection, data, photos):
    """
    Insert data into the SQLite database, including handling BLOB for images.
    """
    cursor = connection.cursor()

    for photo in photos:
        photoBlob = convertToBinaryData(photo)
        sqlite_insert_photoBlob_query = """ INSERT INTO images (photo, place_id_for) VALUES (?, ?)"""
        data_tuple = (photoBlob, data['place-id'])
        cursor.execute(sqlite_insert_photoBlob_query, data_tuple)

    cursor.execute('''
            INSERT INTO places (
                place_id, host_id_foreign, place_country, place_city, place_street, 
                place_building_number, place_postcode, place_house_number, place_floor, place_type, place_size, 
                place_rooms, place_balcony, place_smoking, place_pets, place_music_party, 
                place_garden, place_reception_security, place_municipality,
                place_room_equipment, place_price, place_parking, place_kitchen, place_bathroom, 
                place_near_bus_lines, place_near_tram_lines, place_near_train_station, 
                place_near_touristic_places, place_near_groceries_stores, 
                place_tags, place_features, place_added_date, place_update_date,
                place_verified, place_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?)
        ''', (
        data['place-id'], data['host-id'], data['country'], data['city'],
        data['street'], data['building-number'],
        data['postcode'], data['house-number'], data['floor'], data['type'], data['size'],
        data['rooms'], data['balcony'], data['smoking'], data['pets'],
        data['music-party'], data['garden'], data['reception_security'],
        json.dumps(data['municipality'],),
        json.dumps(data['room-equipment']),
        json.dumps(data['price']),
        json.dumps(data['parking']),
        json.dumps(data['kitchen']),
        json.dumps(data['bathroom']),
        json.dumps(data['near-bus-lines']),  # Serialize nested structures
        json.dumps(data['near-tram-lines']),
        json.dumps(data['near-train-station']),
        json.dumps(data['near-touristic-places']),
        json.dumps(data['near-groceries-stores']),
        json.dumps(data['tags']),
        json.dumps(data['features']),
        data['added-date'], data['update-date'],
        data['verified'], data['available']
    ))
    connection.commit()


def parse_and_store(json_file_path, db_name, photos):
    """
    Parse the JSON file and store data into a SQLite database.
    """
    # Create database and table
    connection = sqlite3.connect(db_name, check_same_thread=False)

    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            # Assuming the JSON file contains a list of records
            json_data = json.load(file)

            if not isinstance(json_data, list):
                raise ValueError("JSON file must contain a list of records.")

            for record in json_data:
                insert_data(connection, record, photos)

        print(f"Data successfully inserted into {db_name}.")

    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        connection.close()


def fetch_and_display_all_data(db_name):
    """
    Fetch and display all data from the Places table in the SQLite database.

    Args:
        db_name (str): The name of the SQLite database file.
    """
    try:
        # Connect to the database
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()

        # Fetch all data
        cursor.execute("SELECT * FROM places")
        rows = cursor.fetchall()

        # Fetch column names for better readability
        column_names = [description[0] for description in cursor.description]

        # Display data
        if rows:
            print("Data from Places table:")
            print(" | ".join(column_names))
            print("-" * 80)
            for row in rows:
                for i, value in enumerate(row):
                    # Deserialize JSON fields for display
                    if column_names[i] in [
                        "kitchen", "bathroom", "near_bus_lines", "near_tram_lines", "near_train_station",
                        "near_touristic_places", "near_groceries_stores", "tags"
                    ]:
                        print(f"{column_names[i]}: {json.loads(value)}")
                    else:
                        print(f"{column_names[i]}: {value}")
                print("-" * 80)
        else:
            print("No data found in the Places table.")

        # printing the images belonging to the place

        # place_id_index = column_names.index("place_id")
        # for row in rows:
        #     # Fetch the actual place_id value from the row
        #     place_id = row[place_id_index]
        #
        #     # Fetch images associated with this place_id
        #     cursor.execute("SELECT * FROM images WHERE place_id_for = ?", (place_id,))
        #     image_rows = cursor.fetchall()
        #
        #     # Process the images
        #     if image_rows:
        #         print(f"Images for place_id {place_id}:")
        #         for image_row in image_rows:
        #             print(image_row)  # Display the image details
        #     else:
        #         print(f"No images found for place_id {place_id}.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")

    finally:
        # Close the database connection
        if connection:
            connection.close()

def get_admin_id():
    # Replace with your database connection logic
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT admin_id FROM admin LIMIT 1")
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def load_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def supported_countries_list(data):
    """Returns a list of supported countries."""
    return [entry["country"] for entry in data]


def supported_cities_list(data, country):
    """Returns a list of cities in a given country."""
    for entry in data:
        if entry["country"] == country:
            return list(entry["cities"].keys())
    return []


def supported_municipalities_list(data, country, city):
    """Returns a list of municipalities in a given city of a country."""
    for entry in data:
        if entry["country"] == country:
            city_data = entry["cities"].get(city)
            if city_data:
                return list(city_data["municipalities"].keys())
    return []


def supported_parts_list(data, country, city, municipality):
    """Returns a list of parts in a given municipality of a city."""
    for entry in data:
        if entry["country"] == country:
            city_data = entry["cities"].get(city)
            if city_data:
                municipality_data = city_data["municipalities"].get(municipality)
                if municipality_data:
                    return municipality_data.get("parts", [])
    return []


def supported_apartment_types(json_file_path):
    try:
        # Open and read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        # Extract and return the list of apartment types
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            apartment_types = list(data[0].values())
            return apartment_types
        else:
            raise ValueError("Unexpected JSON structure.")
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing JSON file: {e}")
        return []


def build_query(user_search_response, list_search_parameters):
    base_query = "SELECT * FROM places WHERE"
    filters = []
    values = []

    for parameter in list_search_parameters:
        if parameter == "country":
            if "country" in user_search_response and user_search_response["country"]:
                filters.append("place_country = ?")
                values.append(user_search_response["country"])
        elif parameter == "city":
            if "city" in user_search_response and user_search_response["city"]:
                filters.append("place_city = ?")
                values.append(user_search_response["city"])
        elif parameter == "municipality":
            if "municipality" in user_search_response and user_search_response["municipality"]:
                district = user_search_response["municipality"].get("district")
                if district:
                    filters.append("JSON_EXTRACT(place_municipality, '$.district') = ?")
                    values.append(district)

                part = user_search_response["municipality"].get("part")
                if part:
                    filters.append("JSON_EXTRACT(place_municipality, '$.part') = ?")
                    values.append(part)
        elif parameter == "type":
            if "type" in user_search_response and user_search_response["type"]:
                filters.append("place_type = ?")
                values.append(user_search_response["type"])
        elif parameter == "budget":
            if "budget" in user_search_response and user_search_response["budget"]:
                min_budget = user_search_response["budget"].get("min_value")
                max_budget = user_search_response["budget"].get("max_value")

                if min_budget is not None:
                    filters.append("JSON_EXTRACT(place_price, '$.base') >= ?")
                    values.append(min_budget)

                if max_budget is not None:
                    filters.append("JSON_EXTRACT(place_price, '$.base') <= ?")
                    values.append(max_budget)
        elif parameter == "rooms":
            if "rooms" in user_search_response and user_search_response["rooms"]:
                filters.append("place_rooms = ?")
                values.append(user_search_response["rooms"])
        elif parameter == "parking":
            if "parking" in user_search_response:
                filters.append("JSON_EXTRACT(place_parking, '$.available') <= ?")
                values.append(user_search_response["parking"])
        elif parameter == "smoking":
            if "smoking" in user_search_response and user_search_response["smoking"]:
                filters.append("place_smoking = ?")
                values.append(user_search_response["smoking"])
        elif parameter == "pets":
            if "pets" in user_search_response and user_search_response["pets"]:
                filters.append("place_pets = ?")
                values.append(user_search_response["pets"])
        elif parameter == "balcony":
            if "balcony" in user_search_response and user_search_response["balcony"]:
                filters.append("place_balcony = ?")
                values.append(user_search_response["balcony"])
    if not filters:
        return None, None

    query = f"{base_query} {' AND '.join(filters)}"
    return query, values


def send_photo_via_telegram(token, chat_id, image_path):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(image_path, 'rb') as photo_file:
        response = requests.post(
            url,
            data={'chat_id': chat_id},
            files={'photo': photo_file}
        )
    if response.status_code == 200:
        print("Photo sent successfully:", response.json())
    else:
        print("Failed to send photo:", response.status_code, response.text)


def get_kitchen_info(kitchen_data):
    kitchen_available = "Yes" if kitchen_data.get("available") == 1 else "No"
    kitchen_type = []
    if kitchen_data.get("separate") == 1:
        kitchen_type.append("Separate")
    if kitchen_data.get("shared") == 1:
        kitchen_type.append("Shared")

    equipment = kitchen_data.get("equipment", [])
    equipment_list = ", ".join(equipment) if equipment else "No equipment listed."

    kitchen_info = (
        f"\nDoes it have kitchen?: {kitchen_available}\n"
        f"Type: {', '.join(kitchen_type) if kitchen_type else 'N/A'}\n"
        f"Kitchen Equipment: {equipment_list}"
    )
    return kitchen_info


def get_bathroom_info(bathroom_data):
    bathroom_available = "Yes" if bathroom_data.get("available") == 1 else "No"
    bathroom_type = "Shared" if bathroom_data.get("shared") else "Not shared"

    bathroom_info = (
        f"available? : {bathroom_available} \n"
        f"Shared?: {bathroom_type}"
    )
    return bathroom_info


def convert_to_yes_no(data):
    return "Yes" if data else "No"


def get_parking_info(parking_data):
    if parking_data.get("available"):
        price = parking_data.get("price", "N/A")
        parking_type = parking_data.get("type", "N/A")
        return f"Available\nType: {parking_type.capitalize()}\nPrice: {price} PLN"
    else:
        return "Not Available"


def meters_to_km(meters):
    """Convert meters to kilometers and format with 2 decimal points."""
    try:
        km = int(meters) / 1000  # Safe conversion to float
        return f"{km:.2f} km"
    except (TypeError, ValueError):
        return "N/A"


def get_bus_lines_info(bus_data):
    if bus_data:
        address = bus_data.get("address", "N/A")
        lines = ", ".join(bus_data.get("lines", []))
        distance = meters_to_km(bus_data.get("distance", '0'))
        return f"\nBus station: {address}\nLines: {lines}\nDistance: {distance}"
    return "No nearby bus stops available."


def get_tram_lines_info(tram_data):
    if tram_data:
        address = tram_data.get("address", "N/A")
        lines = ", ".join(map(str, tram_data.get("lines", [])))
        distance = meters_to_km(tram_data.get('distance', '0'))
        return f"\nTram station: {address}\nLines: {lines}\nDistance: {distance}"
    return "No nearby tram stops available."


def get_train_station_info(train_data):
    if train_data:
        stations_info = "\n".join(
            [f"{station}: {meters_to_km(distance)}" for station, distance in train_data.items()]
        )
        return f"\nTrain Stations:\n{stations_info}"
    return "No nearby train stations available."


def get_touristic_places_info(places_data):
    if places_data:
        places_info = "\n".join(
            [
                f"* {place}: {round(int(distance) / 1000, 1)} km"
                for place, distance in places_data.items()
            ]
        )
        return f"\n{places_info}"
    return "No touristic attractions nearby."


def get_grocery_stores_info(stores_data):
    if stores_data:
        stores_info = "\n".join(
            [
                f"* {store}: {round(int(distance) / 1000, 1)} km"
                for store, distance in stores_data.items()
            ]
        )
        return f"\n{stores_info}"
    return "No grocery stores nearby."


def format_tags(tags):
    if tags:
        return " ".join([f"#{tag}" for tag in tags])
    return "No tags available."


def format_features(features):
    if features and isinstance(features, list):  # Ensure it's a list
        return "\n".join([f"* {feature.capitalize().strip()}" for feature in features])
    return "None"


def format_date(date_str):
    try:
        # Parse the date from the source string
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        # Reformat the date into a more human-readable format
        return date_obj.strftime("%B %d, %Y")  # Example: 'December 04, 2024'
    except ValueError:
        return date_str  # If the parsing fails, return the original string







