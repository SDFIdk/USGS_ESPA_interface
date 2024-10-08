from landsat_product_name_query import landsat_query
from plot_stats import plot_landsat_data

import requests
import json
import netrc
import sys
import os
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import tarfile
from pprint import pprint

ESPA_HOST = 'https://espa.cr.usgs.gov/api/v1/'
LOG_FILE_PATH = 'order_log.txt'  # Default log file path

def espa_api(endpoint, verb='get', username = None, password = None, body=None, uauth=None):

    """ 
    ## espa_api: A Function
    * See the [ESPA API Source Code](https://github.com/USGS-EROS/espa-api/)
    * Visit the [ESPA On-Demand Interface](https://espa.cr.usgs.gov)

    # User Guide:
    # https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1417_ESPA-On-Demand-Interface_User-Guide-v15.pdf#

    First and foremost, define a simple function for interacting with the API. 
    
    The key things to watch for:
    
    * Always scrub for a `"messages"` field returned in the response, it is only informational about a request
      * **Errors** (`"errors"`): Brief exlaination about why a request failed
      * **Warnings** (`"warnings"`): Cautions about a successful response
    * Always make sure the requested HTTP `status_code` returned is valid 
      * **GET**: `200 OK`: The requested resource was successfully fetched (result can still be empty)
      * **POST**: `201 Created`: The requested resource was created
      * **PUT**: `202 Accepted`: The requested resource was updated

    If credentials for USGS API services are not provided, netrc will be used.
    """


    if username is None:
        username, _, password = netrc.netrc().authenticators(ESPA_HOST)

    auth_tup = uauth if uauth else (username, password)
    response = getattr(requests, verb)(ESPA_HOST + endpoint, auth=auth_tup, json=body)
    # print('{} {}'.format(response.status_code, response.reason))
    data = response.json()
    if isinstance(data, dict):
        messages = data.pop("messages", None)  
        if messages:
            print((json.dumps(messages, indent=4)))
    try:
        response.raise_for_status()
    except Exception as e:
        print(e)
        return None
    else:
        return data

def test_api(api):
    """
    Tests connection and credentials status to USGS ESPA
    """
    print('GET /api/v1/user')
    print((json.dumps(api, indent=4)))

def print_valid_projections(api):
    """
    ESPA can produce outputs all of the same geographic projections.  
    Call to show the available projection parameters that can be used
    """
    print('GET /api/v1/projections')
    print(json.dumps(list(api.keys())))

def dk_proj():
    return {
    'utm': {
        'zone_ns': 'north',
        'zone': 32,
        }
    }

def build_espa_order(ls_products, product_type = ['et'], resample = 'cc', data_format = 'gtiff', note = None):

    l8_ls = [ls for ls in ls_products if ls[0:5] == 'LC08_']
    l9_ls = [ls for ls in ls_products if ls[0:5] == 'LC09_']

    product_type = ['et']

    order = espa_api('available-products', body=dict(inputs=ls_products))

    for sensor in order.keys():
        if isinstance(order[sensor], dict) and order[sensor].get('inputs'):
            if set(l9_ls) & set(order[sensor]['inputs']):
                order[sensor]['products'] = product_type
            if set(l8_ls) & set(order[sensor]['inputs']):
                order[sensor]['products'] = product_type

    # Add in the rest of the order information
    order['projection'] = dk_proj()
    order['format'] = data_format
    order['resampling_method'] = resample
    if note is not None: order['note'] = note

    return order

def print_order_request(order):
    print((json.dumps(order, indent=4)))

