import os
import asyncio
import aiohttp
from aiohttp import web
import aiofiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import functools
from bs4 import BeautifulSoup
import pathlib
import json
import ollama
import httpx
import time
import fitz


# Constants
PORT = int(os.environ.get('PORT', 2000))
SNAPSHOT_FILE = './data/snapshot.html'
DOCS_DIRECTORY = './data/downloaded_docs'
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:1000')
RECEIVER_URL = os.environ.get('RECEIVER_URL', 'http://localhost:3000')
OLLAMA_CONNECTION_STR = os.environ.get("OLLAMA_CONNECTION_STR", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
PROMPT_TEMPLATE_PATH = os.environ.get("PROMPT_TEMPLATE_PATH", "./app/prompt.txt")


async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def save_snapshot(html):
    async with aiofiles.open(SNAPSHOT_FILE, 'w') as f:
        await f.write(html)

async def load_snapshot():
    try:
        async with aiofiles.open(SNAPSHOT_FILE, 'r') as f:
            return await f.read()
    except FileNotFoundError:
        return None

async def download_file(session, url, filename):
    file_path = os.path.join(DOCS_DIRECTORY, filename)
    async with session.get(url) as response:
        if response.status == 200:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(await response.read())
            return file_path
    return None

async def notify_receiver(data):
    async with aiohttp.ClientSession() as session:
        await session.post(RECEIVER_URL, json=data)

def wait_for_ollama(ollama_client):
    tries = 10
    while True:
        try:
            ollama_client.ps()
            break
        except httpx.HTTPError:
            if tries:
                tries -= 1
                time.sleep(1)
            else:
                raise

def download_model(ollama_client, model):
    existing_models = [model["name"] for model in ollama_client.list()["models"]]
    if model not in existing_models:
        print(f"Model not found locally, downloading: {model}")
        ollama_client.pull(model)
    else:
        print(f"Model: {model} found locally")

async def classify_pdf(file_path, prompt_template, ollama_client):

    # Extract the file name from the file path
    file_name = os.path.basename(file_path)
    
    # Read the PDF text
    pdf_text = ""
    async with aiofiles.open(file_path, 'rb') as f:
        pdf_data = await f.read()
        # Use PyMuPDF to extract text
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        for page in pdf_document:
            pdf_text += page.get_text()

    # Prepare the prompt by replacing the placeholder with the actual PDF text
    prompt = prompt_template.replace("$TEXT", pdf_text)


    # Call the Ollama client to generate a response
    api_response = ollama_client.generate(
        model=OLLAMA_MODEL,
        prompt=prompt,
        format="json",
        stream=False,
    )

    # Parse the response and add the file name to the JSON
    response = json.loads(api_response["response"])
    response["file_name"] = file_name
    
    return response

async def compare_and_download(ollama_client, prompt_template):
    try:
        current_html = await fetch_html(SERVER_URL)
        previous_html = await load_snapshot()

        if previous_html is None or previous_html != current_html:
            await save_snapshot(current_html)

            soup = BeautifulSoup(current_html, 'html.parser')
            links = soup.find_all('a', href=True)

            async with aiohttp.ClientSession() as session:
                tasks = []
                for link in links:
                    if link['href'].startswith('/docs/'):
                        file_url = f"{SERVER_URL}{link['href']}"
                        filename = os.path.basename(link['href'])
                        tasks.append(download_file(session, file_url, filename))

                file_paths = await asyncio.gather(*tasks)

                for file_path in filter(None, file_paths):
                    response_json = await classify_pdf(file_path, prompt_template, ollama_client)
                    await notify_receiver(response_json)

            await notify_receiver({"message": "Task completed: Documents downloaded, processed, and snapshot updated"})
        else:
            await notify_receiver({"message": "No changes detected"})

    except Exception as e:
        await notify_receiver({"error": str(e)})

async def start_scheduler(ollama_client, prompt_template):
    scheduler = AsyncIOScheduler()
    cand = functools.partial(compare_and_download, ollama_client, prompt_template)
    scheduler.add_job(cand, 'interval', minutes=1)
    scheduler.start()

async def create_gettr():
    os.makedirs(DOCS_DIRECTORY, exist_ok=True)

    ollama_client = ollama.Client(host=OLLAMA_CONNECTION_STR)
    wait_for_ollama(ollama_client)
    download_model(ollama_client, OLLAMA_MODEL)
    prompt_template = pathlib.Path(PROMPT_TEMPLATE_PATH).read_text()

    await start_scheduler(ollama_client, prompt_template)
    await compare_and_download(ollama_client, prompt_template)

    app = web.Application()

    return app


def run_gettr():
    os.makedirs(DOCS_DIRECTORY, exist_ok=True)

    gettr = create_gettr()

    web.run_app(gettr, port=PORT)