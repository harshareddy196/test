import os

from ace_logger import Logging
from db_utils import DB

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def get_container_file_category(tenant_id, container):
    logging.info(f'Getting file category name for `{container}` container.')

    db_config['tenant_id'] = tenant_id
    system_db = DB('system', **db_config)
    container_info = system_db.get_all('containers', condition={'container_name': container})
    logging.debug(f'Container Info: {container_info}')

    if container_info.empty:
        logging.debug(f'Container not configured in the system DB. Using `Uncategorized` as category.')
        return 1

    category = list(container_info['file_category'])[0]
    logging.info(f'File category name for `{container}` is `{category}`')

    return category

def get_queue_file_category(tenant_id, queue_id):
    logging.info(f'Getting file category name for queue ID `{queue_id}`')

    db_config['tenant_id'] = tenant_id
    queue_db = DB('queues', **db_config)
    queue_def = queue_db.get_all('queue_definition', condition={'id': queue_id})
    logging.debug(f'Queue Info: {queue_def}')

    if queue_def.empty:
        logging.debug(f'Container not configured in the system DB. Using `Uncategorized` as category.')
        return 1

    category = list(queue_def['file_category'])[0]
    logging.info(f'File category name for `{queue_def}` is `{category}`')

    return category

def update_file_manager(case_id, file_name, tenant_id, folder_id=None, container=None, file_manager_db=None, file_manager=None, update=True):
    if file_manager_db is None:
        db_config['tenant_id'] = tenant_id
        file_manager_db = DB('file_manager', **db_config)
    
    if file_manager is None:
        file_manager = file_manager_db.get_all('file_manager', condition={'case_id': case_id})

    if folder_id is None and container is None:
        logging.error('Atleast folder ID or container name should be given.')
        return
    
    if folder_id is None and container is not None:
        folder_id = get_container_file_category(tenant_id, container)

    # Add file to file manager table with corresponding folder_id
    # Check if file exists. Update if exists else create.
    if file_manager.loc[file_manager['file_name'] == file_name].empty:
        logging.debug(f'Inserting file into `file_manager`')
        insert_data = {'case_id': case_id, 'file_name': file_name, 'folder_id': folder_id}
        file_manager_db.insert_dict(insert_data, 'file_manager')
    else:
        if update:
            logging.debug(f'Updating folder ID in `file_manager`')
            update_clause = {'folder_id': folder_id}
            where_clause = {'file_name': file_name, 'case_id': case_id}
            file_manager_db.update('file_manager', update=update_clause, where=where_clause)
        else:
            logging.debug(f'Update flag is false. Not updating.')