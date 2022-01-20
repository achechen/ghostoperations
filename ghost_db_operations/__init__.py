import logging
import os
import azure.functions as func
import requests
import json
from datetime import datetime
import re
import tempfile

def authenticate(username, password, endpoint):
    data = {
        'username': username,
        'password': password
    }
    url = f'{endpoint}/ghost/api/v3/admin/session/'
    
    try:
        session = requests.Session()
        r = session.post(
            url=url,
            data=data
        )
    except Exception as e:
        return "FAIL", "Could not authenticate with Ghost server", str(e)
    if r.status_code != 201:
        logging.error('Could not authenticate with Ghost server')
        return "FAIL", "Could not authenticate with Ghost server", str(r.json())
    else:
        return "OK", session, ""

def delete_all_posts(session, endpoint):
    url = f'{endpoint}/ghost/api/v3/admin/db/'    
    try:
        r = session.delete(
            url=url
        )
    except Exception as e:
        return "FAIL", "Could not delete posts", str(e)
    if r.status_code != 204:
        logging.error('Could not delete posts')
        logging.error(str(r))
        return "FAIL", "Could not delete posts", str(r.json())
    else:
        return "OK", "successfully deleted all posts", ""

def export_all_posts(session, endpoint):
    url = f'{endpoint}/ghost/api/v3/admin/db/'    
    try:
        r = session.get(
            url=url
        )
    except Exception as e:
        return "FAIL", "Could not export posts", str(e)
    if r.status_code != 200:
        logging.error('Could not export posts')
        logging.error(str(r))
        return "FAIL", "Could not export posts", str(r.json())
    else:
        return "OK", r.json(), "successfully exported all posts"

def import_all_posts(session, endpoint, files):
    url = f'{endpoint}/ghost/api/v3/admin/db/'  
    try:
        r = session.post(
            url=url,
            files=files
        )
    except Exception as e:
        return "FAIL", "Could not import posts", str(e)
    if r.status_code != 200:
        logging.error('Could not import posts')
        logging.error(str(r))
        return "FAIL", "Could not import posts", str(r.json())
    else:
        return "OK", r.json(), "successfully imported all posts"

def write_json(endpoint_name, data):
    temp_dir = tempfile.gettempdir()
    now = datetime.now().utcnow()
    f_name = now.strftime(
        f'{temp_dir}/{endpoint_name}_%Y-%m-%d-%H-%M-%S.json')
    with open(f_name, 'w') as f:
        json.dump(data, f)
    return f_name

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    try:
        body = req.get_json()
    except ValueError:
        logging.error('The request has no body.')
        return func.HttpResponse("The request has no body", status_code=400)
    
    environment = body.get('environment')
    operation = body.get('operation')
    prod_endpoint = os.environ['GHOST_PROD_URL']
    prod_username = os.environ['GHOST_PROD_USERNAME']
    prod_password = os.environ['GHOST_PROD_PASSWORD']
    staging_endpoint = os.environ['GHOST_STAGING_URL']
    staging_username = os.environ['GHOST_STAGING_USERNAME']
    staging_password = os.environ['GHOST_STAGING_PASSWORD']

    if not operation:
        logging.error('Operation was not specified')
        return func.HttpResponse("operation value was not specified", status_code=400)

    # delete
    if operation == 'delete':
        if not environment:
            logging.error('Environment was not specified for delete operation')
            return func.HttpResponse("environment value was not specified for delete operation", status_code=400)
        elif environment != 'prod' and environment != 'staging':
            logging.error('Wrong environment value was specified. Allowed values: prod, staging')
            return func.HttpResponse("Wrong environment value was specified. Allowed values: prod, staging", status_code=400)

        if environment == 'prod':
            endpoint = prod_endpoint
            username = prod_username
            password = prod_password
        else:
            endpoint = staging_endpoint
            username = staging_username
            password = staging_password

        # authenticate
        logging.info(f"Environment is {environment}. Authenticating with {endpoint}")
        status, session, error = authenticate(username, password, endpoint)
        
        if status == 'FAIL':
            logging.error(session)
            logging.error(error)
            return func.HttpResponse(f"{session} {error}", status_code=500)
        else:
            logging.info("Successfully authenticated with ghost server")

        # send delete call
        status, message, error = delete_all_posts(session, endpoint)
        if status == 'FAIL':
            logging.error(message)
            logging.error(error)
            return func.HttpResponse(f"{message} {error}", status_code=500)
        else:
            logging.info("Successfully deleted all posts")
            return func.HttpResponse("Successfully deleted all posts", status_code=201)

    # move
    if operation == 'move':
        # authenticate with staging
        logging.info(f"Authenticating with {staging_endpoint}")
        status, session, error = authenticate(staging_username, staging_password, staging_endpoint)
        
        if status == 'FAIL':
            logging.error(session)
            logging.error(error)
            return func.HttpResponse(f"{session} {error}", status_code=500)
        else:
            logging.info("Successfully authenticated with staging ghost server")

        # export from staging
        logging.info("Exporting all posts from staging")
        status, json_export, message = export_all_posts(session, staging_endpoint)
        if status == 'FAIL':
            logging.error(message)
            return func.HttpResponse(f"Export was not successful. {message}", status_code=500)
        else:
            logging.info(f"Successfully exported all posts.")
        
        # dump into file
        url = re.compile(r"https?://(www\.)?")
        ghost_url_name = url.sub('', staging_endpoint).strip().strip('/')
        ghost_url_name = ghost_url_name.replace('.', '_')
        filename = write_json(ghost_url_name, json_export)
        logging.info(f'Filename: {filename}')

        # authenticate with prod
        logging.info(f"Authenticating with {prod_endpoint}")
        status, session, error = authenticate(prod_username, prod_password, prod_endpoint)
        
        if status == 'FAIL':
            logging.error(session)
            logging.error(error)
            return func.HttpResponse(f"{session} {error}", status_code=500)
        else:
            logging.info("Successfully authenticated with prod ghost server")
      
        # import to prod
        logging.info("Importing all posts from staging into production")
        file = open(filename, 'rb')
        files = {'importfile': file}
        status, response, message = import_all_posts(session, prod_endpoint, files)
        file.close()
        os.remove(filename)
        if status == 'FAIL':
            logging.error(message)
            return func.HttpResponse(f"Import was not successful. {message}", status_code=500)
        else:
            logging.info(f"Successfully imported all posts.")
            return func.HttpResponse("Successfully moved all posts from staging to prod", status_code=200)