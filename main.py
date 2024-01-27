from flask import Flask, jsonify
from flask import request
from homeassistant_api import Client
from requests import get
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

def create_response(data, return_code=0, return_message=""):
    return {
        "DispData": data,
        "ReturnCode": return_code,
        "ReturnMessage": return_message
    }

def getURL(endpoint):
    url = f"{os.environ.get('URL')}{endpoint}"
    headers = {
        "Authorization": f"Bearer {os.environ.get('TOKEN')}",
        "content-type": "application/json",
    }
    
    response = get(url, headers=headers)
    return response.text

def getCalendar(calendar: str):
    results = dotdict(json.loads(getURL(f"/states/{calendar}")))
    return results.attributes.message

def process_results(path):
    global HASS

    try:
        data = {
            "/temperature": {
                "entity_id": "weather.home",
                "attribute": "temperature",
                "template": "{value}°C"
            },
            "/calendar": {
                "function": getCalendar("calendar.bills_and_payments"),
                "template": "{value}"
            },
            "/bin": {
                "entity_id": "sensor.bin_sensor",
                "template": "{value}"
            },
            "/message": {
                "entity_id": "input_text.divoom_message",
                "template": "{value}"
            }
        }
        
        if "function" in data[path]:
            return create_response((data[path]["template"] or "{value}").format(value=str(data[path]["function"])))
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
    import argparse

    parser = argparse.ArgumentParser(description='Start a web server.')
    
    # parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port for the web server')
    # parser.add_argument('--url', type=str, required=True, help='The URL to your Home Assistant instance')
    # parser.add_argument('--token', type=str, required=True, help='The Long Lived Access Token for this')

    # args = parser.parse_args()
    print(os.environ.get("URL"))
    HASS = Client(os.environ.get("URL"), os.environ.get("TOKEN"))

    app.run(port=os.environ.get("PORT") or 8080)

    