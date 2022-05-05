import json
import urllib3
import boto3
from datetime import datetime, timedelta

# (you should probably use secrets manager)
SERVER = 'https://{tenant}.atlassian.net'
USER = '{your user}'
PASS = '{your password}'

def get_request(http, url):
    headers = urllib3.make_headers(basic_auth='{0}:{1}'.format(USER, PASS))
    headers['Content-Type'] = 'application/json'
    response = http.request('GET', url,
                            headers=headers)
    if response.status != 200:
        print("error: {}".format(response.data))
        raise Exception("problem with http")
    payload = json.loads(response.data.decode('utf8'))
    return payload

def get_paginated(http, url):
    payload = get_request(http, url)
    results = payload['results']
    while True:
        if 'next' not in payload['_links']:
            break
        payload = get_request(http, SERVER + "/wiki" + payload['_links']['next'])
        results.extend(payload['results'])
    return results

def get_spaces(http):
    """

    :param http:
    :return: list of space objects
    """
    return get_paginated(http, SERVER + '/wiki/rest/api/space?limit=1000')

def get_pages_for_space(http, space, pages):
    """

    :param http:
    :param space:
    :return: map of space key to API URL
    """
    key = space['key']
    pages_json = get_paginated(http, SERVER + '/wiki/rest/api/space/{0}/content/page?expand=history,history.lastUpdated&limit=1000'.format(key))
    for page in pages_json:
        if page['status'] != 'current':
            print("Page {0} is not current".format(page['id']))
            continue
        last_updated = page['history']['lastUpdated']['when']
        id = page['id']
        # Key is {space_key}-{page_id}-{update_time}
        page_path = "{0}.{1}.{2}".format(space['id'], id, last_updated)
        pages[page_path] = page['_links']['self']
    return pages

def get_page_content(http, page_url):
    return get_request(http, page_url + '?expand=childTypes.all,body.storage')

def lambda_handler(event, context):
    start_time = datetime.now()
    http = urllib3.PoolManager()
    spaces = get_spaces(http=http)
    pages = {}
    for space in spaces:
        pages = get_pages_for_space(http=http, space=space, pages=pages)
    
    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator('list_objects_v2')
    s3_pages = paginator.paginate(Bucket='confluence-data')
    files = []
    for s3_page in s3_pages:
        if 'Contents' in s3_page.keys():
            s3_page_files = [f["Key"] for f in s3_page["Contents"]]
            files.extend(s3_page_files)
    
    files.sort()
    #print(len(files))
    #exit(1)
    
    missing_files = {}
    for page_key, page_url in pages.items():
        if page_key not in files:
            missing_files[page_key] = page_url
    
    inserted_files = []
    stopped_early = False
    for page_key, page_url in missing_files.items():
        page_contents = get_page_content(http=http, page_url=page_url)
        s3_client.put_object(Bucket="confluence-data", Key=page_key, Body=json.dumps(page_contents))
        inserted_files.append(page_key)
        if datetime.now() > (timedelta(minutes=13) + start_time):
            stopped_early = True
            break
    result = { 'result': 'updated missing files',
                            'stopped_early': stopped_early,
                            #'inserted_files': inserted_files,
                            'number_inserted': len(inserted_files),
                            'number_existing_files': len(files),
                            'number_total_files': len(pages.keys()),
                            'number_missing_files': len(missing_files.keys()),
                            'number_remaining_files': len(missing_files.keys()) - len(inserted_files)
        }
    
    print(result)
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
