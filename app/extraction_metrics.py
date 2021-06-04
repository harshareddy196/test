#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:00:55 2019

@author: amith
"""

import os
import sqlalchemy
import json
import traceback

from difflib import SequenceMatcher

from db_utils import DB
from ace_logger import Logging


logging = Logging()

# field_list = ['PO Number','Invoice Number','Invoice Date','Invoice Total','Invoice Base Amount','DRL GSTIN','Vendor GSTIN']
db_config = {
    'host': os.environ['HOST_IP'],
    'port': os.environ['LOCAL_DB_PORT'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
}




def get_mandatory_field(tenant_id):

    db = DB('queues', tenant_id=tenant_id, **db_config)

    tab_df = db.get_all('tab_definition')
    ocr_tab_id = tab_df.loc[tab_df['source'] == 'ocr'].index.values.tolist()

    tab_list = ', '.join([str(i) for i in ocr_tab_id])
    logging.debug(f'Tab List: {tab_list}')

    queue_query = f'select id from queue_definition where unique_name = "template_exceptions"'
    queue_id_df = db.execute(queue_query)
    queue_id_df['id'] = queue_id_df.index

    queue_id = list(queue_id_df['id'])[0]

    query = f'SELECT * FROM `field_definition` WHERE `tab_id`in ({tab_list}) and FIND_IN_SET({queue_id}, queue_field_mapping) > 0'

    ocr_fields_df = db.execute(query)
    mandatory_fields = list(ocr_fields_df['unique_name'])

    return mandatory_fields

def get_data(tenant_id):
    
    query1 = "SELECT * FROM ocr"
    query2 = "SELECT `id`,`case_id`, `fields_changed` FROM field_accuracy"
    
    # config_extraction = 'mysql://root:@192.168.0.108:3306/extraction?charset=utf8'
    # config_queues = 'mysql://root:@192.168.0.108:3306/queues?charset=utf8'
    #
    # engine_extraction = sqlalchemy.create_engine(config_extraction)
    # engine_queues = sqlalchemy.create_engine(config_queues)
    #
    #

    extraction_db = DB('extraction', tenant_id=tenant_id, **db_config)
    queue_db = DB('queues', tenant_id=tenant_id, **db_config)

    rp_1 = extraction_db.execute(query1).to_dict(orient='records')
    rp_2 = queue_db.execute(query2).to_dict(orient='records')

    ocr_data = case_id_key(rp_to_dict(rp_1))
    accuracy_data = rp_to_dict(rp_2)
    
    return ocr_data, accuracy_data

def rp_to_dict(result_proxy):
    d, a = {}, []
    for row in result_proxy:
        for column, value in row.items():
            d = {**d, **{column : value}}
        a.append(d)
    return a

def case_id_key(list_of_dict):
    a = {}
    for row in list_of_dict:
        a = {**a, **{row['case_id'] : row}}
    return a 

def generate_extraction_metrics(tenant_id=None):
    ocr_data, accuracy_data = get_data(tenant_id)
    metrics = []

    mandatory_fields = get_mandatory_field(tenant_id)

    for row in accuracy_data:
        case_id = row['case_id']
        if case_id in ocr_data:
            ocr_row = ocr_data[case_id]
            fields_changed = json.loads(row['fields_changed']) if row['fields_changed'] else {}
            field_temp = {}
            for field in mandatory_fields:
            # for field, value in ocr_row.items():
                if field not in ocr_row:
                    continue
                value = ocr_row[field]

                field_ = '_'.join(field.lower().split()) + '_ocr' 
                if field_ in fields_changed:
                    temp = {
                            field: {
                                    "predicted_value" : fields_changed[field_]['actual_value'],
                                    "actual_value" : fields_changed[field_]['changed_value'],
                                    "value_predicted_correctly": False,
                                    "predicted_keyword": '',
                                    "actual_keyword": '',
                                    "key_predicted_correctly": ""

                                    }
                            }
                    field_temp = {**field_temp, **temp}
                else:
                    temp = {
                            field: {
                                    "predicted_value" : value,
                                    "actual_value" : value,
                                    "value_predicted_correctly": True,
                                    "predicted_keyword": '',
                                    "actual_keyword": '',
                                    "key_predicted_correctly": ""
                                    }
                            }
                    field_temp.update(temp)
            metrics.append([case_id, field_temp])
    return metrics
                    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
        