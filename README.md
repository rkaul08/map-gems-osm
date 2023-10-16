# map-gems-osm
This project can give you points of interests around a particular address within a range of 5 kms.
1. The project uses overpass-api to extract information around a address using python.
2. It uses folium package to generate a map using latitude and longitude from the api results.
3. It uses flask to create a web app for displaying the results.

List of poi's are under data/amenities. To include more amenities the amenity can be added to the yaml in the same way as others.

To run the application simply run sh -x run_app.sh and it will host the app at http://127.0.0.1:5000/

Thanks
