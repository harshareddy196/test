import logging
import os

from inspect import getframeinfo, stack

from py_zipkin.storage import get_default_tracer


class Logging(logging.Logger):
    def __init__(self, **kwargs):
        log_levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }

        logging_config = {
            'level': log_levels[os.environ['LOG_LEVEL']],
            'format': os.environ['LOG_FORMAT']
        }
        
        logging.basicConfig(**logging_config)

        logging.getLogger('kafka').disabled = True
        logging.getLogger('kafka.client').disabled = True
        logging.getLogger('kafka.cluster').disabled = True
        logging.getLogger('kafka.conn').disabled = True
        logging.getLogger('kafka.consumer.fetcher').disabled = True
        logging.getLogger('kafka.consumer.group').disabled = True
        logging.getLogger('kafka.consumer.subscription_state').disabled = True
        logging.getLogger('kafka.coordinator').disabled = True
        logging.getLogger('kafka.coordinator.consumer').disabled = True
        logging.getLogger('kafka.metrics.metrics').disabled = True
        logging.getLogger('kafka.producer.kafka').disabled = True
        logging.getLogger('kafka.producer.record_accumulator').disabled = True
        logging.getLogger('kafka.producer.sender').disabled = True
        logging.getLogger('matplotlib').disabled = True
        logging.getLogger('matplotlib.font_manager').disabled = True
        logging.getLogger('requests').disabled = True
        logging.getLogger('urllib3.connectionpool').disabled = True
        logging.getLogger('werkzeug').disabled = True

        self.extra = {
            'tenantID': None,
            'traceID': None
        }

        self.set_ids(**kwargs)

    def set_ids(self):
        tenant_id = None
        trace_id = None
        line_no = None
        file_name = None
        try:
            # logging.debug('Setting tenant ID from zipkin...', extra=self.extra)

            zipkin_attrs = get_default_tracer().get_zipkin_attrs()
            
            if zipkin_attrs:
                tenant_id = zipkin_attrs.tenant_id
                trace_id = zipkin_attrs.trace_id

        except:
            message = 'Failed to get tenant and trace ID from zipkin header. Setting tenant/trace ID to None.'
            print(message)

        try:
            caller = getframeinfo(stack()[2][0])
            file_name = caller.filename
            line_no = caller.lineno
        except:
            message = 'Failed to get caller stack'

        # logging.debug(f'Tenant ID: {tenant_id}', extra=self.extra)
        # logging.debug(f'Trace ID: {trace_id}', extra=self.extra)

        self.tenant_id = tenant_id
        self.trace_id = trace_id
        self.line_no = line_no
        self.file_name = file_name

        self.extra = {
            'tenantID': self.tenant_id,
            'traceID': self.trace_id,
            'fileName': self.file_name,
            'lineNo': self.line_no
        }

    def basicConfig(self, *args, **kwargs):
        logging.basicConfig(**kwargs)

    def debug(self, msg, *args, **kwargs):
        self.set_ids()
        logging.debug(msg, extra=self.extra, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.set_ids()
        logging.info(msg, extra=self.extra, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.set_ids()
        logging.warning(msg, extra=self.extra, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.set_ids()
        logging.error(msg, extra=self.extra, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.set_ids()
        logging.critical(msg, extra=self.extra, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.set_ids()
        logging.exception(msg, extra=self.extra, *args, **kwargs)

    def getLogger(self, name=None):
        return logging.getLogger(name=name)

    def disable(self, level):
        logging.disable(level)
