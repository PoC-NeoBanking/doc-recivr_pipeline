from aiohttp import web

from os import environ
import datetime


PORT = environ.get("PORT", 3000)

# A list to store all POST requests data
requests_data = []

# Handler for GET requests to show all POST data
async def handle_get(request):
    if not requests_data:
        return web.Response(text="No requests has been recieved yet", content_type='text/html')

    response_content = ""
    for request_record in requests_data:
        response_content += (
            f"Time: {request_record['time']}<br>"
            f"Path: /{request_record['path']}<br>"
            "Data: {<br>"
        )
        for key in request_record['data']:
            response_content += f"&nbsp;&nbsp;&nbsp;{key}: {request_record['data'][key]}<br>"
        response_content += "&nbsp;&nbsp;&nbsp;}<br><hr>"


    return web.Response(text=response_content, content_type='text/html')

# Handler for POST requests to log data and respond
async def handle_post(request):
    try:
        post_data = await request.json()
    except:
        return web.Response(text="Invalid JSON data", status=400)
    
    path_info = request.match_info.get('path', '')
    timecode = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    requests_data.append({
        'time': timecode,
        'path': path_info,
        'data': dict(post_data)
    })

    return web.Response(text="POST data received")

def run_recivr():
    app = web.Application()
    app.add_routes([
        web.get('/{path:.*}', handle_get),
        web.post('/{path:.*}', handle_post)
    ])
    web.run_app(app, port= PORT)
