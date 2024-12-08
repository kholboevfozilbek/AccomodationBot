import sqlite3
import json

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

    if not filters:
        return None, None

    query = f"{base_query} {' AND '.join(filters)}"
    return query, values
