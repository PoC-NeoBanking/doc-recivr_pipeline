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
import fitz
import lamini


# Constants
PORT = int(os.environ.get('PORT', 2000))
SNAPSHOT_FILE = './data/snapshot.html'
DOCS_DIRECTORY = './data/downloaded_docs'
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:1000')
RECEIVER_URL = os.environ.get('RECEIVER_URL', 'http://localhost:3000')
PROMPT_TEMPLATE_PATH = os.environ.get("PROMPT_TEMPLATE_PATH", "./app/prompt.txt")
API_KEY = os.environ.get("API_KEY")
CLASSIFIED_PDFS_FILE = './data/classified_pdfs.json'


async def load_classified_pdfs():
    try:
        async with aiofiles.open(CLASSIFIED_PDFS_FILE, 'r') as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

async def save_classified_pdfs(classified_pdfs):
    async with aiofiles.open(CLASSIFIED_PDFS_FILE, 'w') as f:
        await f.write(json.dumps(classified_pdfs, indent=4))

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

async def classify_pdf(file_path, prompt_template, llm, classified_pdfs):
    file_name = os.path.basename(file_path)
    
    # Skip if already classified
    if file_name in classified_pdfs:
        return {"message": f"File {file_name} already classified."}
    
    pdf_text = ""
    async with aiofiles.open(file_path, 'rb') as f:
        pdf_data = await f.read()
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        for page in pdf_document:
            pdf_text += page.get_text()

    prompt = prompt_template.replace("$TEXT", pdf_text)

    api_response = llm.generate(f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>{prompt}<|eot_id|>\
                                <|start_header_id|>assistant<|end_header_id|>")

    response = json.loads(api_response)
    response["file_name"] = file_name
    
    # Mark as classified
    classified_pdfs.append(file_name)
    await save_classified_pdfs(classified_pdfs)
    
    return response

async def compare_and_download(llm, prompt_template):
    try:
        current_html = await fetch_html(SERVER_URL)
        previous_html = await load_snapshot()

        if previous_html is None or previous_html != current_html:
            await save_snapshot(current_html)

            soup = BeautifulSoup(current_html, 'html.parser')
            links = soup.find_all('a', href=True)

            classified_pdfs = await load_classified_pdfs()

            async with aiohttp.ClientSession() as session:
                tasks = []
                for link in links:
                    if link['href'].startswith('/docs/'):
                        file_url = f"{SERVER_URL}{link['href']}"
                        filename = os.path.basename(link['href'])
                        tasks.append(download_file(session, file_url, filename))

                file_paths = await asyncio.gather(*tasks)

                for file_path in filter(None, file_paths):
                    response_json = await classify_pdf(file_path, prompt_template, llm, classified_pdfs)
                    await notify_receiver(response_json)

            await notify_receiver({"message": "Task completed: Documents downloaded, processed, and snapshot updated"})
        else:
            await notify_receiver({"message": "No changes detected"})

    except Exception as e:
        await notify_receiver({"error": str(e)})

async def start_scheduler(llm, prompt_template):
    scheduler = AsyncIOScheduler()
    cand = functools.partial(compare_and_download, llm, prompt_template)
    scheduler.add_job(cand, 'interval', minutes=1)
    scheduler.start()

async def create_gettr():
    os.makedirs(DOCS_DIRECTORY, exist_ok=True)

    lamini.api_key = API_KEY
    llm = lamini.Lamini("meta-llama/Meta-Llama-3.1-8B-Instruct")
    prompt_template = pathlib.Path(PROMPT_TEMPLATE_PATH).read_text()

    await start_scheduler(llm, prompt_template)
    await compare_and_download(llm, prompt_template)

    app = web.Application()

    return app


def run_gettr():
    os.makedirs(DOCS_DIRECTORY, exist_ok=True)

    gettr = create_gettr()

    web.run_app(gettr, port=PORT)