#!/bin/bash

# Create a virtual environment named 'venv'
python3 -m venv venv
source venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip and install required packages from requirements.txt
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Run your Flask app
flask run
