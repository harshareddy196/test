import json
import spacy
import random
import os
import traceback


from pathlib import Path
from tqdm import tqdm
from flask import Flask, request, jsonify
from flask_cors import CORS

from ace_logger import Logging

app = Flask(__name__)
CORS(app)

logging = Logging()

class KeywordTrainer():
    def __init__(self, model_path=None):
        self.MODEL_PATH = model_path
        self.TRAIN_DATA = []
        self.MODEL = None
        try:
            self.nlp = spacy.load(self.MODEL_PATH)
        except:
            print("KeywordTrainer kho gaye")
            self.nlp = None
            traceback.print_exc()

    def get_model(self):
        logging.debug(f'Getting model from `{self.MODEL_PATH}`')
        if Path(self.MODEL_PATH).exists():
            logging.debug(f'Path exists')
            if (Path(self.MODEL_PATH) / 'tokenizer').is_file(): 
                logging.debug(f'Contains model files. Model will be retrained.')
                return self.MODEL_PATH
            else:
                logging.warning('Does not contain model files. Use save_model method to save.')
        else:
            logging.warning('Model path does not exist')
            raise IOError(f'Model path `{Path(self.MODEL_PATH).absolute()}` does not exist')
        
        return

    def train(self, ocr_text, trained_info, n_iter=25):
        entities = []

        for field, data in trained_info.items():
            if not data['keyword']:
                continue
            
            keyword = data['keyword'].lower()

            try:
                start = ocr_text.lower().index(keyword)
                end = start + len(keyword)
            except:
                continue
            
            entities.append((start, end, field))
                    
        self.TRAIN_DATA.append((ocr_text, {'entities': entities}))
        try:
            self.MODEL = self.get_model()
        except:
            self.MODEL = None

        if self.MODEL is not None:
            self.nlp = spacy.load(self.MODEL)  # load existing spaCy model
            logging.debug(f'Loaded model `{self.MODEL}`')
        else:
            logging.debug('Created blank "en" model')
            self.nlp = spacy.blank('en')  # Create blank Language class
        
        if 'ner' not in self.nlp.pipe_names:
            ner = self.nlp.create_pipe('ner')
            self.nlp.add_pipe(ner)
        else:
            ner = self.nlp.get_pipe('ner')
        
        # * Add label
        logging.debug('Adding labels')
        for _, annotations in self.TRAIN_DATA:
            for ent in annotations['entities']:
                logging.debug(f'Adding: {ent[2]}')
                ner.add_label(ent[2])
        
        # * Get names of other pipes to disable them while training
        logging.debug('Disabling pipes')
        losses = {}
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != 'ner']
        with self.nlp.disable_pipes(*other_pipes):
            optimizer = self.nlp.begin_training()
        
            for itn in range(n_iter):
                random.shuffle(self.TRAIN_DATA)
                losses = {}
        
                for text, annotations in self.TRAIN_DATA:
                    # print('kuch to ho rha hai')
                    self.nlp.update(
                        [text],
                        [annotations],
                        drop=0.5,
                        sgd=optimizer,
                        losses=losses
                    )
                logging.debug(losses)

        return True
    
    def predict(self, string):
        logging.info('Predicting')
        logging.debug(f'String: {string}')


        field_entities = {}
        try:

            logging.info('write a file')
            toWrite = "hello world"

            with open('/var/www/training_api/app/textfile.txt','w') as f:
                f.write(toWrite)

            logging.info('writing is complete')

            print('model_path = ', self.MODEL_PATH)

            logging.info('read a file')
            with open(f'{self.MODEL_PATH}meta.json','r') as f:
                print(f.read())

            logging.info('reading complete')

            self.nlp = spacy.load(self.MODEL_PATH)

            # logging.info('reading complete')

            doc = self.nlp(string)

            logging.info('keywords mil gaye')

            for ent in doc.ents:
                field = ent.label_
                keyword = ent.text
                start = ent.start_char
                end = ent.end_char
                
                keywords_info = {
                        'keyword': keyword,
                        'start': start,
                        'end': end,
                        'field': field
                    }



                if field in field_entities:
                    field_entities[field].append(keywords_info)
                else:
                    field_entities[field] = [keywords_info]
        
            logging.debug(f'Field Entitites: {json.dumps(field_entities, indent=2)}')

        except:
            traceback.print_exc()
            logging.debug(f'prediction mai kuch kharabi')

        return field_entities

    def save_model(self):
        logging.debug(f'Saving model to {self.MODEL_PATH}')
        self.nlp.to_disk(self.MODEL_PATH)


@app.route('/train', methods = ['POST'])
def ner_training():
    logging.info('Training NER')
    result = request.json

    ocr_text = result['ocr_text']
    field_data = result['field_data']

    #training the ner keyword prediction model
    try:
        ner_model_path = '/home/akshat/file_io/model/'

        print("path dekho to zara - ", ner_model_path)

        keyword_trainer = KeywordTrainer(ner_model_path)


        keyword_trainer.train(ocr_text, field_data)

        keyword_trainer.save_model()

        print("training ner model complete")
        return 'True'
    except:
        logging.error('path wrong maybe')
        traceback.print_exc()
        return 'False'

    

if __name__ == "__main__":
    # # Fetch data from database
    # db_config = {
    #     'host': '3.208.195.34',
    #     'user': 'root',
    #     'password': 'AlgoTeam123',
    #     'database': 'queues'
    # }
    # db = DB(**db_config)

    # query = ('SELECT process_queue.id, process_queue.case_id, ocr_info.ocr_text, '
    #     'trained_info.template_name, trained_info.field_data '
    #     'FROM process_queue, ocr_info, trained_info '
    #     'WHERE process_queue.case_id=ocr_info.case_id '
    #     'AND process_queue.template_name=trained_info.template_name ')
    # data = db.execute(query)

    # ocr_text = list(data['ocr_text'])[0]
    # trained_info = json.loads(list(data['field_data'])[0])

    # kt = KeywordTrainer('./model')
    # kt.train(ocr_text, trained_info)
    # kt.save_model()
    # kt.predict(ocr_text)
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-p', '--port', type=int, help='Port Number', default=7002)
    # parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    # args = parser.parse_args()

    host = '0.0.0.0'
    port = 7002

    app.run(host=host, port=port, debug=False)