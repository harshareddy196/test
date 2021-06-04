
import requests
import ntpath
import os
import base64
import shutil
import json
import PyPDF2


from pathlib import Path
from pyzbar.pyzbar import decode
from pdf2image import convert_from_path


import ocr.xml_parser_sdk as xml_parser_sdk
from ace_logger import Logging

logging = Logging()

def path_leaf(path):
                """give any path...platform independent...get the base name"""
                head, tail = ntpath.split(path)
                return tail or ntpath.basename(head)

def isListEmpty(inList):
    if not inList:
        return True
    if isinstance(inList, list):  # Is a list
        return all(map(isListEmpty, inList))
    return False

def get_count(ocr_data):
    # with open('./words_dictionary.json') as f:
    #     words_dict = json.load(f)
    count = 0
    for page in ocr_data:
        for word in page:
            #if word['word'].lower() in words_dict.keys():
            count += 1
    return count

def filter_junkwords(ocr_data):
    with open('./words_dictionary.json') as f:
        words_dict = json.load(f)
    positives_count = 0
    positives = []

    for page in ocr_data:
        for word in page:
            if word['word'].lower() in words_dict.keys() and len(word['word']) > 3 \
                    and word['word'].lower() not in positives:
                positives_count += 1
                positives.append(word['word'].lower())
        break

    return {'count': positives_count, 'valid_words': ' '.join(positives)}

def ocr_pdf_plumber(internal_file_path, tenant_id, parameters):
    """
    Author : Akshat Goyal
    """
    logging.info(' -> Trying PDF plumber...')
    host = os.environ['HOST_IP']
    port = 5002
    route = 'plumb'
    data = {
        'file_name': internal_file_path,
        'tenant_id': tenant_id
    }
    response = requests.post(f'http://{host}:{port}/{route}', json=data)
    pdf_response = response.json()

    if pdf_response['flag']:
        pdf_data = pdf_response['data']
        pdf_working = True
    else:
        pdf_data = None

    # if isListEmpty(pdf_data):
    #         pdf_working = False
    # else:
    #     proper_ocr = filter_junkwords(pdf_data)
    #     junk_words_thres = parameters['junk_words_thres']
    #     if proper_ocr['count'] < junk_words_thres:
    #         pdf_working = False
    #         pdf_data = None

    return pdf_data

def get_ocr_pdf_plumber(tenant_id, case_id, file_name, parameters):
    try:
        internal_file_path = f'{tenant_id}/{case_id}/{file_name}'
        logging.debug(f'internal_file_path - {internal_file_path}')
        # internal_file_path = tenant_id + '/' + file_name if tenant_id else file_name
        pdf_data = ocr_pdf_plumber(internal_file_path, tenant_id, parameters)
    except:
        logging.exception('PDF plumbing failed.')
        pdf_data = None

    return pdf_data


def ocr_sdk_table(file_path):
    """
    Author : Akshat Goyal
    """
    try:
        file_path = str(file_path)
        file_name_ = path_leaf(Path(file_path).absolute())
        files_data = {'file': open(file_path, 'rb')}
        url = os.environ['ABBYY_URL_TABLE']

        logging.debug(url)
        response = requests.post(url, files=files_data)

        logging.debug(type(response))
        sdk_output = response.json()
        logging.debug(type(sdk_output))
        logging.debug(sdk_output.keys())
        # if 'blob' in sdk_output:
        #     pdf = base64.b64decode(sdk_output['blob'])
        #     with open(file_path, 'wb') as f:
        #         f.write(pdf)
        # else:
        #     logging.warning('no blob in sdk_output')


        # shutil.copyfile(file_path, file_path+'_1')
        # os.remove(file_path)
        # os.rename(file_path+'_1', file_path)


        # shutil.copyfile(file_path, 'training_ui/' + file_parent_input + file_name)

        xml_string = sdk_output['xml_string'].replace('\r', '').replace('\n', '').replace('\ufeff', '')
    except:
        xml_string = None
        message = f'Failed to OCR {file_path} using SDK'
        logging.exception(message)

    return xml_string

def rotate_pages(file_path, rotation):
    pdf_reader = PyPDF2.PdfFileReader(file_path)
    pdf_writer = PyPDF2.PdfFileWriter()

    angle_to_rotate = {}

    for page in rotation:
        angle_to_rotate[page['pageNum']] = page['rotate']

    for pagenum in range(pdf_reader.numPages):
        page = pdf_reader.getPage(pagenum)
        if pagenum in angle_to_rotate:
            angle = angle_to_rotate[pagenum]
            page.rotateClockwise(angle)
            pdf_writer.addPage(page)
        else:
            pdf_writer.addPage(page)

    with open(file_path, 'wb') as file:
        pdf_writer.write(file)



