import numpy as np
import copy
import pymysql
import re
import json
import os
import editdistance
from db_utils import DB
from ace_logger import Logging
from template_detection.opencV_and import match_box

from sklearn.feature_extraction import text
from fuzzywuzzy import fuzz

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}


# def get_parameters():
#     with open('configs/template_detection_params.json') as f:
#         return json.loads(f.read())


# parameters = get_parameters()
# ANALYST_DATABASE = parameters['database_name']
# machines = parameters['platform']


def load_trained_info(tenant_id):
    query = "SELECT * from trained_info"
    template_db = DB('template_db', tenant_id=tenant_id, **db_config)
    trained_info_data = template_db.execute(query).to_dict(orient='records')

    trained_info = {}
    for i in trained_info_data:
        trained_info[i['template_name']] = {
            'header_ocr': i['header_ocr'].encode('utf-8').decode(),
            'footer_ocr': i['footer_ocr'].encode('utf-8').decode(),
            'address_ocr': i['address_ocr'],
            'unique_fields': i['unique_fields'].encode('utf-8').decode(),
            'condition': i['operator'],
            'ad_trained_info': i['ad_train_info']
        }
    return trained_info


def sort_ocr(data):
    data = sorted(data, key=lambda i: i['top'])
    for i in range(len(data) - 1):
        data[i]['word'] = data[i]['word'].strip()
        data[i]['word'] = data[i]['word'].encode('utf-8').decode()
        data[i + 1]['word'] = data[i + 1]['word'].strip()
        if abs(data[i]['top'] - data[i + 1]['top']) < 6:
            data[i + 1]['top'] = data[i]['top']
    data = sorted(data, key=lambda i: (i['top'], i['left']))
    return data


def get_trained_templates(tenant_id, lower=False):
    query = "SELECT `template_name` FROM trained_info"
    template_db = DB('template_db', tenant_id=tenant_id, **db_config)

    query_result = template_db.execute(query)

    if query_result:
        if lower:
            return [row[0].lower() for row in query_result]
        return [row[0] for row in query_result]
    else:
        return []


def remove_all_except_al_num(text):
    return re.sub('[,.!@#$%^&*()\_\-=`~\'";:<>/?]', '', text.lower())


def string_match(s1, s2):
    if len(s1) <= len(s2):
        shorter = s1
        longer = s2
    else:
        shorter = s2
        longer = s1

    len_short = len(shorter)
    len_long = len(longer)

    if len_short == 0:
        return 0
    highest_ratio = 0
    for idx in range(0, len_long - len_short+1):
        sub_str = longer[idx:idx+len_short]

        distance = editdistance.eval(shorter, sub_str)
        ratio = (len_short - distance)/len_short
        # ratio = fuzz.partial_ratio(shorter, sub_str)

        if ratio > highest_ratio:
            highest_ratio = ratio

    return highest_ratio*100



