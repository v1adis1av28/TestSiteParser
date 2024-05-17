from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.error import URLError
import settings
import asyncio
import aiohttp
from models import db_session, Materials

# Ссылка на магазин, который парсим
ROOT = 'https://vlg.saturn.net/'
ITEMS_ROOT = "https://vlg.saturn.net/catalog/Stroymateriali/"

def get_first_text(iter):
    for item in iter:
        return item.text.strip()


# 1. Выбрать сайт который будете парсить
# 2. Определить ограничения на парсинг
# 3. Скачать инофрмацию по разделам в виде Название раздела -> URL
# 5. Записать при помощи SQLAlchemy полученные данные в БД

# Получаем html страницы
def fetcher():
    with urlopen(ROOT) as request:
        return request.read()


def ItemsFetcher(page_number=1):
    items_url = f"{ITEMS_ROOT}?page={page_number}&per_page=20"
    with urlopen(items_url) as request:
        return request.read()


# Парсим страницу
# Парсим Категории получаем ссылки на них
def parser_categories(html):
    urls = []
    soup = BeautifulSoup(html, features="lxml")
    for i, div in enumerate(
            soup.select('div.top_menu_catalogBlock a.top_menu_catalogBlock_listBlock_item.swiper-slide')):
        categories = get_first_text(div)  # Получаем категории товаров
        url = div.get('href')
        urls.append(ROOT + url)
        print(categories, ' ---> ', ROOT + url)
    return urls


# Парсим товары категории стройматериалы
# 4. Выкачать из любого раздела, в котором товары размещены более чем на одной странице, данные по всем товарам, а именно
# Артикул, Название, Стоимость, Описание, Объем упаковки.

def parser(html):
    soup = BeautifulSoup(html, features="lxml")
    for i, div in enumerate(soup.select('div.catalog_Level2__goods_list__block li.catalog_Level2__goods_list__item')):
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
        # Extracting description
        description = ""
        link = div.select_one('div.goods_card_link a.goods_card_text.swiper-no-swiping')
        if link and 'href' in link.attrs:
            descrip_url = ROOT + link['href']
            try:
                descrip_html = urlopen(descrip_url).read()
                descrip_soup = BeautifulSoup(descrip_html, features='lxml')
                description_element = descrip_soup.select_one('div.catalog__goods__description__text')
                if description_element:
                    description = description_element.get_text(strip=True)
            except URLError as e:
                print(f"Error reading from {descrip_url}: {e}")
        Item = Materials(name=name, article=article, cost=int(cost), volume=volume, description=description)
        db_session.add(Item)
        db_session.commit()


if __name__ == '__main__':
    page_number = 1
    parser(ItemsFetcher(page_number))
    # for i in range(65):
    #   html = ItemsFetcher(page_number)
    #  page_number += 1
    # parser(html)
