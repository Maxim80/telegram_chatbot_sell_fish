from dotenv import dotenv_values
import requests
import json


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


def get_products():
    url = '/api/products/'
    params = {
        'pagination[page]': 1,
        'pagination[pageSize]': 10,
    }

    response = json.loads(_get_response(url, 'get', params=params))
    products = response['data']
    page = response['meta']['pagination']['page']
    page_count = response['meta']['pagination']['pageCount']
    while page_count - 1 > 0:
        params['pagination[page]'] += 1
        page_count -= 1
        response = json.loads(_get_response(url, 'get', params=params))
        products.extend(response['data'])
    
    return products


def get_product_info(product_id):
    url = f'/api/products/{product_id}'
    params = {
        'populate[0]': 'picture',
    }
    product = json.loads(_get_response(url, 'get', params=params))
    title = product['data']['attributes']['title']
    description = product['data']['attributes']['description']
    price = product['data']['attributes']['price']
    picture_url = product['data']['attributes']['picture']['data'][0]['attributes']['formats']['medium']['url']
    picture = _get_response(picture_url, 'get')
    return (title, description, price, picture)


def create_cart(tg_id):
    url = '/api/carts'
    data = {
        'data': {
            'tg_id': str(tg_id),
        },
    }
    response = _get_response(url, 'post', data=data)
    return json.loads(response)


def get_cart(tg_id):
    url = '/api/carts'
    params = {
        'filters[tg_id][$eq]': tg_id,
    }
    response = _get_response(url, 'get', params=params)
    return json.loads(response)


if __name__ == '__main__':
    print(get_cart(8177178))
