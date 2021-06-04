import Lib
import logging
import pandas as pd
import json
import datetime
from db_utils import DB


__methods__ = [] # self is a BusinessRules Object
register_method = Lib.register_method(__methods__)

@register_method
def evaluate_static(self, function, parameters):
    if function == 'Assign':
        return self.doAssign(parameters)
    if function == 'AssignQ':
        return self.doAssignQ(parameters)
    if function == 'CompareKeyValue':
        return self.doCompareKeyValue(parameters)
    if function == 'GetLength':
        return self.doGetLength(parameters)
    if function == 'GetRange':
        return self.doGetRange(parameters)
    if function == 'Select':
        return self.doSelect(parameters)
    if function == 'Transform':
        return self.doTransform(parameters)
    if function == 'Count':
        return self.doCount(parameters)
    if function == 'Contains':
        return self.doContains(parameters)

@register_method
def doGetLength(self, parameters):
    """Returns the lenght of the parameter value.
    Args:
        parameters (dict): The parameter from which the needs to be taken. 
    eg:
       'parameters': {'param':{'source':'input', 'value':5},
                      }
    Note:
        1) Recursive evaluations of rules can be made.
    
    """
    try:
        value = len(self.get_param_value(parameters['param']))
    except Exception as e:
        logging.error(e)
        logging.error(f"giving the defalut lenght 0")
        value = 0
    return value

@register_method
def doGetRange(self, parameters):
    """Returns the parameter value within the specific range.
    Args:
        parameters (dict): The source parameter and the range we have to take into. 
    eg:
       'parameters': {'value':{'source':'input', 'value':5},
                        'range':{'start_index': 0, 'end_index': 4}
                      }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Range is the python range kind of (exclusive of the end_index)
    """
    logging.info(f"parameters got are {parameters}")
    value = self.get_param_value(parameters['value'])
    range_ = parameters['range']
    start_index = range_['start_index']
    end_index = range_['end_index']
    try:
        return (str(value)[start_index: end_index])
    except Exception as e:
        logging.error(f"some error in the range function")
        logging.error(e)
    return ""

@register_method
def doSelect(self, parameters):
    """Returns the vlookup value from the tables.
    Args:
        parameters (dict): The table from which we have to select and the where conditions. 
    eg:
        'parameters': {
            'from_table': 'ocr',
            'select_column': 'highlight',
            'lookup_filters':[
                {
                    'column_name': 'Vendor GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
                {
                    'column_name': 'DRL GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
            ]
        }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Its like vlook up in the dataframe and the from_table must have the primary key...case_id.
    """
    logging.info(f"parameters got are {parameters}")
    from_table = parameters['from_table']
    column_name_to_select = parameters['select_column']
    lookup_filters = parameters['lookup_filters']

    # convert the from_table dictionary into pandas dataframe
    try:
        master_data = self.data_source[from_table]
    except Exception as e:
        logging.error(f"data source does not have the table {from_table}")
        logging.error(e)
        master_data = {}

    master_df = pd.DataFrame(master_data) 

    # build the query
    query = ""
    for lookup in lookup_filters:
        lookup_column = lookup['column_name']
        compare_value = self.get_param_value(lookup['compare_with'])
        query += f"{lookup_column} == {compare_value} & "
    query = query.strip(' & ') # the final strip for the extra &
    result_df = master_df.query(query)

    # get the wanted column from the dataframe
    if not result_df.empty:
        try:
            return result_df[column_name_to_select][0] # just return the first value of the matches
        except Exception as e:
            logging.error(f"error in selecting the required data from the result")
            logging.error(e)
            return ""

@register_method
def doTransform(self,parameters) :
    """Returns the evalated data of given equations
    Args:
        parameters (dict): The source parameter which includes values and operators.
    eg:
        'parameters':[
            {'param':{'source':'input', 'value':5}},
            {'operator':'+'},
            {'param':{'source':'input', 'value':7}},
            {'operator':'-'},
            {'param':{'source':'input', 'value':1}},
            {'operator':'*'},
            {'param':{'source':'input', 'value':3}}
        ]
    Note:
        1) Recursive evaluations of rules can be made.
    """
    equation = ''
    logging.info(f"parameters got are {parameters}")
    for dic in parameters :
        for element,number_operator in dic.items() :
            if element == 'param' :
                value = f'{self.get_param_value(number_operator)}'
            elif element == 'operator' :
                value = f' {number_operator} '
        equation = equation + value
    return(eval(equation))

@register_method
def doContains(self,parameters):
    """ Returns true value if the data is present in the data_source
    Args:
        parameters (dict): The source parameter which includes values that should be checked.
    eg:
            cpt_check_rule = {'rule_type': 'static',
                'function': 'Contains',
                'parameters': { 'table_name': 'ocr','column_name': 'cpt_codes',
                                'value':{'source':'input', 'value':92610}
                        }
            }
    """
    logging.info(f"parameters got are {parameters}")
    table_name = parameters['table_name']
    column_name = parameters['column_name']
    value = self.get_param_value(parameters['value'])
    print(value)
    if value in self.data_source[table_name][column_name]:
        return True
    else :
        return False

@register_method
def doCount(self, parameters):
    """Returns the count of records from the tables.
    Args:
        parameters (dict): The table from which we have to select and the where conditions. 
    eg:
        'parameters': {
            'from_table': 'ocr',
            'lookup_filters':[
                {
                    'column_name': 'Vendor GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
                {
                    'column_name': 'DRL GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
            ]
        }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Its like vlook up in the dataframe and the from_table must have the primary key...case_id.
    """
    logging.info(f"parameters got are {parameters}")
    from_table = parameters['from_table']
    lookup_filters = parameters['lookup_filters']

    # convert the from_table dictionary into pandas dataframe
    try:
        master_data = self.data_source[from_table]
    except Exception as e:
        logging.error(f"data source does not have the table {from_table}")
        logging.error(e)
        master_data = {}

    master_df = pd.DataFrame(master_data) 

    # build the query
    query = ""
    for lookup in lookup_filters:
        lookup_column = lookup['column_name']
        compare_value = self.get_param_value(lookup['compare_with'])
        query += f"{lookup_column} == {compare_value} & "
    query = query.strip(' & ') # the final strip for the extra &
    result_df = master_df.query(query)

    # get the wanted column from the dataframe
    if not result_df.empty:
        try:
            return len(result_df) # just return the first value of the matches
        except Exception as e:
            logging.error(f"error in selecting the required data from the result")
            logging.error(e)
            return 0
    else:
        return 0
