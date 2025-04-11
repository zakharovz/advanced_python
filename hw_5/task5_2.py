import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from pathlib import Path
import argparse


class AsyncRealtyScraper:
    def __init__(self, storage_dir="realty_data", check_interval=3600):
        self.storage_dir = Path(storage_dir)
        self.check_interval = check_interval
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.headers = {"User-Agent": self.user_agent}
        self.storage_dir.mkdir(exist_ok=True)

    async def fetch(self, session, url):
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.text()
                print(f"Ошибка {response.status} при запросе {url}")
                return None
        except Exception as e:
            print(f"Ошибка при запросе {url}: {str(e)}")
            return None

    async def scrape_cian(self, session, url):
        html = await self.fetch(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        for item in soup.select('article[data-name="CardComponent"]'):
            try:
                offer = {
                    'source': 'cian',
                    'title': item.select_one('[data-name="TitleComponent"]').get_text(strip=True),
                    'price': item.select_one('[data-mark="MainPrice"]').get_text(strip=True),
                    'address': item.select_one('[data-name="GeoLabel"]').get_text(strip=True),
                    'url': "https://cian.ru" + item.select_one('a[data-name="LinkArea"]')['href'],
                    'date': datetime.now().isoformat()
                }
                offers.append(offer)
            except Exception as e:
                print(f"Ошибка парсинга объявления CIAN: {str(e)}")
                continue

        return offers

    async def scrape_yandex(self, session, url):
        html = await self.fetch(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        for item in soup.select('article[data-test="offer-card"]'):
            try:
                offer = {
                    'source': 'yandex',
                    'title': item.select_one('span[data-test="offer-title"]').get_text(strip=True),
                    'price': item.select_one('span[data-test="offer-price"]').get_text(strip=True),
                    'address': item.select_one('div[data-test="address"]').get_text(strip=True),
                    'url': "https://realty.yandex.ru" + item.find('a')['href'],
                    'date': datetime.now().isoformat()
                }
                offers.append(offer)
            except Exception as e:
                print(f"Ошибка парсинга объявления Яндекс: {str(e)}")
                continue

        return offers

    async def scrape_avito(self, session, url):
        html = await self.fetch(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        for item in soup.select('div[data-marker="item"]'):
            try:
                offer = {
                    'source': 'avito',
                    'title': item.select_one('h3[itemprop="name"]').get_text(strip=True),
                    'price': item.select_one('meta[itemprop="price"]')['content'] + " ₽",
                    'address': item.select_one('[data-marker="item-address"]').get_text(strip=True),
                    'url': "https://www.avito.ru" + item.select_one('a[data-marker="item-title"]')['href'],
                    'date': datetime.now().isoformat()
                }
                offers.append(offer)
            except Exception as e:
                print(f"Ошибка парсинга объявления Авито: {str(e)}")
                continue

        return offers

    async def save_offers(self, offers):
        today = datetime.now().strftime("%Y-%m-%d")
        filename = self.storage_dir / f"offers_{today}.json"

        existing = []
        if filename.exists():
            with open(filename, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        existing_ids = {o['url'] for o in existing}
        new_offers = [o for o in offers if o['url'] not in existing_ids]

        if new_offers:
            all_offers = existing + new_offers
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_offers, f, ensure_ascii=False, indent=2)
            print(f"Найдено {len(new_offers)} новых объявлений. Всего сохранено: {len(all_offers)}")
        else:
            print("Новых объявлений не найдено")

    async def run_once(self):
        urls = {
            'cian': 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&engine_version=2&offer_type=flat&region=1',
            'yandex': 'https://realty.yandex.ru/moskva_i_moskovskaya_oblast/snyat/kvartira/',
            'avito': 'https://www.avito.ru/moskva/kvartiry/sdam/na_dlitelnyy_srok'
        }

        async with aiohttp.ClientSession() as session:
            tasks = [
                self.scrape_cian(session, urls['cian']),
                self.scrape_yandex(session, urls['yandex']),
                self.scrape_avito(session, urls['avito'])
            ]
            results = await asyncio.gather(*tasks)
            all_offers = [offer for sublist in results for offer in sublist]
            await self.save_offers(all_offers)

    async def run_periodically(self):
        while True:
            print(f"\n{datetime.now().isoformat()} - Начинаем сканирование...")
            await self.run_once()
            print(f"Следующее сканирование через {self.check_interval // 60} минут...")
            await asyncio.sleep(self.check_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Асинхронный скрапер объявлений о съеме жилья')
    parser.add_argument('--once', action='store_true', help='Запустить однократное сканирование')
    parser.add_argument('--interval', type=int, default=3600, help='Интервал сканирования в секундах')
    parser.add_argument('--dir', type=str, default='realty_data', help='Директория для сохранения данных')

    args = parser.parse_args()

    scraper = AsyncRealtyScraper(storage_dir=args.dir, check_interval=args.interval)

    if args.once:
        asyncio.run(scraper.run_once())
    else:
        asyncio.run(scraper.run_periodically())