class OrderTools:

    # TODO 
    # SET THIS THING UP WITH A BETTER LOG, 
    # ENSURE THE LOG HAS A DATE ASSOCIATED WITH THE ORDER OR EXTRACT IT IF POSSIBLE
    # MAKE SURE ORDERS OVER 7 DAYS OLD ARE REMOVED
    # 
    # DOCUMENTATION FOR ALL ORDERS
    # ORDERS SHOULDNT PRINT BUT RETURN, PRINT AS OPTION
    # MAYBE CLI?

    def __init__(self, espa_api):
        self.espa_api = espa_api

    def place_order(self, order, log_file_path=LOG_FILE_PATH):
        resp = self.espa_api('order', verb='post', body=order)
        order_id = resp['orderid']

        with open(log_file_path, 'a') as log_file:
            log_file.write(f"{order_id}\n")
        
        return order_id
    

    def read_order_ids(self, log_file_path=LOG_FILE_PATH):
        if not os.path.exists(log_file_path):
            return []

        with open(log_file_path, 'r') as log_file:
            order_ids = [line.strip() for line in log_file if line.strip()]
        return order_ids
    

    def check_order_status(self, log_file_path=LOG_FILE_PATH):
        order_ids = order_tools.read_order_ids(log_file_path)
        for order_id in order_ids:
            print(f'GET /api/v1/order-status/{order_id}')
            resp = self.espa_api(f'order-status/{order_id}')
            print(json.dumps(resp, indent=4))


    def check_completed_orders(self, log_file_path=LOG_FILE_PATH):
        order_ids = order_tools.read_order_ids(log_file_path)
        for order_id in order_ids:
            resp = self.espa_api(f'item-status/{order_id}', body={'status': 'complete'})
            print(json.dumps(resp[order_id], indent=4))


    def check_order_backlog(self, log_file_path=LOG_FILE_PATH):
        order_ids = order_tools.read_order_ids(log_file_path)
        for order_id in order_ids:
            resp = self.espa_api(f'list-orders/{order_id}', body= {"status": ["complete", "ordered"]})
            if ' not found' in resp: print('GOTCHA')

            print(resp)

            #TODO GET MESSAGES OUT OF THE ESPA API OR PROCESS THEM IN IT

            # for key, value in resp.items():
            #     print(key)
            #     print('...')
            #     print(value)

            # print('AAA')
            # print(resp)
            # print((json.dumps(resp, indent=4)))
            sys.exit()


    def get_download_urls(self, log_file_path=LOG_FILE_PATH, order_ids = None):
        """
        Returns a list of download links from either a provided list of orders
        or if not, all placed and available orders associated with USGS user
        """

        if order_ids is None:
            order_ids = order_tools.read_order_ids(log_file_path)

        if not type(order_ids) == list: order_ids = [order_ids]

        for order_id in order_ids:
            resp = self.espa_api(f'item-status/{order_id}', body={'status': 'complete'})
            for item in resp[order_id]:
                yield item.get('product_dload_url')

    def find_previous_orders(self, log_file_path=LOG_FILE_PATH): 
        """
        Find previous orders 
        List backlog orders for the authenticated user.
        """
        
        print('GET /api/v1/list-orders')
        filters = {"status": ["ordered"]}
        return self.espa_api('list-orders', body=filters)



def download_file(url, dir_path):
    """
    Download a file from a URL to a specified directory and extract if it's a tar.gz file.
    
    Parameters:
    - url (str): The URL of the file to download.
    - dir_path (str): The directory path where the file will be saved and extracted.
    """

    order_number = url.split('-')[3] + '/'

    dir_path = os.path.join(dir_path, order_number)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Parse the URL to get the file name
        filename = os.path.basename(urlparse(url).path)
        file_path = os.path.join(dir_path, filename)
        
        # Write the file to the directory
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        print(f"Downloaded: {filename}")

        # Extract the tar.gz file to its own directory
        if filename.endswith('.tar.gz'):
            extract_dir = os.path.join(dir_path, filename[:-7])
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(file_path, 'r:gz') as tar:
                tar.extractall(path=extract_dir)
            print(f"Extracted: {filename} to {extract_dir}")

    except Exception as e:
        print(f"Failed to download or extract {url}: {e}")


def download_files(urls, dir_path, num_threads=4):
    """
    Download multiple files from a list of URLs to a specified directory using multiple threads.
    
    Parameters:
    - urls (list): A list of URLs of the files to download.
    - dir_path (str): The directory path where the files will be saved.
    - num_threads (int): The number of threads to use for downloading. Defaults to 4.
    """

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(lambda url: download_file(url, dir_path), urls)



if __name__ == "__main__":

    # test_api(espa_api('user'))

    start_date = "2023-01-01"
    end_date = "2024-01-01"

    shape = "shapes/gludsted/POLYGON.shp"
    # shape = "shapes/skjern/POLYGON.shp"
    # shape = "shapes/soroe/POLYGON.shp"
    # shape = "shapes/voulund/POLYGON.shp"

    destination_dir = "J:/javej/drought/SSEB_files/"

    # order_tools = OrderTools(espa_api)
    # order_tools.check_order_backlog()

    # sys.exit()

    
    # print(find_previous_orders())


    #DOWNLOAD ORDERED DATA

    # CREATE NEW ORDER
    # urls = [url for url in get_download_urls()]    
    # download_files(urls, destination_dir)

    # ls_products, stats = landsat_query.query_landsat_eodag(
    #     start_date, 
    #     end_date, 
    #     shape, 
    #     cloudcover=100, 
    #     output_stats = True, 
    #     figure_name = None
    #     )
    # print(len(ls_products))



    
    # order = build_espa_order(ls_products, product_type = ['et'], resample = 'cc', data_format = 'gtiff', note = None)
    # place_order(order)

    # check_order_backlog()
