"""
Author: Ashyam Zubair
Created Date: 14-02-2019
"""
import json
import pandas as pd
import traceback
import sqlalchemy
import os

from MySQLdb._exceptions import OperationalError
from sqlalchemy import create_engine, exc
from time import time

from ace_logger import Logging

logging = Logging()

class DB(object):
    def __init__(self, database, host='127.0.0.1', user='root', password='', port='3306', tenant_id=None):
        """
        Initialization of databse object.

        Args:
            databse (str): The database to connect to.
            host (str): Host IP address. For dockerized app, it is the name of
                the service set in the compose file.
            user (str): Username of MySQL server. (default = 'root')
            password (str): Password of MySQL server. For dockerized app, the
                password is set in the compose file. (default = '')
            port (str): Port number for MySQL. For dockerized app, the port that
                is mapped in the compose file. (default = '3306')
        """

        self.HOST = host
        self.USER = user
        self.PASSWORD = password
        self.PORT = port
        self.DATABASE = f'{tenant_id}_{database}' if tenant_id else database
        
        logging.info(f'Host: {self.HOST}')
        logging.info(f'User: {self.USER}')
        logging.info(f'Password: {self.PASSWORD}')
        logging.info(f'Port: {self.PORT}')
        logging.info(f'Database: {self.DATABASE}')

        self.connect()

    def connect(self, max_retry=5):
        retry = 1

        try:
            start = time()
            logging.debug(f'Making connection to `{self.DATABASE}`...')
            config = f'mysql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DATABASE}?charset=utf8'
            self.db_ = create_engine(config, connect_args={'connect_timeout': 2}, pool_recycle=300)
            logging.info(f'Engine created for `{self.DATABASE}`')
            while retry <= max_retry:
                try:
                    self.engine = self.db_.connect()
                    logging.info(f'Connection established succesfully to `{self.DATABASE}`! ({round(time() - start, 2)} secs to connect)')
                    break
                except Exception as e:
                    logging.warning(f'Connection failed. Retrying... ({retry}) [{e}]')
                    retry += 1
                    self.db_.dispose()
        except:
            raise Exception('Something went wrong while connecting. Check trace.')

    def execute(self, query, attempt=0, **kwargs):
        """
        Executes an SQL query.

        Args:
            query (str): The query that needs to be executed.
            params (list/tuple/dict): List of parameters to pass to in the query.

        Returns:
            (DataFrame) A pandas dataframe containing the data from the executed
            query. (None if an error occurs)
        """
        data = None

        params = kwargs['params'] if 'params' in kwargs else None
        logging.debug(f'Query: {query}')
        logging.debug(f'Params: {params}')
        try:
            data = pd.read_sql(query, self.engine, index_col='id', **kwargs)
        except exc.ResourceClosedError:
            logging.warning('Query does not have any value to return.')
            return True
        except exc.IntegrityError as e:
            logging.warning(f'Integrity Error - {e}')
            return None
        except (exc.StatementError, OperationalError) as e:
            logging.warning(f'Creating new connection. Engine/Connection is probably None. [{e}]')
            attempt += 1
            if attempt <= 5:
                self.connect()
                logging.debug(f'Attempt #{attempt}')
                return self.execute(query, attempt=attempt, **kwargs)
            else:
                logging.debug(f'Maximum attempts reached. ({5})')
                return False
        except:
            logging.exception('Something went wrong executing query. Check trace.')
            return False

        return data.where((pd.notnull(data)), None)

    def execute_(self, query, attempt= 0, **kwargs):
        """
        Executes an SQL query.

        Args:
            query (str): The query that needs to be executed.
            params (list/tuple/dict): List of parameters to pass to in the query.

        Returns:
            (DataFrame) A pandas dataframe containing the data from the executed
            query. (None if an error occurs)
        """
        data = None

        try:
            data = pd.read_sql(query, self.engine, **kwargs)
        except exc.ResourceClosedError:
            return True
        except exc.IntegrityError as e:
            logging.warning(f'Integrity Error - {e}')
            return None
        except (exc.StatementError, OperationalError) as e:
            logging.warning(f'Creating new connection. Engine/Connection is probably None. [{e}]')
            attempt += 1
            if attempt <= 5:
                self.connect()
                logging.debug(f'Attempt #{attempt}')
                return self.execute_(query, attempt=attempt, **kwargs)
            else:
                logging.debug(f'Maximum attempts reached. ({5})')
                return False
        except:
            logging.exception(f'Something went wrong while connecting. Check trace.')
            params = kwargs['params'] if 'params' in kwargs else None
            return False

        return data.replace({pd.np.nan: None})


    def insert(self, data, table, **kwargs):
        """
        Write records stored in a DataFrame to a SQL database.

        Args:
            data (DataFrame): The DataFrame that needs to be write to SQL database.
            table (str): The table in which the rcords should be written to.
            kwargs: Keyword arguments for pandas to_sql function.
                See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_sql.html
                to know the arguments that can be passed.

        Returns:
            (bool) True is succesfully inserted, else false.
        """
        logging.info(f'Inserting into `{table}`')

        try:
            data.to_sql(table, self.engine, **kwargs)
            try:
                self.execute(f'ALTER TABLE `{table}` ADD PRIMARY KEY (`id`);')
            except:
                pass
            return True
        except:
            logging.exception('Something went wrong inserting. Check trace.')
            return False

    def insert_dict(self, data, table):
        """
        Insert dictionary into a SQL database table.

        Args:
            data (DataFrame): The DataFrame that needs to be write to SQL database.
            table (str): The table in which the rcords should be written to.

        Returns:
            (bool) True is succesfully inserted, else false.
        """
        logging.info(f'Inserting dictionary data into `{table}`...')
        logging.debug(f'Data:\n{data}')

        try:
            column_names = []
            params = []

            for column_name, value in data.items():
                column_names.append(f'`{column_name}`')
                params.append(value)
                logging.info(f"column_nameeeeeeeeeeeeeeeeeeee - {column_name}")
                logging.info(f"Valueeeeeeeeeee - {value}")

            logging.info(f"Length of paraaaaaaaaaaams - {len(params)}")
            logging.debug(f'Column names: {column_names}')
            logging.debug(f'Params: {params}')

            columns_string = ', '.join(column_names)
            param_placeholders = ', '.join(['%s'] * len(column_names))

            query = f'INSERT INTO {table} ({columns_string}) VALUES ({param_placeholders})'

            return self.execute(query, params=params)
        except:
            logging.exception('Error inserting data.')
            return False

    def update(self, table, update=None, where=None, force_update=False):
        logging.info(f'Updating table: `{table}`')
        logging.info(f'Update data: `{update}`')
        logging.info(f'Where clause data: `{where}`')
        logging.info(f'Force update flag: `{force_update}`')

        try:
            set_clause = []
            set_value_list = []
            where_clause = []
            where_value_list = []

            if where is not None and where:
                for set_column, set_value in update.items():
                    set_clause.append(f'`{set_column}`=%s')
                    set_value_list.append(set_value)
                set_clause_string = ', '.join(set_clause)
            else:
                logging.error(f'Update dictionary is None/empty. Must have some update clause.')
                return False

            if where is not None and where:
                for where_column, where_value in where.items():
                    where_clause.append(f'{where_column}=%s')
                    where_value_list.append(where_value)
                where_clause_string = ' AND '.join(where_clause)
                query = f'UPDATE `{table}` SET {set_clause_string} WHERE {where_clause_string}'
            else:
                if force_update:
                    query = f'UPDATE `{table}` SET {set_clause_string}'
                else:
                    message = 'Where dictionary is None/empty. If you want to force update every row, pass force_update as True.'
                    logging.error(message)
                    return False

            params = set_value_list + where_value_list
            self.execute(query, params=params)
            return True
        except:
            logging.exception('Something went wrong updating. Check trace.')
            return False

    def get_column_names(self, table):
        """
        Get all column names from an SQL table.

        Args:
            table (str): Name of the table from which column names should be extracted.
            database (str): Name of the database in which the table lies. Leave
                it none if you want use database during object creation.

        Returns:
            (list) List of headers. (None if an error occurs)
        """
        try:
            logging.info(f'Getting column names of table `{table}`')
            return list(self.execute(f'SELECT * FROM `{table}`'))
        except:
            logging.exception('Something went wrong getting column names. Check trace.')
            return

    def execute_default_index(self, query, **kwargs):
        """
        Executes an SQL query.

        Args:
            query (str): The query that needs to be executed.
            database (str): Name of the database to execute the query in. Leave
                it none if you want use database during object creation.
            params (list/tuple/dict): List of parameters to pass to in the query.

        Returns:
            (DataFrame) A pandas dataframe containing the data from the executed
            query. (None if an error occurs)
        """
        data = None

        try:
            data = pd.read_sql(query, self.engine, **kwargs)
        except exc.ResourceClosedError:
            return True
        except:
            logging.exception(f'Something went wrong while executing query. Check trace.')
            params = kwargs['params'] if 'params' in kwargs else None
            return False

        return data.where((pd.notnull(data)), None)


    def get_all(self, table, discard=None, condition=None):
        """
        Get all data from an SQL table.

        Args:
            table (str): Name of the table from which data should be extracted.
            discard (list): columns to be excluded while selecting all
        Returns:
            (DataFrame) A pandas dataframe containing the data. (None if an error
            occurs)
        """
        logging.info(f'Getting all data from `{table}`')
        
        if discard is not None:
            logging.info(f'Discarding columns `{discard}`')
            columns = list(self.execute_default_index(f'SHOW COLUMNS FROM `{table}`',).Field)
            columns = [col for col in columns if col not in discard]
            columns_str = json.dumps(columns).replace("'",'`').replace('"','`')[1:-1]
            return self.execute(f'SELECT {columns_str} FROM `{table}`')

        if isinstance(condition, dict):
            where_clause = []
            where_value_list = []
            for where_column, where_value in condition.items():
                where_clause.append(f'`{where_column}`=%s')
                where_value_list.append(where_value)
            where_clause_string = ' AND '.join(where_clause)
            return self.execute(f'SELECT * FROM `{table}` WHERE {where_clause_string}', params=where_value_list)

        return self.execute(f'SELECT * FROM `{table}`')

    def get_latest(self, data, group_by_col, sort_col):
        """
        Group data by a column containing repeated values and get latest from it by
        taking the latest value based on another column.

        Example:
        Get the latest products
            id     product   date
            220    6647     2014-09-01
            220    6647     2014-10-16
            826    3380     2014-11-11
            826    3380     2015-05-19
            901    4555     2014-09-01
            901    4555     2014-11-01

        The function will return
            id     product   date
            220    6647     2014-10-16
            826    3380     2015-05-19
            901    4555     2014-11-01

        Args:
            data (DataFrame): Pandas DataFrame to query on.
            group_by_col (str): Column containing repeated values.
            sort_col (str): Column to identify the latest record.

        Returns:
            (DataFrame) Contains the latest records. (None if an error occurs)
        """
        try:
            logging.info('Grouping data...')
            logging.info(f'Data: {data}')
            logging.info(f'Group by column: {group_by_col}')
            logging.info(f'Sort column: {sort_col}')
            return data.sort_values(sort_col).groupby(group_by_col).tail(1)
        except KeyError as e:
            logging.errot(f'Column `{e.args[0]}` does not exist.')
            return None
        except:
            logging.exception('Something went wrong while grouping data.')
            return None
