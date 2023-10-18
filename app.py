from flask import Flask, render_template, request, send_from_directory
import subprocess
import os
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

amenities_list.update(grocery_list)

@app.route('/')
def index():
    return render_template('index.html', amenities=amenities_list)


@app.route('/process', methods=['POST'])
def process():
    location = request.form.get('location')
    radius = request.form.get('radius')
    amenities = request.form.getlist('amenities')

    python_executable = os.path.join(venv_path, 'bin', 'python')
    if 'show_counts' in request.form:
        result_str = ""
        for amenity in amenities:
            result = subprocess.run(
                [python_executable, "scripts/getAmenities.py", location, radius, amenity],
                stdout=subprocess.PIPE,
                text=True,
                shell=False
            )
            result_str = result_str + str(result.stdout)
        return result_str

    elif 'show_map' in request.form:
        result = subprocess.Popen(
            [python_executable, "scripts/getAmenities.py", location, radius, ','.join(amenities)],
            stdout=subprocess.PIPE,
            text=True,
            shell=False
        )
        result.wait()
        map_filename = "map.html"
        map_directory = os.path.join(os.getcwd(), "templates")
        return send_from_directory(map_directory, map_filename, as_attachment=False)


@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response


if __name__ == '__main__':
    app.run(debug=True)
