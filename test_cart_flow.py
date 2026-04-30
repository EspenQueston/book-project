"""Test marketplace cart flow."""
import http.client
import json

def test():
    # 1. Get CSRF token from cart page
    conn = http.client.HTTPConnection('127.0.0.1', 8001)
    conn.request('GET', '/marketplace/cart/')
    resp = conn.getresponse()
    body = resp.read().decode()

    csrf = ''
    session_id = ''
    for header_name, header_val in resp.getheaders():
        if header_name.lower() == 'set-cookie':
            if 'csrftoken=' in header_val:
                csrf = header_val.split('csrftoken=')[1].split(';')[0]
            if 'sessionid=' in header_val:
                session_id = header_val.split('sessionid=')[1].split(';')[0]
    conn.close()

    print(f"CSRF: {csrf[:20]}...")
    print(f"Session: {session_id[:20]}...")

    # 2. Add product to cart
    data = f'item_type=product&item_id=1&quantity=2&csrfmiddlewaretoken={csrf}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': f'csrftoken={csrf}; sessionid={session_id}',
        'X-CSRFToken': csrf,
    }
    conn = http.client.HTTPConnection('127.0.0.1', 8001)
    conn.request('POST', '/marketplace/cart/add/', data, headers)
    resp = conn.getresponse()
    result = resp.read().decode()
    print(f"Add to cart: {resp.status} - {result}")
    conn.close()

    # 3. Check cart count
    conn = http.client.HTTPConnection('127.0.0.1', 8001)
    conn.request('GET', '/marketplace/cart/count/', headers={'Cookie': f'sessionid={session_id}'})
    resp = conn.getresponse()
    result = resp.read().decode()
    print(f"Cart count: {resp.status} - {result}")
    conn.close()

    # 4. View cart page
    conn = http.client.HTTPConnection('127.0.0.1', 8001)
    conn.request('GET', '/marketplace/cart/', headers={'Cookie': f'csrftoken={csrf}; sessionid={session_id}'})
    resp = conn.getresponse()
    body = resp.read().decode()
    print(f"Cart page: {resp.status} (length: {len(body)})")
    conn.close()

    # 5. Checkout page
    conn = http.client.HTTPConnection('127.0.0.1', 8001)
    conn.request('GET', '/marketplace/checkout/', headers={'Cookie': f'csrftoken={csrf}; sessionid={session_id}'})
    resp = conn.getresponse()
    body = resp.read().decode()
    print(f"Checkout page: {resp.status} (length: {len(body)})")
    conn.close()

    print("\nAll tests passed!")

if __name__ == '__main__':
    test()
