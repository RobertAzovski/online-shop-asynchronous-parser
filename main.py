import time
import asyncio
import os, winshell
import bs4
import aiohttp
from pathlib import Path


# define variables ?PAGEN_1=2
BASE_PATH = './'
BASE_URL = 'https://romatti.ru/catalog'
url_product_list = []
path_product_list = []


class Product():
    def __init__(self) -> None:
        self.artikul = None
        self.name = None
        self.price = None
        self.photos_path = None
        self.description = None
        self.ops = None
        self.variations = None
        self.url = None
    
    MESSAGE: str = ('Артикул: {self.artikul}\n'
                    'Имя: {self.name}\n'
                    'Цена: {self.price}\n'
                    'Описание: {self.description}\n'
                    'Характеристики: {"\n".join(["\t"+key+": "+value for key, value in self.ops])}\n'
                    'Вариации: {self.variations}\n')

    def show_data(self):
        return self.MESSAGE.format(self=self)

async def fetch(client, url_section):
    async with client.get(url_section) as resp:
        assert resp.status == 200
        return await resp.text()

async def get_html(url_section):
    async with aiohttp.ClientSession() as client:
        html = await fetch(client, url_section)
        return html

async def get_product_url(url_section):
    soup = bs4.BeautifulSoup(await get_html(url_section), 'html.parser')
    for link in soup.findAll('a', {'class': 'picture_wrapper'}):
        try:
            whole_product_path = url_section.replace(BASE_URL, '') + link['href'].replace('/catalog', '').replace('.html', '/')
            path_product_list.append(whole_product_path)
            url_product_list.append(BASE_URL + link['href'].replace('/catalog', ''))
        except KeyError:
            pass

def get_custum_url():
    with open('urls.txt', 'r') as file:
        for url_section in file:
            yield url_section.rstrip()

async def save_url_shortcut(url_product, path_product):
    with winshell.shortcut(create_path(f'{path_product}/shortcut.lnk')) as shortcut:
        shortcut.path = url_product
        shortcut.write()

async def get_product_page_data(url_product, path_product, i):
    product = Product()
    soup = bs4.BeautifulSoup(await get_html(url_product), 'html.parser')
    if soup.contents:
        try:
            product.artikul = soup.find('div', {'class': 'articul_code'}).find('span').string
            product.name = soup.find('div', {'class': 'articul_code'}).parent.find('h1').text.split(',')[0]
            product.price = soup.find('div', {'class': 'product-item-detail-price-current'}).contents
            product.photos_path = create_path(f'{path_product}/f/')
            # product.description = soup.find('div', {'data-value': 'description'}).find('p').string
            product.ops = dict(zip([prop.string for prop in soup.find_all('div', {'class': 'prop_title'})], [prop.string for prop in soup.find_all('div', {'class': 'prop_val'})]))
            product.variations = [spec.string for spec in soup.find_all('div', {'class': 'product-item-scu-item-text'})]
            product.url = url_product
            print(f'Task {i} - {product.name}')
        except Exception as err:
            raise err
        finally:
            with open(create_path(f'{path_product}/{product.name}.txt'), 'w', encoding='utf-8') as file:
                file.write(product.show_data())

def create_path(url_product):
    url_parts = url_product.replace(BASE_URL, '')
    new_path = os.path.abspath(os.sep.join([BASE_PATH, url_parts]))
    return new_path

async def make_directory_tree(url_product):
    Path(create_path(url_product)).mkdir(parents=True, exist_ok=True)

async def main():
    # Get products urls
    await asyncio.gather(*[get_product_url(url_section) for url_section in get_custum_url()])
    # Make products directories
    await asyncio.gather(*[make_directory_tree(path) for path in path_product_list])
    # Save product urls shortcuts
    await asyncio.gather(*[save_url_shortcut(url, path) for url, path in zip(url_product_list, path_product_list)])
    # Parse product data and save
    await asyncio.gather(*[asyncio.shield(get_product_page_data(url, path, i)) for i, (url, path) in enumerate(zip(url_product_list, path_product_list))])
    

if __name__ == '__main__':
    start_time = time.time()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    execution_time = round(time.time() - start_time, 3)
    print(f'Время выполнения программы: {execution_time} с.')