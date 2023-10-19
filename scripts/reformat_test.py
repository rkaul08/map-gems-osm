import os, sys
import yaml
from geopy.geocoders import Nominatim
import requests
import folium
import time
import multiprocessing


def convert_city_to_geo_code(location):
    loc = Nominatim(user_agent="Geopy Library")
    # entering the location name
    getLoc = loc.geocode(location, exactly_one=True)
    return getLoc.latitude, getLoc.longitude


def amenities_to_map(amenities):
    amenities_path = os.path.join(os.getcwd(), "data/amenities", "amenities.yaml")
    delivery_path = os.path.join(os.getcwd(), "data/delivery", "grocery_delivery.yaml")
    with open(amenities_path, "r") as amenities_file:
        all_amenities = yaml.safe_load(amenities_file)

    with open(delivery_path, "r") as delivery_file:
        all_delivery = yaml.safe_load(delivery_file)

    input_amenities = []
    for amenity, amenity_list in all_amenities.items():
        for amenity_type in amenity_list:
            if amenity_type.split(",")[0] in amenities.split(","):
                input_amenities.append(amenity_type)

    input_delivery = {key: value for key, value in all_delivery.items() if key in amenities.split(",")}
    return input_amenities, input_delivery


def poi_overpass_data(overpass_url, input_amenities, radius, latitude, longitude):
    count = 0
    query = f"""[out:json]; \n("""
    while count < len(input_amenities):
        if ',' not in input_amenities[count]:
            amenity_type = input_amenities[count]
            query = query + f"  nw(around:{radius},{latitude},{longitude})[amenity={amenity_type}];\n"
            count += 1
        else:
            for tags in input_amenities[count].split(","):
                if '=' not in tags:
                    query = query + f"  nw(around:{radius},{latitude},{longitude})[amenity={tags}];\n"
                else:
                    value = tags.split("=")
                    query = query + f"  nw(around:{radius},{latitude},{longitude})[{value[0]}={value[1]}];\n"
            count += 1
    overpass_query = query + ");\nout;"

    response = requests.get(overpass_url, params={'data': overpass_query})
    if response.status_code == 200:
        data = response.json()
    amenities = data['elements']

    return amenities


def get_grocery_delivery(delivery_data, pincode):
    grocery_delivery = {"grocery_delivery": []}
    temp = {}
    for grocery_store in delivery_data["grocery_delivery"]:
        for brand, url in grocery_store.items():
            url_postcode = url.format(pincode=pincode)
            response = requests.get(url_postcode)
            if response.status_code == 200:
                data = response.json()
                temp[brand] = data["hasDelivery"]
            else:
                return f"Error: Failed to fetch delivery data. Status Code: {response.status_code}"

    grocery_delivery["grocery_delivery"].append(temp)

    return grocery_delivery


def get_postal_code(overpass_url, latitude, longitude, radius=100):
    overpass_query = f"""
        [out:json];
        // Query amenities around the specified latitude and longitude within the given radius
        nw(around:{radius},{latitude},{longitude})["postal_code"];
        out;
        """
    response = requests.get(overpass_url, params={'data': overpass_query})

    if response.status_code == 200:
        data = response.json()
        postal_code = data['elements'][0]["tags"]["postal_code"]
        return postal_code
    else:
        print(f"Error: Failed to fetch data. Status Code: {response.status_code}")
        return None


def get_node_data(overpass_url, amenity_row, item):
    if amenity_row["type"] == "node":
        latitude = amenity_row["lat"]
        longitude = amenity_row["lon"]
        name = amenity_row["tags"].get("name", "unknown").replace("`", "'")
        amenity = item
        return [latitude, longitude, name, amenity]
    else:
        node_id = amenity_row["nodes"][0]
        name = amenity_row["tags"].get("name", "unknown").replace("`", "'")
        amenity = item
        query = f"""
                [out:json];
                node({node_id});
                out;
                """
        node_result = requests.get(overpass_url, params={'data': query})

        if node_result.status_code == 200:
            data = node_result.json()
            node_data = data['elements'][0]
            latitude = node_data["lat"]
            longitude = node_data["lon"]
            return [latitude, longitude, name, amenity]
        else:
            print(f"Error: Failed to fetch data. Status Code: {node_result.status_code}")
            return None


