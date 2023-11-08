from flask import Flask, render_template, request, send_from_directory
import subprocess
import os
import ast
import yaml
from time import time

app = Flask(__name__)

#
# # Set the path to your virtual environment
venv_path = os.path.join(os.getcwd(), "venv")

amenities_file_path = os.path.join(os.getcwd(), "data/amenities", "amenities.yaml")
grocery_file_path = os.path.join(os.getcwd(), "data/delivery", "grocery_delivery.yaml")

with open(amenities_file_path, 'r') as amen_file:
    amenities_list = yaml.safe_load(amen_file)

with open(grocery_file_path, 'r') as delivery_file:
    grocery_list = yaml.safe_load(delivery_file)

amenities_available = []
for amenity,amenity_type in amenities_list.items():
    for item in amenity_type:
        amenities_available.append(item.split(",")[0])

for key in grocery_list:
    amenities_available.append(key)


# @app.route('/')
# def index():
#     return render_template('index.html', amenities=amenities_available)

@app.route('/')
def purpose_selection():
    return render_template('purpose_selection.html')


@app.route('/travel')
def travel_purpose():
    return render_template('index.html', amenities=amenities_available)


@app.route('/residential')
def residential_purpose():
    return render_template('index.html', amenities=amenities_available)


@app.route('/process', methods=['POST'])
def process():
    location = request.form.get('location')
    radius = request.form.get('radius')
    amenities = request.form.getlist('amenities')

    python_executable = os.path.join(venv_path, 'bin', 'python')
    if 'show_counts' in request.form:
        result = subprocess.run(
                [python_executable, "scripts/getAmenities.py", location, radius, ','.join(amenities), "count"],
                stdout=subprocess.PIPE,
                text=True,
                shell=False
            )
        data = ast.literal_eval(result.stdout)
        return render_template('counts.html', counts=data, radius= radius, place=location)

        # return result.stdout

    elif 'show_map' in request.form:
        result = subprocess.Popen(
            [python_executable, "scripts/getAmenities.py", location, radius, ','.join(amenities), "maps"],
            stdout=subprocess.PIPE,
            text=True,
            shell=False
        )
        result.wait()
        map_filename = "map.html"
        map_directory = os.path.join(os.getcwd(), "templates")
        return send_from_directory(map_directory, map_filename, as_attachment=False)
    if 'show_nearest' in request.form:
        result = subprocess.run(
                [python_executable, "scripts/getAmenities.py", location, radius, ','.join(amenities), "nearest"],
                stdout=subprocess.PIPE,
                text=True,
                shell=False
            )
        data = ast.literal_eval(result.stdout)
        return render_template('nearest.html', counts=data, radius=radius, place=location)
    if 'show_nearest_map' in request.form:
        result = subprocess.Popen(
            [python_executable, "scripts/getAmenities.py", location, radius, ','.join(amenities), "nearest_maps"],
            stdout=subprocess.PIPE,
            text=True,
            shell=False
        )
        result.wait()
        map_filename = "nearest_map.html"
        map_directory = os.path.join(os.getcwd(), "templates")
        return send_from_directory(map_directory, map_filename, as_attachment=False)


@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)