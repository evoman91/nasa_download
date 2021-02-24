import requests
import json
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
import os
import logging
import sys 

search_term = ['curiosity', 'perseverance', 'mars2020', 'mars 2020']
export_root = './NASA'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

consoleLogger = logging.StreamHandler(sys.stdout)
consoleLogger.setLevel(20)
consoleFormat = logging.Formatter('%(levelname)-8s %(message)s')
consoleLogger.setFormatter(consoleFormat)

logging.getLogger('').addHandler(consoleLogger)

download_list = os.path.join(export_root, 'download_list.txt')

def make_safe_filename(s):
    def safe_char(c):
        if c.isalnum():
            return c
        else:
            return "_"
    return "".join(safe_char(c) for c in s).rstrip("_")

def get_api_response(url):
  try:
    response = requests.get(url=url)
    return json.loads(response.content)
  except Exception as e:
    logger.error(e)
    return None

def make_dir(dir):
  try:
    os.makedirs(dir)
  except FileExistsError:
      # directory already exists
      pass

def get_item_links(href):
  item_links = get_api_response(url=href)
  if item_links:
    for link in item_links:
      if 'orig' in link:
        link_org = link
      elif 'large' in link:
        link_large = link
      elif 'medium' in link:
        link_medium = link
      elif 'small' in link:
        link_small = link
      elif 'thumb' in link:
        link_thumb = link
    
    if link_org:
      return link_org,'link_org'
    elif link_large:
      return link_large,'link_large'
    elif link_medium:
      return link_medium,'link_medium'
    elif link_small:
      return link_small,'link_small'
    elif link_thumb:
      return link_thumb,'link_thumb'
    else:
      return None,None
  else: 
      return None,None

def download_media(url, nasa_id, folder_structure):
  url_detail = urlparse(url)
  file_ext = Path(url_detail.path).suffix
  download_file_path = os.path.join(folder_structure, f'{nasa_id}{file_ext}')
  try:
    file_content = requests.get(url, allow_redirects=True)
    open(download_file_path, 'wb').write(file_content.content)
    return True
  except Exception as e:
    logger.error(e)
    logger.error(f'Failed to download {nasa_id}')
    return False

def add_download(nasa_id,date,download_success,download_type):
  line = f'&&{nasa_id}|{date}|{download_success}|{download_type}\n'
  try:
    with open(download_list, 'a') as file:
      file.write(line)
  except Exception as e:
    logger.error('Failed to write to download list')
    raise 

def check_downloaded(nasa_id):
  try:
    if os.path.exists(download_list):
      with open(download_list, 'r') as read_obj:     
        for line in read_obj:
          if nasa_id in line:
            return True
      return False
  except Exception as e:
    logger.error(e)
    logger.error('Failed to check download file')
    raise 

def process_link(meta_object):
  nasa_id = meta_object['data'][0]['nasa_id']
  nasa_id = make_safe_filename(s=nasa_id)
  downloaded = check_downloaded(nasa_id=nasa_id)
  if not downloaded:
    datetime_object = datetime.strptime(meta_object['data'][0]['date_created'], '%Y-%m-%dT%H:%M:%SZ')
    datetime_object = datetime_object.date()
    logger.info(f'Downloading - {nasa_id} - {datetime_object}')
    folder_structure = os.path.join(export_root, str(datetime_object.year), str(datetime_object.month), str(datetime_object.day))
    make_dir(dir=folder_structure)
    
    image_detail = get_item_links(href=meta_object['href'])
    image_download_url = image_detail[0]
    image_download_type = image_detail[1]

    download_success = False
    if image_download_url:
      download_success = download_media(url=image_download_url, nasa_id=nasa_id, folder_structure=folder_structure)
    if download_success:
      meta_data_file = os.path.join(folder_structure, f'{nasa_id}.json')
      try:
        with open(meta_data_file, 'w') as file:
          file.write(json.dumps(meta_object))
      except Exception as e: 
        logger.error('Failed to write meta data to disk')
        download_success = False

    add_download(nasa_id=nasa_id,download_success=download_success,download_type=image_download_type,date=datetime_object)

def process(url):
  response = get_api_response(url=url)
  if 'items' in response['collection']: 
    for item in response['collection']['items']:
       process_link(meta_object=item)

  if 'links' in response['collection']:
    for link in response['collection']['links']:
      if link['prompt'] == 'Next':
        process(url=link['href'])

for key_word in search_term:
  logger.info(f'Processing {key_word}')
  logger.info('Starting base search')
  url = f'https://images-api.nasa.gov/search?q={key_word}&media_type=image'
  process(url=url)
  logger.info('Starting keyword search')
  url = f'https://images-api.nasa.gov/search?keywords={key_word}&media_type=image'
  process(url=url)
  logger.info('---')



