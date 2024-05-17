import asyncio
import aiohttp
from bs4 import BeautifulSoup
from models import db_session, Materials

# Ссылка на магазин, который парсим
ROOT = 'https://vlg.saturn.net/'
ITEMS_ROOT = "https://vlg.saturn.net/catalog/Stroymateriali/"

# Функция для получения текста первого элемента в итераторе
def get_first_text(iter):
    for item in iter:
        return item.text.strip()

# Асинхронная функция для получения HTML страницы
async def fetch(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            return await response.text()
        else:
            print(f"Error fetching {url}: {response.status}")
            return None

# Асинхронная функция для парсинга категорий с корневой страницы
async def parser_categories(html):
    urls = []
    soup = BeautifulSoup(html, features="lxml")
    # Извлечение ссылок на категории
    for div in soup.select('div.top_menu_catalogBlock a.top_menu_catalogBlock_listBlock_item.swiper-slide'):
        categories = get_first_text(div)
        url = div.get('href')
        if url:
            full_url = ROOT + url
            urls.append(full_url)
            print(categories, ' ---> ', full_url)
    return urls

# Асинхронная функция для парсинга товаров на странице категории
async def parser_items(session, html):
    soup = BeautifulSoup(html, features="lxml")
    tasks = []
    # Извлечение данных о товарах
    for div in soup.select('div.catalog_Level2__goods_list__block li.catalog_Level2__goods_list__item'):
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

        # Извлечение ссылки на страницу с описанием товара
        link = div.select_one('div.goods_card_link a.goods_card_text.swiper-no-swiping')
        if link and 'href' in link.attrs:
            description_url = ROOT + link['href']
            # Создание задачи для получения и сохранения описания товара
            tasks.append(fetch_description_and_save(session, name, article, cost, volume, description_url))

    # Ожидание завершения всех задач
    await asyncio.gather(*tasks)

# Асинхронная функция для получения описания товара и сохранения его в базе данных
async def fetch_description_and_save(session, name, article, cost, volume, url):
    try:
        descrip_html = await fetch(session, url)
        if descrip_html:
            descrip_soup = BeautifulSoup(descrip_html, features='lxml')
            description_element = descrip_soup.select_one('div.catalog__goods__description__text')
            description = description_element.get_text(strip=True) if description_element else ""

            # Сохранение данных в базу данных
            item = Materials(name=name, article=article, cost=int(cost), volume=volume, description=description)
            print(name, article, cost, description, volume)
            db_session.add(item)
            db_session.commit()
    except Exception as e:
        print(f"Error reading from {url}: {e}")

# Основная асинхронная функция
async def main():
    async with aiohttp.ClientSession() as session:
        # Получаем и парсим корневую страницу для категорий
        root_html = await fetch(session, ROOT)
        if root_html:
            category_urls = await parser_categories(root_html)

            # Получаем и парсим страницы с товарами для каждой категории
            for url in category_urls:
                page_number = 1
                while True:
                    items_url = f"{url}?page={page_number}&per_page=20"
                    items_html = await fetch(session, items_url)
                    if items_html:
                        await parser_items(session, items_html)
                        page_number += 1
                    else:
                        break

if __name__ == '__main__':
    # Запуск основного асинхронного цикла
    asyncio.run(main())
