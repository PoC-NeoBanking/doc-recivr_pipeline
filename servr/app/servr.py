from aiohttp import web
import os
import asyncio

# Constants
PORT = os.environ.get('PORT', 1000)
DIRECTORY = "./docs"

async def list_documents(request):
    files = os.listdir(DIRECTORY)
    html = "<h1>Documents</h1><ul>"
    for file in files:
        html += f'<li><a href="/docs/{file}">{file}</a></li>'
    html += "</ul>"
    return web.Response(text=html, content_type='text/html')

async def serve_document(request):
    filename = request.match_info['filename']
    filepath = os.path.join(DIRECTORY, filename)
    if os.path.exists(filepath):
        return web.FileResponse(filepath)
    return web.Response(text="File not found", status=404)

async def create_new_document(request):
    if request.method == 'POST':
        data = await request.post()
        a = data.get('a')
        if a and a.isdigit() and int(a) > 0:
            # Run the document creation script
            process = await asyncio.create_subprocess_exec(
                'py', './app/doc_creator.py', '-a', a,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return web.Response(text=f"Document(s) created successfully (amount: {a})", status=201)
            else:
                return web.Response(text=f"Error creating document: {stderr.decode()}", status=500)
        else:
            return web.Response(text=f"Invalid 'a' parameter: '{a}'", status=400)
    else:
        return web.Response(text="Method Not Allowed", status=405)
    
async def clear_documents(request):
    if request.method == 'POST':
        data = await request.post()
        confirmation = data.get('confirmation', '').lower() == 'true'
        
        if confirmation:
            try:
                counter = 0
                for filename in os.listdir(DIRECTORY):
                    file_path = os.path.join(DIRECTORY, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        counter += 1
                return web.Response(text=f"All documents have been deleted (amount: {counter})", status=200)
            except Exception as e:
                return web.Response(text=f"Error deleting documents: {str(e)}", status=500)
        else:
            return web.Response(text=f"Confirmation required to delete all documents (confirmation: '{confirmation}')", status=400)
    else:
        return web.Response(text="Method not allowed", status=405)

async def init_app():
    app = web.Application()
    app.router.add_get('/', list_documents)
    app.router.add_get('/docs/{filename}', serve_document)
    app.router.add_post('/newdoc', create_new_document)
    app.router.add_post('/clear', clear_documents)
    return app

def run_servr(port:int = PORT) -> None:
    if not os.path.exists(DIRECTORY):
        os.makedirs(DIRECTORY)
    
    app = init_app()
    web.run_app(app, port=port)