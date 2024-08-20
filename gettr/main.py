import os
import asyncio
import aiohttp
from aiohttp import web
import aiofiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup


# Constants
PORT = os.environ.get('PORT', 2000)
SNAPSHOT_FILE = './data/snapshot.html'
DOCS_DIRECTORY = './data/downloaded_docs'
SERVER_URL = 'http://localhost:1000'
RECEIVER_URL = os.environ.get('RECEIVER_URL', 'http://localhost:3000')


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
    async with session.get(url) as response:
        if response.status == 200:
            async with aiofiles.open(os.path.join(DOCS_DIRECTORY, filename), 'wb') as f:
                await f.write(await response.read())

async def notify_receiver(message):
    async with aiohttp.ClientSession() as session:
        await session.post(RECEIVER_URL, json={'message': message})

async def compare_and_download():
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

                await asyncio.gather(*tasks)

            await notify_receiver("Task completed: Documents downloaded and snapshot updated")
        else:
            await notify_receiver("No changes detected")

    except Exception as e:
        await notify_receiver(f"Error occurred: {str(e)}")

async def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(compare_and_download, 'interval', minutes=1)
    scheduler.start()

async def create_gettr():
    app = web.Application()
    await start_scheduler()
    await compare_and_download()
    return app

if __name__ == '__main__':
    # Ensure the docs directory exists
    os.makedirs(DOCS_DIRECTORY, exist_ok=True)

    gettr = create_gettr()
    web.run_app(gettr, port=PORT)