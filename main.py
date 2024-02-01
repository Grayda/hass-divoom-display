from flask import Flask, jsonify, request
from datetime import datetime
from homeassistant_api import Client
from requests import get
import subprocess
import json
import os

app = Flask(__name__)

args = None

# Default port
DEFAULT_PORT = 8080

# Home Assistant client
HASS = None

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(*args):
        val = dict.get(*args)
        return dotdict(val) if type(val) is dict else val
    __setattr__ = dict.__setitem__     
    __delattr__ = dict.__delitem__

def create_response(data: str, return_code=0, return_message=""):
    return {
        "DispData": data.upper(),
        "ReturnCode": return_code,
        "ReturnMessage": return_message
    }

def getURL(endpoint):
    url = f"{os.getenv('URL')}{endpoint}"
    headers = {
        "Authorization": f"Bearer {os.getenv('TOKEN')}",
        "content-type": "application/json",
    }
    
    response = get(url, headers=headers)
    return response.text

def getCalendar(calendar: str):
    results = dotdict(json.loads(getURL(f"/states/{calendar}")))
    
    event_name = results.attributes.message
    event_time = results.attributes.start_time
    
    dt = datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S")
    formatted_dt = dt.strftime(f"%a {dt.day}{getSuffix(dt.day)} %b, %I:%M %p")
    
    return f"{event_name} ({formatted_dt})"

def getSuffix(n):
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return suffix

def getDate():
    today = datetime.now().date()

    # Extract day, month, and year
    day = today.day
    
    dateString = today.strftime(f"%a {day}{getSuffix(day)} %b")  # Full month name
    
    return dateString

def update():
    print("Updating")
    try:
        # Run 'git pull' command
        subprocess.run(['git', 'pull'], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        # Handle the error as needed

def process_results(path):
    global HASS

    try:
        data = {
            "/update": {
                "function": update,
                "parameters": []
            },
            "/temperature": {
                "entity_id": "weather.home",
                "attribute": "temperature",
                "template": "{value}°C OUT"
            },
            "/temperature_inside": {
                "entity_id": "sensor.bedroom_climate_temperature",
                "template": "{value}°C IN"
            },
            "/calendar": {
                "function": getCalendar,
                "parameters": ["calendar.home_calendar"],
                "template": "{value}"
            },
            "/date": {
              "function": getDate,
              "parameters": [],
              "template": "{value}"  
            },
            "/message": {
                "entity_id": "input_text.divoom_message",
                "template": "{value}"
            }
        }
        
        if "function" in data[path]:
            fn = data[path]["function"]
            params = data[path]["parameters"] or []
            
            results = fn(*params)
            
            return create_response((data[path]["template"] or "{value}").format(value=results))
        elif "attribute" in data[path]:
            state = HASS.get_entity(entity_id=data[path]["entity_id"])
            return create_response((data[path]["template"] or "{value}").format(value=str(state.state.attributes[data[path]['attribute']])))
        else:
            state = HASS.get_entity(entity_id=data[path]["entity_id"])
            return create_response((data[path]["template"] or "{value}").format(value=str(state.state.state)))

    except Exception as ex:
        return create_response(data=str(ex))


@app.route('/<path:custom_path>')
def dynamic_route(custom_path):
    result = process_results(request.path)
    return jsonify(result)

if __name__ == '__main__':
    # args = parser.parse_args()
    print(f"Port: {os.getenv('PORT')}")
    print(f"URL: {os.getenv('URL')}")
    print(f"Token: ...{os.getenv('TOKEN')[-6:]}")
    HASS = Client(os.getenv("URL"), os.getenv("TOKEN"))
    app.json.ensure_ascii = False
    app.json.mimetype = "application/json; charset=utf-8"
    app.run(port=os.getenv("PORT", 8080), host="0.0.0.0")
    

    