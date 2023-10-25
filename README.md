# map-gems-osm
This project can give you points of interests around a particular address within a range of 5 kms.
1. The project uses overpass-api to extract information around a address using python.
2. It uses folium package to generate a map using latitude and longitude from the api results.
3. It uses flask to create a web app for displaying the results and the hosts the application on your localhost using gunicorn.

List of poi's are under data/amenities. To include more amenities the amenity can be added to the yaml in the same way as others.
Also we have non osm amenities in a saparate folder delivery which has yaml for companies that can deliver groceries.

Requirement to run the code is to have python3 installed in your machine.
To run the application simply run sh -x run_app.sh and it will host the app at  http://0.0.0.0:8000 and will install all necessary requirements needed to run the project.

Preview of the web app: 
![Alt text](/app-screenshot/frontend-image.png?raw=true "Frontend UI")



Thanks