def ocr_sdk(file_path, page_rotate=None):
    """
    Author : Akshat Goyal
    """
    try:


        file_name_ = path_leaf(Path(file_path).absolute())
        if page_rotate:
            try:
                rotate_pages(file_path, page_rotate)
            except:
                logging.exception('error in rotation')

        if page_rotate:
            files_data = {'file': open(file_path, 'rb'), 'json': json.dumps(page_rotate)}
        else:
            files_data = {'file': open(file_path, 'rb')}
        url = os.environ['ABBYY_URL']

        logging.debug(url)
        response = requests.post(url, files=files_data)

        logging.debug(type(response))
        sdk_output = response.json()
        logging.debug(type(sdk_output))
        logging.debug(sdk_output.keys())
        if 'blob' in sdk_output:
            pdf = base64.b64decode(sdk_output['blob'])
            with open(file_path, 'wb') as f:
                f.write(pdf)
        else:
            logging.warning('no blob in sdk_output')

        #
        # shutil.copyfile(file_path, file_path+'_1')
        # os.remove(file_path)
        # os.rename(file_path+'_1', file_path)


        # shutil.copyfile(file_path, 'training_ui/' + file_parent_input + file_name)

        xml_string = sdk_output['xml_string'].replace('\r', '').replace('\n', '').replace('\ufeff', '')
    except:
        xml_string = None
        message = f'Failed to OCR {file_path} using SDK'
        logging.exception(message)

    return xml_string


def choose_ocr(abbyy_ocr_data, pdfplumber_ocr_data, parameters):
    """
    Author : Akshat Goyal
    """
    abbyy_word_count = get_count(abbyy_ocr_data)
    if abbyy_word_count == 0:
        xml_string = ''
    pdfplumber_word_count = get_count(pdfplumber_ocr_data)
    logging.debug(f"abby_count: {abbyy_word_count} pdfplumbercount: {pdfplumber_word_count}")
    if abbyy_word_count - pdfplumber_word_count > parameters['battle_resolver_threshold']:
        logging.info(f"abbyy ocr data is being used")
        ocr_data = abbyy_ocr_data
    else:
        logging.info(f"pdf plumber ocr data is being used")
        ocr_data = pdfplumber_ocr_data

    return ocr_data


def append_barcode(ocr_data, file_path):
    """
    Author : Akshat Goyal
    """
    pdf_file_image = convert_from_path(file_path)

    size_ocr = len(ocr_data)
    for idx, image in enumerate(pdf_file_image):
        w, h = image.size
        barcode_datas = decode(image)
        for barcode_data in barcode_datas:
            new_word = {}

            new_word['word'] = barcode_data.data.decode()
            new_word['left'] = barcode_data.rect.left
            new_word['right'] = barcode_data.rect.left + barcode_data.rect.width
            new_word['top'] = barcode_data.rect.top
            new_word['bottom'] = barcode_data.rect.top + barcode_data.rect.height
            new_word['width'] = barcode_data.rect.width
            new_word['height'] = barcode_data.rect.height
            new_word['confidence'] = 100
            new_word = xml_parser_sdk.resize(new_word, 670/w)

            try:
                ocr_data[idx].append(new_word)
            except:
                ocr_data.append([new_word])

    return ocr_data

def ocr_selection(xml_string, pdf_data, file_path, parameters):
    ocr_data = []
    dpi_page = []
    if xml_string is not None or xml_string or not isListEmpty(pdf_data):
        logging.debug('now the battle begins')
        try:
            abbyy_ocr_data, dpi_page = xml_parser_sdk.convert_to_json(xml_string)
        except Exception as e:
            abbyy_ocr_data = []
            dpi_page = []
            logging.exception(f'Error parsing XML. Check trace.')
            pass
        
        ocr_data = choose_ocr(abbyy_ocr_data, pdf_data, parameters)

        # ocr_data = append_barcode(ocr_data, file_path)
        
    else:
        logging.debug(f'No OCR data for {file_path}. Continuing to next file.')

    return ocr_data, dpi_page


def get_ocr(case_id, file_name, tenant_id, parameters, page_rotate=None):
    """
    Author : Akshat Goyal
    """
    # original_file_name = original_file_names[index]
    xml_string = None
    label = ''
    probability = 0.0

    logging.info(f'Processing file {file_name}')


    pdf_data = get_ocr_pdf_plumber(tenant_id, case_id, file_name, parameters)

    file_path = f'/app/input/{tenant_id}/{case_id}/{file_name}'

    # pdf_data = []

    xml_string = ocr_sdk(file_path, page_rotate)

    ocr_data, dpi_page = ocr_selection(xml_string, pdf_data, file_path, parameters)

    return ocr_data, dpi_page

def get_ocr_table(file_path):
    """
    Author : Akshat Goyal
    """
    # case_id = file_name.rsplit('.', 1)[0]
    # original_file_name = original_file_names[index]
    xml_string = None
    label = ''
    probability = 0.0

    logging.info(f'Processing file {file_path}')

    pdf_data = []

    xml_string = ocr_sdk_table(file_path)

    return xml_string