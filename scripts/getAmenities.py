import requests
import sys
import time
from geopy.geocoders import Nominatim
import folium
import os
import yaml


def get_amenities_count(latitude, longitude, radius=0, key="NA", value="NA"):
    overpass_url = "https://overpass-api.de/api/interpreter"
    ## USE NWR instead or node in query
    if key != "NA" and value != "NA":
        overpass_query = f"""
        [out:json];
        // Query amenities around the specified latitude and longitude within the given radius
        nw(around:{radius},{latitude},{longitude})[{value}={key}];
        out;
        """
    else:
        overpass_query = f"""
        [out:json];
        // Query amenities around the specified latitude and longitude within the given radius
        nw(around:{radius},{latitude},{longitude})["postal_code"];
        out;
        """

    response = requests.get(overpass_url, params={'data': overpass_query})

    if response.status_code == 200:
        data = response.json()
        amenities = data['elements']
        return amenities
    else:
        print(f"Error: Failed to fetch data. Status Code: {response.status_code}")
        return None


def get_node_data(node_id):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node({node_id});
    out;
    """
    node_result = requests.get(overpass_url, params={'data': query})
    return node_result


def convert_city_to_geo_code(location):
    loc = Nominatim(user_agent="Geopy Library")
    # entering the location name
    getLoc = loc.geocode(location, exactly_one=True)
    # printing address
    # print(getLoc.address)
    # printing latitude and longitude
    # print(f"latitude : {getLoc.latitude} and longitude : {getLoc.longitude}")
    return getLoc.latitude, getLoc.longitude


def interactive_map(locations, latitude, longitude, place):
    # files_to_remove = glob.glob(os.path.join(os.getcwd(), "templates","map_*.html"))
    # for file_to_remove in files_to_remove:
    #     os.remove(file_to_remove)

    m = folium.Map(location=[latitude, longitude], zoom_start=20)
    folium.Marker([latitude, longitude], tooltip="Your Location", popup=place, icon=folium.Icon(color="red")).add_to(m)
    for location in locations:
        amenity = location[3]
        icon_path = os.path.join(os.getcwd(), 'data/icons', f"{amenity}.png")

        folium.Marker(
            [location[0], location[1]], tooltip=location[3], popup=location[2],
            icon=folium.CustomIcon(icon_image=icon_path, icon_size=(32, 32))
        ).add_to(m)

    # result_path = os.path.join(os.getcwd(), "templates", f"map_{place}.html")
    result_path = os.path.join(os.getcwd(), "templates", "map.html")

    m.save(result_path)


def delivery(delivery_data, pincode):
    # delivery_path = os.path.join(os.getcwd(), "data/delivery", "grocery_delivery.yaml")
    # with open(delivery_path, "r") as delivery_file:
    #     all_delivery = yaml.safe_load(delivery_file)
    # print(all_delivery)

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


def get_lat_lon_node(result, poi_location, amenity):
    for k in result:
        if k.get("type") == "way":
            node_id = k["nodes"][0]
            node_result = get_node_data(node_id)
            if node_result.status_code == 200:
                data = node_result.json()
            lat = data["elements"][0]["lat"]
            lon = data["elements"][0]["lon"]
            poi_location.append([lat, lon, k["tags"].get("name", "unknown").replace("`", "'"), amenity])
        elif k.get("type") == "node":
            poi_location.append([k["lat"], k["lon"], k["tags"].get("name", "unknown").replace("`", "'"), amenity])


def amenities_to_map(amenities):
    amenities_path = os.path.join(os.getcwd(), "data/amenities", "amenities.yaml")
    delivery_path = os.path.join(os.getcwd(), "data/delivery", "grocery_delivery.yaml")
    with open(amenities_path, "r") as amenities_file:
        all_amenities = yaml.safe_load(amenities_file)

    with open(delivery_path, "r") as delivery_file:
        all_delivery = yaml.safe_load(delivery_file)

    input_amenities = {key: value for key, value in all_amenities.items() if key in amenities.split(",")}
    input_delivery = {key: value for key, value in all_delivery.items() if key in amenities.split(",")}
    return input_amenities, input_delivery


def main():
    place = sys.argv[1]  # Replace with the desired latitude
    radius = int(sys.argv[2]) * 1000  # The radius converted in meters, entered in kms
    amenities = sys.argv[3]  # The amenities user is interested in mapping
    input_amenities, input_delivery = amenities_to_map(amenities)
    # get lat and long from place
    latitude, longitude = convert_city_to_geo_code(place)
    postal_code = get_amenities_count(latitude, longitude, 100)[0]["tags"]["postal_code"]

    # print(f"{place} has latitude: {latitude},longitude : {longitude}")

    poi_location = []
    count_dict = {}

    for i, v in input_amenities.items():
        if len(v) > 1:
            count = 0
            for j in v:
                if '=' not in j:
                    result = get_amenities_count(latitude, longitude, radius, i, j)
                    amenity_count = len(result)
                    if amenity_count is not None:
                        count = count + amenity_count
                        get_lat_lon_node(result, poi_location, i)

                else:
                    result = get_amenities_count(latitude, longitude, radius, j.split('=')[1], j.split("=")[0])
                    amenity_count = len(result)
                    if amenity_count is not None:
                        count = count + amenity_count
                        get_lat_lon_node(result, poi_location, i)
            count_dict[i] = count
        else:
            result = get_amenities_count(latitude, longitude, radius, i, v[0])
            amenity_count = len(result)
            get_lat_lon_node(result, poi_location, i)
            count_dict[i] = amenity_count

    interactive_map(poi_location, latitude, longitude, place)

    if len(input_delivery) >= 1:
        delivery_status = delivery(input_delivery, postal_code)
        count_dict.update(delivery_status)

    return count_dict


if __name__ == '__main__':
    result = main()
    print(result)
    # for k, v in result.items():
    #     print(f"Total number of {k} around {sys.argv[2]} km of {sys.argv[1]} : {v},")
