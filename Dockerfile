FROM ubuntu

RUN apt-get update
RUN apt-get install -y apt-utils vim curl apache2 apache2-utils
RUN apt-get -y install python3 libapache2-mod-wsgi-py3
RUN apt-get -y install libmariadbclient-dev
RUN apt-get install -y libsm6 libxext6 libxrender-dev
RUN ln /usr/bin/python3 /usr/bin/python
RUN apt-get update && apt-get -y install python3-pip
RUN ln /usr/bin/pip3 /usr/bin/pip
RUN apt-get update && apt-get install -y libzbar0
RUN apt-get install -y libmagickwand-dev
RUN apt-get update && apt-get install -y poppler-utils
# RUN apt-get install libmagickcore5-extra

# Install any needed packages specified in requirements.txt
COPY ./app/requirements.txt /app/
RUN cat /app/requirements.txt | xargs -n 1 pip install ; exit 0
RUN pip install scikit-image

RUN pip install editdistance==0.5.3
COPY ./app/ /app/
COPY ./app/jinja2ext.py /usr/local/lib/python3.6/dist-packages/flask_cache

COPY ./app/db_utils.py /usr/lib/python3.6
COPY ./app/metrics_interface.py /usr/lib/python3.6
COPY ./app/ace_logger.py /usr/lib/python3.6
COPY ./app/producer.py /usr/lib/python3.6
COPY ./app/acepi.py /usr/lib/python3.6
COPY ./app/elasticsearch_utils.py /usr/lib/python3.6
COPY ./app/ace_utils.py /usr/lib/python3.6
COPY ./app/extraction_metrics.py /usr/lib/python3.6

COPY ./app/py_zipkin/zipkin.py /usr/local/lib/python3.6/dist-packages/py_zipkin
COPY ./app/py_zipkin/__init__.py /usr/local/lib/python3.6/dist-packages/py_zipkin
COPY ./app/py_zipkin/logging_helper.py /usr/local/lib/python3.6/dist-packages/py_zipkin

COPY ./app/py_zipkin/encoding/_decoders.py /usr/local/lib/python3.6/dist-packages/py_zipkin
COPY ./app/py_zipkin/encoding/_decoders.py /usr/local/lib/python3.6/dist-packages/py_zipkin
COPY ./app/py_zipkin/encoding/_encoders.py /usr/local/lib/python3.6/dist-packages/py_zipkin
COPY ./app/py_zipkin/encoding/_helpers.py /usr/local/lib/python3.6/dist-packages/py_zipkin

COPY ./app/ocr /usr/lib/python3.6/ocr
COPY ./app/template_detection /usr/lib/python3.6/template_detection

COPY policy.xml /etc/ImageMagick-6
