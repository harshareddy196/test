from ace_logger import Logging
from influxdb import InfluxDBClient

logging = Logging()

def store_data(metrics_data, db_name, table_name):
    json_body = []
    # import pdb
    # pdb.set_trace()
    try:
        for measurement in metrics_data:
            tags = {}
            fields = {}

            low_key = measurement.get("low_card", {})
            high_key = measurement.get("high_card", {})
            values = measurement.get("value", {})

            for tag_name, value in low_key.items():
                tags.update({tag_name: value})

            for tag_name, value in high_key.items():
                tags.update({tag_name: value})

            for field_name, value in values.items():
                fields.update({field_name: value})

            json_body.append({
                "measurement": table_name,
                "tags": tags,
                "fields": fields
            })
            logging.debug(f"data body - {json_body}")
            client = InfluxDBClient("influxdb", 8086, "admin", "", db_name)
            client.write_points(json_body)
    except:
        logging.exception("Metrics data is empty")