import aiohttp
import asyncio
import os
from urllib.parse import urljoin
from pathlib import Path


async def download_image(session: aiohttp.ClientSession, save_dir: str, index: int):
    url = f"https://picsum.photos/2000/2000?random={index}"
    filename = os.path.join(save_dir, f"image_{index}.jpg")

    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(filename, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                print(f"Успешно загружено: {filename}")
            else:
                print(f"Ошибка загрузки {url}: статус {response.status}")
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {str(e)}")


async def download_images_async(num_images: int, save_dir: str):
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(num_images):
            task = asyncio.create_task(download_image(session, save_dir, i))
            tasks.append(task)

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Асинхронная загрузка случайных изображений с picsum.photos')
    parser.add_argument('--count', type=int, required=True, help='Количество изображений для загрузки')
    parser.add_argument('--dir', type=str, default='downloaded_images', help='Папка для сохранения изображений')

    args = parser.parse_args()

    asyncio.run(download_images_async(args.count, args.dir))