class TemplateDetector():
    def __init__(self, tenant_id, threshold=0.7, address_threshold=0.7):
        self.max_match_score = -1
        self.threshold = threshold
        self.address_threshold = address_threshold
        self.trained_info = load_trained_info(tenant_id)

    def ngrams(self, input, n):
        '''
        Author : Akshat Goyal

        :param input: str : string for which ngram is to be calculated
        :param n: int : the no of consideredecutive words are to considered
        :return: a map of ngram as key with no of corresponding ngram as value
        '''
        input = input.split(' ')
        output = {}
        for i in range(len(input) - n + 1):
            g = (' '.join(input[i:i + n])).strip()
            output.setdefault(g, 0)
            output[g] += 1
        return output

    def ngram_2(self, sample):
        sample_ng = []
        if len(sample) > 2:
            for i, j in enumerate(sample):
                try:
                    temp = j + sample[i + 1]
                    sample_ng.append(temp)
                except:
                    break

            return sample_ng
        else:
            return sample

    def preprocess(self, input_fields, input_matrix, actual_fields, actual_matrix):
        # Convert from nparray to normal list
        if type(input_matrix) is np.ndarray:
            input_matrix = input_matrix.tolist()

        input_set = set(input_fields)
        actual_set = set(actual_fields)

        intersection = list(input_set & actual_set)

        input_fields_ = []
        input_matrix_ = []
        actual_fields_ = []
        actual_matrix_ = []

        c = 0

        # actual_matrix_copy = copy.deepcopy(actual_matrix)
        # Actual Fields
        actual_matrix_copy = copy.deepcopy(actual_matrix)
        for field in actual_fields:
            if field in intersection:
                actual_fields_.append(field)

            else:
                index = actual_fields.index(field) - c
                actual_matrix_copy.pop(index)
                for directions in actual_matrix_copy:
                    directions.pop(index)
                c += 1

        # Input Fields
        input_matrix_copy = copy.deepcopy(input_matrix)
        for field in input_fields:
            if field in intersection:
                input_fields_.append(field)
            else:
                index = input_fields.index(field) - c
                input_matrix_copy.pop(index)
                for directions in input_matrix_copy:
                    directions.pop(index)
                c += 1

        return input_fields_, input_matrix_copy, actual_fields_, actual_matrix_copy

    def get_matching_missing_indices(self, input_fields, actual_fields):
        """
        Return the matching and missing indices from two lists.
        Note.
            See the format of the output..it's in the input fields
            Some redundant steps might be there..Recheck.
        """
        matching_indices_input = []
        matching_indices_actual = []
        missing_indices_input = []
        missing_indices_actual = []

        for i in range(len(input_fields)):
            if input_fields[i] in actual_fields:
                matching_indices_input.append(i)
                matching_indices_actual.append(actual_fields.index(input_fields[i]))
            else:
                missing_indices_input.append(i)
        for i in range(len(actual_fields)):
            if i not in matching_indices_actual:
                missing_indices_actual.append(i)

        return (matching_indices_input, matching_indices_actual, missing_indices_input, missing_indices_actual)

    def get_proccessed_matrices(self, input_matrix, actual_matrix, input_fields, actual_fields):
        """
        Return the processed matrices..after removing.
        Note.
            See the format of the output..it's in the input fields
            Some redundant steps might be there..Recheck.
        """
        input_matrix_rows = []
        actual_matrix_rows = []
        matching_indices_input, matching_indices_actual, missing_indices_input, missing_indices_actual = self.get_matching_missing_indices(
            input_fields, actual_fields)
        for a, b in zip(matching_indices_input, matching_indices_actual):
            input_matrix_rows.append(input_matrix[a])
            actual_matrix_rows.append(actual_matrix[b])

        return (self.get_final_matrix(input_matrix_rows, missing_indices_input),
                self.get_final_matrix(actual_matrix_rows, missing_indices_actual))

    def get_final_matrix(self, matrix_rows, missing_indices):
        final_matrix = []
        for row in matrix_rows[:]:
            a = []
            for i in range(len(row)):
                if i not in missing_indices:
                    a.append(row[i])
            final_matrix.append(a)
        return final_matrix

    def predict_with_vname(self, ocr_data, tenant_id):
        trained_templates = get_trained_templates(lower=True, tenant_id=tenant_id)

        # If nothing is trained then return no template
        if not trained_templates:
            return ''

        # Initialize frequency list
        frequency = [0] * len(trained_templates)
        for word in ocr_data[0]:
            # If any OCR word matches the trained vendor name, then increase count
            if word['word'].lower() in trained_templates:
                index = trained_templates.index(word['word'].lower())
                frequency[index] += 1

        # Which word had the highest frequency
        highest_freq = max(frequency)

        # If the highest frequency is zero that means
        # it didnt find any word that matches the vendor name
        if highest_freq > 0:
            highest_freq_index = frequency.index(highest_freq)
            return trained_templates[highest_freq_index]

        return ''

    def predict_with_ngram(self, ocr_data, filter=None, n=2):
        '''
        Author : Akshat Goyal

        :param ocr_data: the ocr data of the file to which template matching is to be applied
        :param filter:
        :param n : the no of words to considered for ngram
        :return:
        '''
        detected_template = ''
        sorted_ocr_data = []
        # for data in ocr_data:
        sorted_ocr_data.append(sorted(ocr_data[0], key=lambda k: k['top']))

        # by_3_top = int(len(sorted_ocr_data[0]) / 3)
        # ocr_data_top = sorted_ocr_data[0][:by_3_top]

        # stopwords = list(text.ENGLISH_STOP_WORDS)

        # self.trained_info = {k.lower(): v for k, v in self.trained_info.items()}

        if filter:
            trained_templates = dict(zip(filter, [self.trained_info[k] for k in filter]))
        else:
            trained_templates = self.trained_info

        head_foot_match = False
        for template, template_data in trained_templates.items():
            first_text = []
            template_header_ocr = template_data['header_ocr'].lower()
            template_footer_ocr = template_data['footer_ocr'].lower()
            template_address_ocr = template_data['address_ocr'].lower()

            header_match_list = template_header_ocr.lower().split()
            footer_match_list = template_footer_ocr.lower().split()

            # for f_W in filter_words:

            try:
                footer_ngram = self.ngrams(template_footer_ocr, n)
            except:
                footer_ngram = {}

            try:
                header_ngram = self.ngrams(template_header_ocr, n)
            except:
                header_ngram = {}

            first_page = sorted_ocr_data[0]
            last_page = sorted_ocr_data[-1]

            # print(first_page)
            for page in sorted_ocr_data:
                for i in page:
                    first_text.append(re.sub('[^A-Za-z0-9 ]', '', i['word'].lower()))
                    # first_text.append(i['word'].lower())

            try:
                first_text_ngram = self.ngrams(' '.join(first_text), n)
            except:
                first_text_ngram = {}
                # print(' '.join(first_text))

            full_footer_count = 0
            # for i in footer_ngram.keys():
            #     full_footer_count += footer_ngram[i]

            max_footer_count = 0
            # for page in sorted_ocr_data:
            #     last_text = []
            #     footer_count = 0
            #     for i in page:
            #         last_text.append(re.sub('[^A-Za-z0-9 ]', '', i['word'].lower()))

            #     try:
            #         last_text_ngram = self.ngrams(' '.join(last_text), n)
            #     except:
            #         last_text_ngram = {}
            footer_count = 0
            for i in footer_ngram.keys():
                full_footer_count += footer_ngram[i]
                check = re.sub('[^A-Za-z0-9 ]', '', i.lower())
                if check in first_text_ngram:
                    footer_count += footer_ngram[i]

            if footer_count > max_footer_count:
                max_footer_count = footer_count

            footer_count = max_footer_count

            header_count = 0
            max_address_count = 0

            full_header_count = 0
            for i in header_ngram.keys():
                full_header_count += header_ngram[i]
                if i in first_text_ngram:
                    header_count += header_ngram[i]

            # print('first_text_ngram - ', first_text_ngram)
            # print('last_text_ngram - ', last_text_ngram)
            # print(list(header_ngram.keys()))
            # print(template_address_ocr, first_text)

            divisor = 0
            if len(header_ngram) < 1:
                match_top = 0
            else:
                match_top = header_count / full_header_count
                divisor += 1

            if len(footer_ngram) < 1:
                match_bottom = 0
            else:
                match_bottom = footer_count / full_footer_count
                divisor += 1
            if divisor == 0:
                match_score = 0
            else:
                match_score = (match_top + match_bottom) / divisor
            max_address_list = ''
            # print(template_address_ocr)
            if match_score >= self.threshold:
                head_foot_match = True
                full_address_count_final = 0

                if type(template_address_ocr) is str:
                    template_address_ocr = [template_address_ocr]

                for template_address in template_address_ocr:
                    address_count = 0
                    address_match_list = template_address.lower().split(' ')

                    try:
                        address_ngram = self.ngrams(template_address.lower(), n)
                    except:
                        address_ngram = {}

                    full_address_count = 0
                    for i in address_ngram.keys():
                        full_address_count += address_ngram[i]
                        if i in first_text_ngram:
                            address_count += address_ngram[i]
                    if ((full_address_count_final == 0 or full_address_count == 0) or (
                            (float(address_count) / float(full_address_count)) > (
                            float(max_address_count) / float(full_address_count_final)))):
                        max_address_list = address_match_list
                        max_address_count = address_count
                        full_address_count_final = full_address_count

                if full_address_count_final != 0:
                    match_address = max_address_count / full_address_count_final
                    divisor += 1
                else:
                    match_address = 0

                if match_address >= self.max_match_score:
                    self.max_match_score = match_address
                    detected_template = template
                    # print("Detected template is : ", detected_template)

        # print('Score:', self.max_match_score)

        if head_foot_match:
            # if self.max_match_score >= self.address_threshold:
            return detected_template
            # else:
            #     return detected_template + ".doubtful"
        else:
            return ''

    def predict_with_wv(self, ocr_data, filter=None):
        detected_template = ''
        sorted_ocr_data = []
        for data in ocr_data:
            sorted_ocr_data.append(sorted(data, key=lambda k: k['top']))

        # by_3_top = int(len(sorted_ocr_data[0])/3)
        # ocr_data_top = sorted_ocr_data[0][:by_3_top]

        # stopwords = list(text.ENGLISH_STOP_WORDS)

        # self.trained_info = {k.lower(): v for k, v in self.trained_info.items()}

        if filter:
            trained_templates = dict(zip(filter, [self.trained_info[k] for k in filter]))
        else:
            trained_templates = self.trained_info

        head_foot_match = False
        for template, template_data in trained_templates.items():
            first_text = []

            if type(template_data['address_ocr']) is str:
                template_data['address_ocr'] = json.dumps([template_data['address_ocr']])

            template_header_ocr = template_data['header_ocr']
            template_footer_ocr = template_data['footer_ocr']
            template_address_ocr = json.loads(template_data['address_ocr'])
            header_match_list_ = template_header_ocr.lower().split()
            footer_match_list_ = template_footer_ocr.lower().split()
            #            address_match_list = template_address_ocr.lower().split()

            header_match_list = []
            for word in header_match_list_:
                header_match_list.append(''.join(e for e in word if e.isalnum()))

            header_match_list = self.ngram_2(header_match_list)

            footer_match_list = []
            for word in footer_match_list_:
                footer_match_list.append(''.join(e for e in word if e.isalnum()))

            footer_match_list = self.ngram_2(footer_match_list)

            # first_page = sorted_ocr_data[0]
            # last_page = sorted_ocr_data[-1]

            # print(first_page)
            # for i in first_page:
            #     first_text.append(re.sub('[^A-Za-z0-9\.-/_ ]', '', i['word'].lower().replace('.','')))

            # print(' '.join(first_text))

            # max_footer_count = 0
            for page in sorted_ocr_data:
                # last_text = []
                # footer_count = 0
                for i in page:
                    # first_text.append(re.sub('[^A-Za-z0-9 ]', '', i['word'].lower()))
                    first_text.append(i['word'].lower())

            max_footer_count = 0
            # for page in sorted_ocr_data:
            #     last_text = []
            #     footer_count = 0
            #     for i in page:
            #         last_text.append(re.sub('[^A-Za-z0-9\.-/_ ]', '', i['word'].lower()).replace('.',''))

            first_text = ''.join(first_text)
            first_text = remove_all_except_al_num(first_text)
            # first_text = ''.join(e for e in first_text if e.isalnum()).lower()

            footer_count = 0
            for i in footer_match_list:
                if i in first_text:
                    footer_count += 1

            if footer_count > max_footer_count:
                max_footer_count = footer_count

            footer_count = max_footer_count

            header_count = 0
            max_address_count = 0

            for i in header_match_list:
                if i in first_text:
                    header_count += 1

            # print(template_address_ocr, first_text)

            divisor = 0
            if not header_match_list[0]:
                match_top = 0
            else:
                match_top = header_count / len(header_match_list)
                divisor += 1

            if not footer_match_list[0]:
                match_bottom = 0
            else:
                match_bottom = footer_count / len(footer_match_list)
                divisor += 1

            if divisor != 0:
                match_score = (match_top + match_bottom) / divisor
            else:
                match_score = 0

            max_address_list = ''
            # print(template_address_ocr)
            if match_score >= self.threshold:
                head_foot_match = True

                for template_address in template_address_ocr:
                    address_count = 0
                    address_match_list_ = template_address.lower().split()
                    address_match_list = []
                    for word in address_match_list_:
                        address_match_list.append(''.join(e for e in word if e.isalnum()))

                    address_match_list = self.ngram_2(address_match_list)
                    for i in address_match_list:
                        if i in first_text:
                            address_count += 1
                    if max_address_count < address_count:
                        max_address_list = address_match_list
                        max_address_count = address_count

                if (template_address_ocr) and (template_address_ocr[0]) and (
                        (not template_address_ocr[0][0]) or (not len(max_address_list))):
                    match_address = 0
                else:
                    match_address = max_address_count / len(max_address_list)
                    divisor += 1

                if match_address >= self.max_match_score:
                    self.max_match_score = match_address
                    detected_template = template
                    # print("Detected template is : ", detected_template)

                # print(max_match_score, self.threshold)
                self.max_match_score = (2 * match_score + match_address) / 3
            else:
                self.max_match_score = match_score
            # print('Template', template, 'SCORE', self.max_match_score)

        if head_foot_match:
            if self.max_match_score >= self.address_threshold:
                return detected_template
            else:
                return detected_template  # + ".doubtful"
        else:
            return ''

    def predict_with_vname_(self, ocr_data, tenant_id):
        trained_templates = get_trained_templates(tenant_id=tenant_id)

        # If nothing is trained then return no template
        if not trained_templates:
            return None

        text = []
        for word in ocr_data[0]:
            text.append(word['word'])
        plain_text = ' '.join(text)

        matched_templates = []

        for template in trained_templates:
            if template.lower().split('_')[0] in plain_text.lower():
                matched_templates.append(template)
            else:
                pass

        return matched_templates

    def predict_combo(self, ocr_data, tenant_id):
        filter = self.predict_with_vname_(ocr_data, tenant_id=tenant_id)

        # print(filter)

        if filter:
            self.threshold = 0.6
        else:
            self.threshold = 0.8

        return self.predict_with_wv(ocr_data, filter)

    def predict_combo_ngram(self, ocr_data, n=2):
        self.threshold = 0.8

        ngram_result = self.predict_with_ngram(ocr_data, n)

        if ngram_result == '':
            return self.predict_with_wv(ocr_data)
        else:
            return ngram_result

    def aankho_dekhi_method(self, ocr_data, template_detected=''):
        max_match_score = 0
        max_match_template = ''
        trained_templates = self.trained_info

        use_aankho_dekho = False

        if template_detected:
            if template_detected in trained_templates:
                use_aankho_dekho = True
        else:
            use_aankho_dekho = True

        if use_aankho_dekho:
            for template, template_data in trained_templates.items():
                if 'ad_trained_info' in template_data and template_data['ad_trained_info']:
                    max_match = 0
                    for page in ocr_data:
                        match = match_box(template_data['ad_trained_info'], page)
                        if max_match < match:
                            max_match = match

                    if max_match_score < max_match:
                        max_match_score = max_match
                        max_match_template = template

        return max_match_template

    def old_unique_field_method(self, template, unique_fields, condition, first_text, meta_text, list_prob_temp):
        # condition = 'or'
        ocr_unique_fields_list = []
        meta_unique_fields_list = []
        logging.debug(f'template - {template} , unique fields - {unique_fields}')
        for word in unique_fields:
            text = word['text']
            type = word['type']
            if type == 'ocr':
                ocr_unique_fields_list.append(remove_all_except_al_num(text).replace(' ', ''))
            elif type == 'meta':
                meta_unique_fields_list.append(remove_all_except_al_num(text).replace(' ', ''))
            elif type == 'orphan':
                ocr_unique_fields_list.append(remove_all_except_al_num(text).replace(' ', ''))

        found_template = False
        found_template_ocr = False

        if condition == 'and':
            logging.debug(f'using and part')
            found_template = True

            # metric part
            for unique in meta_unique_fields_list:
                if len(unique) == 0 or len(meta_text) == 0 or string_match(unique, meta_text) < self.threshold * 100:
                    found_template = False
                    break
                else:
                    found_template = True
            if found_template:
                if ocr_unique_fields_list:
                    found_template = False
                    for unique in ocr_unique_fields_list:
                        logging.debug(f'unique - {unique}')
                        if len(unique) == 0 or string_match(unique, first_text) < self.threshold * 100:
                            found_template = False
                            break
                        else:
                            found_template = True

            if found_template:
                list_prob_temp.append({'template': template, 'condition': 'and'})

            found_template = True

            # first checking meta fields
            for unique in meta_unique_fields_list:
                if len(unique) == 0 or len(meta_text) == 0 or (
                        unique not in meta_text and string_match(unique, meta_text) < self.threshold * 100):
                    found_template = False
                    break
                else:
                    found_template = True

            if found_template:
                if not ocr_unique_fields_list:
                    return {'probable_templates': list_prob_temp}

                found_template = False
                # checking ocr fields
                for unique in ocr_unique_fields_list:
                    logging.debug(f'unique - {unique}')
                    if len(unique) == 0 or (
                            (unique not in first_text) and string_match(unique, first_text) < self.threshold * 100):
                        found_template = False
                        break
                    else:
                        found_template = True

            logging.debug(f'detection processing is over')
            if found_template:
                return {'template': template, 'probable_templates': list_prob_temp}
            else:
                return {'probable_templates': list_prob_temp}
        else:
            # meta field check
            for unique in meta_unique_fields_list:
                # for metrics purpose
                if unique and meta_text and string_match(unique, meta_text) > self.threshold * 100:
                    list_prob_temp.append({'template': template, 'condition': 'or'})

                if unique and meta_text and string_match(unique, meta_text) > self.threshold * 100:
                    return {'template': template, 'probable_templates': list_prob_temp}

            # ocr field check
            for unique in ocr_unique_fields_list:
                if unique and first_text and string_match(unique, first_text) > self.threshold * 100:
                    list_prob_temp.append({'template': template, 'condition': 'or'})

                if unique and first_text and string_match(unique, first_text) > self.threshold * 100:
                    return {'template': template, 'probable_templates': list_prob_temp}

        return {'probable_templates': list_prob_temp}

    def new_unique_fields(self, template, unique_fields, first_text, meta_text, list_prob_temp):
        for priority in unique_fields:
            rule = str(priority['rule']['execution_rule'])
            logging.debug(f'rule - {rule}')
            identifiers = priority['rule']['identifiers']
            logging.debug(f'identifiers - {identifiers}')
            for identifier in identifiers:
                field_name = identifier['field']
                field_type = identifier['type']
                field_text = remove_all_except_al_num(identifier['text']).replace(' ', '')
                threshold = int(identifier.get('threshold', self.threshold * 100))
                boolean_result = False

                if field_type == 'meta':
                    if field_text and meta_text and string_match(field_text, meta_text) >= threshold:
                        boolean_result = True

                elif field_type == 'ocr':
                    if field_text and first_text and string_match(field_text, first_text) >= threshold:
                        boolean_result = True
                try:
                    logging.debug(f'field - {field_name} matching % - {string_match(field_text, first_text)}')
                except:
                    logging.exception('error')
                    
                rule = rule.replace(field_name, str(boolean_result))

            logging.debug(f'rule - {rule}')
            if eval(rule):
                return {'template': template}
            else:
                continue
        return {}

    def template_prediction(self, template_name, template_data, first_text, meta_text, list_prob_temp):
        old_method = False
        try:
            unique_fields = json.loads(template_data['unique_fields'])
            if isinstance(unique_fields, list):
                old_method = True
            else:
                unique_fields = unique_fields.get('unique_fields', [])
        except:
            unique_fields = [{'type': 'orphan', 'text': template_data['unique_fields']}]
        condition = template_data['condition']

        if old_method:
            response = self.old_unique_field_method(template_name, unique_fields, condition, first_text, meta_text,
                                                    list_prob_temp)
            list_prob_temp = response.get('probable_templates', list_prob_temp)
            template = response.get('template', '')
        else:
            response = self.new_unique_fields(template_name, unique_fields, first_text, meta_text, list_prob_temp)
            template = response.get('template', '')

        return template

    def unique_fields(self, ocr_data, meta_data=(), template_name=''):
        sorted_ocr_data = []
        first_text = []

        for data in ocr_data:
            sorted_ocr_data.append(sort_ocr(data))
            # sorted_ocr_data.append(sorted(data, key=lambda k: k['top']))

        for data in sorted_ocr_data:
            for i in data:
                first_text.append(i['word'].encode('utf-8').decode().lower())

        first_text = ''.join(first_text)
        first_text = remove_all_except_al_num(first_text).replace(' ', '')

        if meta_data:
            meta_text = ''.join(meta_data)
            meta_text = remove_all_except_al_num(meta_text).replace(' ', '')
        else:
            meta_text = None

        trained_templates = self.trained_info

        logging.debug(f'first_text - {first_text}')
        list_prob_temp = []

        template = ''
        if template_name:
            if template_name in trained_templates:
                template_data = trained_templates[template_name]
                template = self.template_prediction(template_name, template_data, first_text, meta_text, list_prob_temp)
        else:
            for template_name, template_data in trained_templates.items():
                template = self.template_prediction(template_name, template_data, first_text, meta_text, list_prob_temp)
                if template:
                    break


                    
        return {'template': template, 'probable_templates': list_prob_temp}