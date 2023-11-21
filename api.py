from dotenv import dotenv_values
from collections import namedtuple
import requests
import json
import pprint


Product = namedtuple('Product', [
    'id',
    'title',
    'description',
    'price',
    'picture_url',
])


def _get_response(url, method, params=None, data=None):
    base_url = 'http://localhost:1337'
    token = dotenv_values('.env')['STRAPI_TOKEN']
    headers = {
        'Authorization': f"bearer {token}"
    }
    methods = {
        'get': requests.get,
        'post': requests.post,
    }
    response = methods[method](base_url + url, headers=headers, params=params, json=data)
    response.raise_for_status()
    return response.content


def get_products(page=1, page_size=10):
    url = '/api/products/'
    params = {
        'pagination[page]': page,
        'pagination[pageSize]': page_size,
        'fields[0]': 'title',
    }

    response = json.loads(_get_response(url, 'get', params=params))
    page = response['meta']['pagination']['page']
    page_count = response['meta']['pagination']['pageCount']
    while page_count - 1 > 0:
        params['pagination[page]'] += 1
        page_count -= 1
        response['data'].extend(json.loads(_get_response(url, 'get', params=params))['data'])
    
    products = [Product(
                    item.get('id', None),
                    item['attributes'].get('title', None),
                    item['attributes'].get('description', None),
                    item['attributes'].get('price', None),
                    item['attributes'].get('picture_url', None),
                ) for item in response['data']]
    
    return products


def get_product(product_id):
    url = f'/api/products/{product_id}'
    params = {
        'fields[0]': 'title',
        'fields[1]': 'description',
        'fields[2]': 'price',
        'populate[picture][fields][0]': 'url',
    }

    response = json.loads(_get_response(url, 'get', params=params))
    product = Product(
        response['data']['id'],
        response['data']['attributes']['title'],
        response['data']['attributes']['description'],
        response['data']['attributes']['price'],
        response['data']['attributes']['picture']['data'][0]['attributes']['url']
    )
    return product


def get_picture(picture_url):
    picture = _get_response(picture_url, 'get')
    return picture


def create_cart(tg_id):
    url = '/api/carts'
    data = {
        'data': {
            'tg_id': str(tg_id),
        },
    }

    cart = json.loads(_get_response(url, 'post', data=data))
    return cart


def get_cart(tg_id):
    url = '/api/carts'
    params = {
        'filters[tg_id][$eq]': tg_id,
        # 'populate[0]': 'cart_products',
        'populate[cart_products][populate][0]': 'products',
     }

    cart = json.loads(_get_response(url, 'get', params=params))
    return cart


def get_cart_contents(tg_id):
    cart = get_cart(tg_id)
    cart_products = cart['data'][0]['attributes']['cart_products']['data']
    return cart_products


if __name__ == '__main__':
    pprint.pprint(get_products(1, 2))