def poi_aggregation(overpass_url, input_amenities, input_delivery, amenities, postal_code):
    poi_aggregation_result = {}

    # get the POI main_keys for which info is needed,
    # In case we have multiple tags like atm,atm=yes
    # we consider first tag i.e atm only and other tags for it
    # i.e atm=yes will append counts to main key atm only.
    main_keys = [i.split(",")[0] for i in input_amenities]
    searched_idx = []
    location_data = []

    for idx, i in enumerate(amenities):
        item = i["tags"].get("amenity", "unknown")
        if item not in poi_aggregation_result and item in main_keys:
            poi_aggregation_result[item] = 1
            # add row indexes already searched
            searched_idx.append(idx)
            map_location_data = get_node_data(overpass_url, i, item)
            location_data.append(map_location_data)
        elif item in main_keys:
            poi_aggregation_result[item] = poi_aggregation_result[item] + 1
            searched_idx.append(idx)
            map_location_data = get_node_data(overpass_url, i, item)
            location_data.append(map_location_data)

    for items in input_amenities:
        if len(items.split(",")) > 1:
            other_values = items.split(",")[1:]
            key = items.split(",")[0]

            for j in other_values:
                other_key = j.split('=')[0]
                other_value = j.split('=')[1]
                for idx, k in enumerate(amenities):
                    # skip looking into row indexes already searched
                    if idx not in searched_idx:
                        if k["tags"].get(other_key, "unknown") == other_value and key not in poi_aggregation_result:
                            poi_aggregation_result[key] = 1
                            searched_idx.append(idx)
                            map_location_data = get_node_data(overpass_url, i, item)
                            location_data.append(map_location_data)
                        elif k["tags"].get(other_key, "unknown") == other_value:
                            poi_aggregation_result[key] = poi_aggregation_result[key] + 1
                            searched_idx.append(idx)
                            map_location_data = get_node_data(overpass_url, i, item)
                            location_data.append(map_location_data)

    if len(input_delivery)>0:
        grocery_data = get_grocery_delivery(input_delivery, postal_code)
        poi_aggregation_result.update(grocery_data)
        return poi_aggregation_result, location_data
    else:
        return poi_aggregation_result, location_data


def interactive_map(locations, latitude, longitude, place):
    m = folium.Map(location=[latitude, longitude], zoom_start=20)
    folium.Marker([latitude, longitude], tooltip="Your Location", popup=place, icon=folium.Icon(color="red")).add_to(m)
    for location in locations:
        amenity = location[3]
        icon_path = os.path.join(os.getcwd(), 'data/icons', f"{amenity}.png")

        folium.Marker(
            [location[0], location[1]], tooltip=location[3], popup=location[2],
            icon=folium.CustomIcon(icon_image=icon_path, icon_size=(32, 32))
        ).add_to(m)

    result_path = os.path.join(os.getcwd(), "templates", "map.html")
    m.save(result_path)


def main():
    overpass_url = "https://overpass-api.de/api/interpreter"
    place = sys.argv[1]  # Replace with the desired latitude
    radius = int(sys.argv[2]) * 1000  # The radius converted in meters, entered in kms
    parsed_amenities = sys.argv[3]  # The amenities user is interested in mapping
    num_cores = os.cpu_count()
    pool = multiprocessing.Pool(processes=num_cores)

    amenities_to_map_start_time = time.time()
    input_amenities, input_delivery = amenities_to_map(parsed_amenities)
    amenities_to_map_end_time = time.time()
    duration_amenities_to_map = amenities_to_map_end_time - amenities_to_map_start_time

    print(f"amenities_to_map pocess took {duration_amenities_to_map:.2f} seconds")

    convert_city_to_geo_code_start_time = time.time()
    latitude, longitude = convert_city_to_geo_code(place)
    convert_city_to_geo_code_end_time = time.time()
    duration_convert_city_to_geo_code = convert_city_to_geo_code_end_time - convert_city_to_geo_code_start_time
    print(f"convert_city_to_geo_code pocess took {duration_convert_city_to_geo_code:.2f} seconds")

    poi_overpass_data_start_time = time.time()
    amenities = poi_overpass_data(overpass_url, input_amenities, radius, latitude, longitude)
    poi_overpass_data_end_time = time.time()
    duration_poi_overpass_data = poi_overpass_data_end_time - poi_overpass_data_start_time
    print(f"poi_overpass_data pocess took {duration_poi_overpass_data:.2f} seconds")

    get_postal_code_start_time = time.time()
    postal_code = get_postal_code(overpass_url, latitude, longitude)
    get_postal_code_end_time = time.time()
    duration_get_postal_code = get_postal_code_end_time - get_postal_code_start_time
    print(f"get_postal_code pocess took {duration_get_postal_code:.2f} seconds")

    poi_aggregation_start_time = time.time()
    poi_aggregation_result, location_data = pool.apply(poi_aggregation,(overpass_url, input_amenities, input_delivery, amenities, postal_code))
    poi_aggregation_end_time = time.time()
    duration_poi_aggregation = poi_aggregation_end_time - poi_aggregation_start_time
    print(f"poi_aggregation pocess took {duration_poi_aggregation:.2f} seconds")

    interactive_map_start_time = time.time()
    interactive_map(location_data, latitude, longitude, place)
    interactive_map_end_time = time.time()
    duration_interactive_map = interactive_map_end_time - interactive_map_start_time
    print(f"interactive_map pocess took {duration_interactive_map:.2f} seconds")

    pool.close()
    pool.join()
    return poi_aggregation_result


if __name__ == '__main__':
    print(main())
