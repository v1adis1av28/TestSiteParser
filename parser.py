from urllib.request import urlopen
from bs4 import BeautifulSoup
#Ссылка на магазин, который парсим
ROOT = 'https://vlg.saturn.net/'

def get_first_text(iter):
    for item in iter:
        return item.text.strip()


#Получаем html страницы
def fetcher():
    with urlopen(ROOT) as request:
        return request.read()

#Парсим страницу
def parser(html):
    soup = BeautifulSoup(html, features="lxml")
    for i, div in enumerate(soup.select('div.top_menu_catalogBlock a.top_menu_catalogBlock_listBlock_item.swiper-slide')):
        categories = get_first_text(div)#Получаем категории товаров
        url = div.get('href')
        print(categories, ' ---> ', ROOT+url)



if __name__ == '__main__':
    parser(fetcher())