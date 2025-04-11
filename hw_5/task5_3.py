import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
import aiohttp
from bs4 import BeautifulSoup

TOKEN = ''
ARTIFACTS_DIR = Path("hw_5/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
SUBSCRIPTIONS_FILE = ARTIFACTS_DIR / "subscriptions.json"
OFFERS_FILE = ARTIFACTS_DIR / "offers.json"
NOTIFICATIONS_FILE = ARTIFACTS_DIR / "notifications.json"
NOTIFICATION_DELAY = 5  # Задержка между уведомлениями в секундах
MAX_DAILY_NOTIFICATIONS = 5  # Максимальное количество уведомлений в день

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


class SubscribeStates(StatesGroup):
    waiting_for_max_price = State()
    waiting_for_max_distance = State()


class RealtyOffer:
    def __init__(self, source, title, price, address, url, timestamp, processed=False):
        self.source = source
        self.title = title
        self.price_value = self._parse_price(price)
        self.price_text = price
        self.address = address
        self.distance_value = self._parse_distance(address)
        self.url = url
        self.timestamp = timestamp
        self.processed = processed

    def _parse_price(self, price_str):
        try:
            return int(''.join(filter(str.isdigit, price_str.split()[0])))
        except:
            return float('inf')

    def _parse_distance(self, address):
        try:
            for word in address.split():
                if word.isdigit():
                    return int(word)
            return float('inf')
        except:
            return float('inf')

    def to_dict(self):
        return {
            'source': self.source,
            'title': self.title,
            'price': self.price_text,
            'price_value': self.price_value,
            'address': self.address,
            'distance_value': self.distance_value,
            'url': self.url,
            'timestamp': self.timestamp,
            'processed': self.processed
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            source=data['source'],
            title=data['title'],
            price=data['price'],
            address=data['address'],
            url=data['url'],
            timestamp=data['timestamp'],
            processed=data.get('processed', False)
        )


class UserSubscription:
    def __init__(self, max_price, max_distance, created_at):
        self.max_price = int(max_price)
        self.max_distance = int(max_distance)
        self.created_at = created_at

    def to_dict(self):
        return {
            'max_price': self.max_price,
            'max_distance': self.max_distance,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            max_price=data['max_price'],
            max_distance=data['max_distance'],
            created_at=data['created_at']
        )


class RealtyScraper:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.headers = {"User-Agent": self.user_agent}

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

    async def scrape_cian(self, session):
        url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&engine_version=2&offer_type=flat&region=1'
        html = await self.fetch(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        for item in soup.select('article[data-name="CardComponent"]'):
            try:
                offer = RealtyOffer(
                    source='cian',
                    title=item.select_one('[data-name="TitleComponent"]').get_text(strip=True),
                    price=item.select_one('[data-mark="MainPrice"]').get_text(strip=True),
                    address=item.select_one('[data-name="GeoLabel"]').get_text(strip=True),
                    url="https://cian.ru" + item.select_one('a[data-name="LinkArea"]')['href'],
                    timestamp=datetime.now().isoformat()
                )
                offers.append(offer)
            except Exception as e:
                print(f"Ошибка парсинга объявления CIAN: {str(e)}")
                continue

        return offers

    async def scrape_yandex(self, session):
        url = 'https://realty.yandex.ru/moskva_i_moskovskaya_oblast/snyat/kvartira/'
        html = await self.fetch(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        for item in soup.select('article[data-test="offer-card"]'):
            try:
                offer = RealtyOffer(
                    source='yandex',
                    title=item.select_one('span[data-test="offer-title"]').get_text(strip=True),
                    price=item.select_one('span[data-test="offer-price"]').get_text(strip=True),
                    address=item.select_one('div[data-test="address"]').get_text(strip=True),
                    url="https://realty.yandex.ru" + item.find('a')['href'],
                    timestamp=datetime.now().isoformat()
                )
                offers.append(offer)
            except Exception as e:
                print(f"Ошибка парсинга объявления Яндекс: {str(e)}")
                continue

        return offers

    async def scrape_avito(self, session):
        url = 'https://www.avito.ru/moskva/kvartiry/sdam/na_dlitelnyy_srok'
        html = await self.fetch(session, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        for item in soup.select('div[data-marker="item"]'):
            try:
                offer = RealtyOffer(
                    source='avito',
                    title=item.select_one('h3[itemprop="name"]').get_text(strip=True),
                    price=item.select_one('meta[itemprop="price"]')['content'] + " ₽",
                    address=item.select_one('[data-marker="item-address"]').get_text(strip=True),
                    url="https://www.avito.ru" + item.select_one('a[data-marker="item-title"]')['href'],
                    timestamp=datetime.now().isoformat()
                )
                offers.append(offer)
            except Exception as e:
                print(f"Ошибка парсинга объявления Авито: {str(e)}")
                continue

        return offers

    async def scrape_all(self):
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.scrape_cian(session),
                self.scrape_yandex(session),
                self.scrape_avito(session)
            ]
            results = await asyncio.gather(*tasks)
            return [offer for sublist in results for offer in sublist]


def load_subscriptions():
    if SUBSCRIPTIONS_FILE.exists():
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {user_id: UserSubscription.from_dict(sub) for user_id, sub in data.items()}
    return {}


def save_subscriptions(subscriptions):
    data = {user_id: sub.to_dict() for user_id, sub in subscriptions.items()}
    with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_offers():
    if OFFERS_FILE.exists():
        with open(OFFERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [RealtyOffer.from_dict(offer) for offer in data]
    return []


def save_offers(offers):
    data = [offer.to_dict() for offer in offers]
    with open(OFFERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_notifications():
    if NOTIFICATIONS_FILE.exists():
        with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                user_id: {
                    'last_notification_date': datetime.fromisoformat(notif['last_notification_date']).date(),
                    'count': notif['count']
                }
                for user_id, notif in data.items()
            }
    return {}


def save_notifications(notifications):
    data = {
        user_id: {
            'last_notification_date': notif['last_notification_date'].isoformat(),
            'count': notif['count']
        }
        for user_id, notif in notifications.items()
    }
    with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def send_offer_notification(user_id, offer):

    notifications = load_notifications()
    today = date.today()

    user_notif = notifications.get(str(user_id), {
        'last_notification_date': today,
        'count': 0
    })

    if user_notif['last_notification_date'] != today:
        user_notif['count'] = 0
        user_notif['last_notification_date'] = today

    if user_notif['count'] >= MAX_DAILY_NOTIFICATIONS:
        print(f"Достигнут лимит уведомлений для пользователя {user_id}")
        try:
            await bot.send_message(
                user_id,
                f"Вы получили максимальное количество уведомлений за сегодня ({MAX_DAILY_NOTIFICATIONS}). "
                "Новые уведомления будут приходить завтра."
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения о лимите: {e}")
        return False

    # Отправляем уведомление
    message = (
        f"Новое объявление!\n\n"
        f"<b>{offer.title}</b>\n"
        f"Цена: {offer.price_text}\n"
        f"Адрес: {offer.address}\n"
        f"<a href='{offer.url}'>Ссылка на объявление</a>"
    )
    try:
        await bot.send_message(user_id, message, parse_mode='HTML')
        await asyncio.sleep(NOTIFICATION_DELAY)

        user_notif['count'] += 1
        notifications[str(user_id)] = user_notif
        save_notifications(notifications)
        return True
    except Exception as e:
        print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        return False


async def background_scraping():
    scraper = RealtyScraper()
    while True:
        try:
            print(f"{datetime.now().isoformat()} - Сканируем объявления...")

            new_offers = await scraper.scrape_all()
            existing_offers = load_offers()

            existing_urls = {o.url.strip().lower() for o in existing_offers}
            unique_new_offers = [
                o for o in new_offers
                if o.url.strip().lower() not in existing_urls
            ]

            if unique_new_offers:
                print(f"Найдено {len(unique_new_offers)} новых объявлений")
                all_offers = existing_offers + unique_new_offers
                save_offers(all_offers)
            else:
                print("Новых объявлений не найдено")

            subscriptions = load_subscriptions()
            if subscriptions:
                print("Проверяем объявления для подписчиков...")
                for user_id, sub in subscriptions.items():
                    suitable_offers = [
                        o for o in all_offers
                        if not o.processed
                           and o.price_value <= sub.max_price
                           and o.distance_value <= sub.max_distance
                    ]

                    if suitable_offers:
                        print(f"Найдено {len(suitable_offers)} подходящих объявлений для {user_id}")
                        sent_count = 0
                        for offer in suitable_offers:
                            if await send_offer_notification(user_id, offer):
                                sent_count += 1
                                offer.processed = True

                                if sent_count >= MAX_DAILY_NOTIFICATIONS:
                                    break
                        save_offers(all_offers)

        except Exception as e:
            print(f"Ошибка в background_scraping: {e}")

        await asyncio.sleep(3600)


@router.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для отслеживания объявлений о съеме жилья.\n\n"
        "Доступные команды:\n"
        "/subscribe - подписаться на уведомления\n"
        "/unsubscribe - отписаться от уведомлений\n"
        "/my_subscriptions - просмотреть текущие подписки\n"
        "/test_notify - тестовое уведомление\n\n"
        f"Лимит: не более {MAX_DAILY_NOTIFICATIONS} уведомлений в день"
    )


@router.message(Command('subscribe'))
async def cmd_subscribe(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите максимальную цену аренды (в рублях):\n"
        "Например: 50000"
    )
    await state.set_state(SubscribeStates.waiting_for_max_price)


@router.message(StateFilter(SubscribeStates.waiting_for_max_price))
async def process_max_price(message: types.Message, state: FSMContext):
    try:
        max_price = int(message.text)
        await state.update_data(max_price=max_price)
        await message.answer(
            "Теперь введите максимальное расстояние до метро (в минутах пешком):\n"
            "Например: 15"
        )
        await state.set_state(SubscribeStates.waiting_for_max_distance)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для цены")


@router.message(StateFilter(SubscribeStates.waiting_for_max_distance))
async def process_max_distance(message: types.Message, state: FSMContext):
    try:
        max_distance = int(message.text)
        user_data = await state.get_data()

        subscriptions = load_subscriptions()
        subscriptions[str(message.from_user.id)] = UserSubscription(
            max_price=user_data['max_price'],
            max_distance=max_distance,
            created_at=datetime.now().isoformat()
        )
        save_subscriptions(subscriptions)

        await state.clear()
        await message.answer(
            f"Вы успешно подписались на уведомления!\n\n"
            f"Критерии:\n"
            f"Максимальная цена: {user_data['max_price']} ₽\n"
            f"Максимальное расстояние до метро: {max_distance} мин.\n\n"
            f"Лимит: не более {MAX_DAILY_NOTIFICATIONS} уведомлений в день."
        )

        existing_offers = load_offers()
        if existing_offers:
            suitable_offers = [
                o for o in existing_offers
                if o.price_value <= user_data['max_price']
                   and o.distance_value <= max_distance
            ]

            if suitable_offers:
                sent_count = 0
                await message.answer(
                    f"Найдено {len(suitable_offers)} подходящих существующих объявлений")
                for offer in suitable_offers:
                    if await send_offer_notification(message.from_user.id, offer):
                        sent_count += 1
                        if sent_count >= MAX_DAILY_NOTIFICATIONS:
                            break

    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для расстояния.")


@router.message(Command('unsubscribe'))
async def cmd_unsubscribe(message: types.Message):
    subscriptions = load_subscriptions()
    user_id = str(message.from_user.id)

    if user_id in subscriptions:
        del subscriptions[user_id]
        save_subscriptions(subscriptions)
        await message.answer("Вы успешно отписались от уведомлений.")
    else:
        await message.answer("У вас нет активных подписок.")


@router.message(Command('my_subscriptions'))
async def cmd_my_subscriptions(message: types.Message):
    subscriptions = load_subscriptions()
    user_id = str(message.from_user.id)

    if user_id in subscriptions:
        sub = subscriptions[user_id]
        notifications = load_notifications()
        user_notif = notifications.get(user_id, {'count': 0})

        await message.answer(
            f"Ваши текущие критерии подписки:\n\n"
            f"• Максимальная цена: {sub.max_price} ₽\n"
            f"• Максимальное расстояние до метро: {sub.max_distance} мин.\n\n"
            f"Статистика:\n"
            f"• Уведомлений сегодня: {user_notif['count']}/{MAX_DAILY_NOTIFICATIONS}\n"
            f"• Подписка активна с: {sub.created_at}"
        )
    else:
        await message.answer("У вас нет активных подписок. Используйте /subscribe чтобы создать подписку.")


@router.message(Command('test_notify'))
async def cmd_test_notify(message: types.Message):
    test_offer = RealtyOffer(
        source='test',
        title='Тестовое объявление',
        price='30000 ₽',
        address='5 мин от метро',
        url='https://example.com',
        timestamp=datetime.now().isoformat()
    )
    if await send_offer_notification(message.from_user.id, test_offer):
        await message.answer("Тестовое уведомление отправлено")
    else:
        await message.answer("Не удалось отправить тестовое уведомление (возможно, достигнут дневной лимит)")


async def main():
    asyncio.create_task(background_scraping())

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
