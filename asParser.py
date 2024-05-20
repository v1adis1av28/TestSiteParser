import asyncio
import aiohttp
from bs4 import BeautifulSoup
from models import db_session, Materials  # Импорт неизвестен, но должен быть для работы с вашей базой данных
import time  # Импортируем модуль для измерения времени выполнения

# URL корневой страницы и каталога товаров
ROOT = 'https://vlg.saturn.net/'
ITEMS_ROOT = "https://vlg.saturn.net/catalog/Stroymateriali/"

# Максимальное количество одновременных задач
PARALLEL_TASKS = 60
# Семафор для ограничения количества одновременных запросов
MAX_DOWNLOAD_AT_TIME = asyncio.Semaphore(PARALLEL_TASKS)


def get_first_text(iter):
    # Вспомогательная функция для извлечения текста из элементов BS4
    for item in iter:
        return item.text.strip()


async def fetch(session, url):
    # Асинхронная функция для загрузки HTML с URL
    async with MAX_DOWNLOAD_AT_TIME:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Error fetching {url}: {response.status}")
                    return None
        except Exception as e:
            print(f"Exception fetching {url}: {e}")
            return None


def parser_categories(session, html):
    # Функция для парсинга категорий из корневой страницы
    urls = []
    soup = BeautifulSoup(html, features="lxml")
    for div in soup.select('div.top_menu_catalogBlock a.top_menu_catalogBlock_listBlock_item.swiper-slide'):
        categories = get_first_text(div)
        url = div.get('href')
        if url:
            full_url = ROOT + url
            urls.append(full_url)
            print(f"Category: {categories} ---> URL: {full_url}")
    return urls


async def parser_items(session, url):
    # Асинхронная функция для парсинга товаров из страницы категории
    page_number = 1
    items_url = f"{url}?page={page_number}&per_page=20"
    items_html = await fetch(session, items_url)
    if items_html:
        soup = BeautifulSoup(items_html, features="lxml")
        tasks = []
        item_divs = soup.select('div.catalog_Level2__goods_list__block li.catalog_Level2__goods_list__item')
        if not item_divs:
            print(f"No more items found on {items_url}")
        for div in item_divs:
            name = get_first_text(div.select('div.goods_card_link a.goods_card_text.swiper-no-swiping'))
            article = get_first_text(div.select('div.goods_card_articul span'))
            cost = get_first_text(div.select('div.goods_card_price_discount_value span.js-price-value'))
            volume_el = div.select('div.goods_card_price_units')
            volume = ''
            if volume_el:
                for el in volume_el:
                    button_wrapper = el.find('div', class_='goods_card_price_units_wrapper')
                    if button_wrapper:
                        active_button = button_wrapper.find('button', class_='units_active')
                        if active_button:
                            volume = f"Цена за {active_button.get_text(strip=True)}"
                    else:
                        text = el.find(class_='price_unit_item_text')
                        if text:
                            volume = f"Цена за {text.get_text(strip=True)}"
            link = div.select_one('div.goods_card_link a.goods_card_text.swiper-no-swiping')
            if link and 'href' in link.attrs:
                description_url = ROOT + link['href']
                tasks.append(fetch_description_and_save(session, name, article, cost, volume, description_url))
        await asyncio.gather(*tasks)


async def fetch_description_and_save(session, name, article, cost, volume, url):
    # Асинхронная функция для загрузки описания и сохранения товара в базу данных
    try:
        descrip_html = await fetch(session, url)
        if descrip_html:
            descrip_soup = BeautifulSoup(descrip_html, features='lxml')
            description_element = descrip_soup.select_one('div.catalog__goods__description__text')
            description = description_element.get_text(strip=True) if description_element else ""

            # Сохранение данных в базу данных (закомментировано, так как нет доступа к вашей базе данных)
            item = Materials(name=name, article=article, cost=int(cost), volume=volume, description=description)
            print(f"Item: {name}, Article: {article}, Cost: {cost}, Volume: {volume}, Description: {description}")
            # db_session.add(item)
            # db_session.commit()
    except Exception as e:
        print(f"Error reading from {url}: {e}")


async def gather_data():
    # Основная асинхронная функция для сбора данных
    async with aiohttp.ClientSession() as session:
        root_html = await fetch(session, ROOT)
        if root_html:
            category_urls = parser_categories(session, root_html)
            tasks = []
            for url in category_urls:
                tasks.append(parser_items(session, url))
            await asyncio.gather(*tasks)


if __name__ == '__main__':
    start_time = time.time()  # Записываем текущее время для измерения времени выполнения
    asyncio.run(gather_data())  # Запускаем основную асинхронную функцию
    end_time = time.time()  # Записываем время окончания выполнения
    print(f"Execution time: {end_time - start_time} seconds")  # Выводим время выполнения
