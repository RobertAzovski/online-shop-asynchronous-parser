import asyncio
import os
import time
from pathlib import Path
from urllib.request import urlopen

import aiofiles as aiof
import aiohttp
import bs4
import winshell

# define variables ?PAGEN_1=2
BASE_PATH = './'
BASE_URL = 'https://romatti.ru/catalog'
url_product_list = []
path_product_list = []
tasks_save_pics = []
tasks_save_txts = []


class Product():
    def __init__(self) -> None:
        self.artikul = None
        self.name = None
        self.price = None
        self.photos_path = None
        self.description = None
        self.ops = None
        self.variations = None
    
    MESSAGE: str = ('Артикул: {self.artikul}\n'
                    'Имя: {self.name}\n'
                    'Цена: {self.price}\n'
                    'Описание: {self.description}\n'
                    'Характеристики: {self.ops}\n'
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
    i = 1
    if (soup.find('li', {'class': 'bx-active'}).find('span').string == f'{i}'):
        print('True pagination')
        isHaveNextPage = True
        i = 2
    while isHaveNextPage:
        soup = bs4.BeautifulSoup(await get_html(f'{url_section}?PAGEN_1={i}'), 'html.parser')
        for link in soup.findAll('a', {'class': 'picture_wrapper'}):
            try:
                whole_product_path = url_section.replace(BASE_URL, '') + link['href'].replace('/catalog', '').replace('.html', '/')
                path_product_list.append(whole_product_path)
                url_product_list.append(BASE_URL + link['href'].replace('/catalog', ''))
            except KeyError:
                pass
        i += 1
        print('page------------------page---------------page')
        soup = bs4.BeautifulSoup(await get_html(f'{url_section}?PAGEN_1={i}'), 'html.parser')
        if (soup.find('li', {'class': 'bx-active'}).find('span').string == f'{i}') is False:
            print('False pagination')
            isHaveNextPage = False
        
        

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
    nbsp = u'\xa0'
    soup = bs4.BeautifulSoup(await get_html(url_product), 'html.parser')
    if soup.contents:
        try:
            product.artikul = soup.find('div', {'class': 'articul_code'}).find('span').string
            product.name = soup.find('div', {'class': 'articul_code'}).parent.find('h1').text.split(',')[0].replace('*', 'x')
            product.price = soup.find('div', {'class': 'product-item-detail-price-current'}).contents[0].replace(nbsp, '')
            product.photos_path = create_path(f'{path_product}/f/')
            if soup.find('div', {'data-value': 'description'}) is not None and soup.find('div', {'data-value': 'description'}).find('p'):
                product.description = soup.find('div', {'data-value': 'description'}).find('p').string
            else:
                product.description = 'Описание отсутствует'
            product.ops = dict(zip([prop.string for prop in soup.find_all('div', {'class': 'prop_title'})], [prop.string for prop in soup.find_all('div', {'class': 'prop_val'})]))
            if soup.find('div', {'class': 'product-item-scu-container-title'}):
                title = soup.find('div', {'class': 'product-item-scu-container-title'}).string
                var_list = [spec.find('div', {'class': 'product-item-scu-item-text'}).string for spec in soup.find_all('li', {'class': 'product-item-scu-item-text-container'})]
                product.variations = f'{title} - {var_list}'
            else:
                product.variations = 'Вариации отсутствуют'
            print(f'Task {i} - {product.name}')
        except Exception as err:
            raise err
        finally:
            task = asyncio.create_task(save_txts(path_product, product))
            tasks_save_txts.append(task)
            task = asyncio.create_task(save_pics(soup=soup, product=product))
            tasks_save_pics.append(task)

async def save_txts(path_product, product):
    async with aiof.open(create_path(f'{path_product}/{product.name}.txt'), 'w', encoding='utf-8') as file:
                await file.write(product.show_data())

async def save_pics(soup, product):
        image_url = None
        try:
            image_url = soup.find('img', title=product.name).get('src')
            if image_url is not None:
                async with aiof.open(f'{product.photos_path}\\1.jpg', "wb") as file:
                    try:
                        remote_file = await urlopen(f'http://romatti.ru{image_url}')
                        await file.write(remote_file.read())
                    except Exception as err:
                        pass
        except Exception as err:
            pass
            

def create_path(url_product):
    url_parts = url_product.replace(BASE_URL, '')
    new_path = os.path.abspath(os.sep.join([BASE_PATH, url_parts]))
    return new_path

async def make_directory_tree(url_product):
    Path(create_path(f'{url_product}/f/')).mkdir(parents=True, exist_ok=True)

async def main():
    # Get products urls
    await asyncio.gather(*[get_product_url(url_section) for url_section in get_custum_url()])
    # Make products directories
    await asyncio.gather(*[make_directory_tree(path) for path in path_product_list])
    # Save product urls shortcuts
    await asyncio.gather(*[save_url_shortcut(url, path) for url, path in zip(url_product_list, path_product_list)])
    # Parse product data
    await asyncio.gather(*[asyncio.shield(get_product_page_data(url, path, i)) for i, (url, path) in enumerate(zip(url_product_list, path_product_list))])
    # Save product data in txts
    await asyncio.gather(*tasks_save_txts)
    # Save product pics
    # await asyncio.gather(*tasks_save_pics)
    print(f'Всего товаров сохранено - {len(tasks_save_txts)}')

if __name__ == '__main__':
    start_time = time.time()
    print('Loading...')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    execution_time = round(time.time() - start_time, 3)
    print(f'Время выполнения программы: {execution_time} с.')