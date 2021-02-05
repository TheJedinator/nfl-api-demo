#NFL Stats API

### What is this?

This is an API example using FastAPI, it queries two other APIs and munges the data
together in a format specified by the client. This is not intended to be "production ready"
code but is meant to be readable, and written in a way that explains some of my though processes


I'm pretty sure the rankings are the latest data, which is likely a problem if we are correlating them to point in time info.


### Get Started
This assumes you have python and pip installed, those are pre-requisites  

Recommend new virtual environment, but that's your funeral....  
Ensure nothing else is running locally on port 8000, either kill it or change the port on line 129 of main.py  


1. `pip3 install -r requirements`
2. `python3 main.py`
3. The server is now running, you can view documentation and test the endpoints by navigating to `http://127.0.0.1:8000/docs`
