''' NLP TOOLS FOR MICROSOFT COGNITIVE SERVICES '''
''' tiwalz@microsoft.com '''
''' Supports Text-To-Speech, Speech-To-Text and LUIS-Scoring '''

# Import required packages
import logging
import argparse
import os
import sys
import configparser
import shutil
import pandas as pd
import helper as he
import scoreLUIS as sl
import speechTranscribe as stt
import synthesizeText as tts
import evaluate as ev
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix

''' COMMAND EXAMPLES '''
# conda activate nlptools
# python .\code\speechTools.py  --do_synthesize --input input/scoringfile.txt

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--input",
                type=str,
                default="input/testset-example.txt",
                help="give the whole path to tab-delimited file")  
parser.add_argument("--mode", 
                default="score",
                type=str,
                help="Mode, either score or eval")
parser.add_argument("--subfolder", 
                default="input",
                type=str,
                help="Input folders, pass comma-separated if multiple ones")
parser.add_argument("--audio_files", 
                default="input/audio/",
                type=str,
                help="Input folders, pass comma-separated if multiple ones")
parser.add_argument("--treshold", 
                default=0.82,
                type=float,
                help="Set minimum confidence score between 0.00 and 1.00") 
parser.add_argument("--do_transcribe",
                default=False,
                 action="store_true",
                help="Input folder of audio files")
parser.add_argument("--do_scoring",
                 default=False,
                 action="store_true",
                 help="Text to speech using Microsoft Speech API") 
parser.add_argument("--do_synthesize",
                 default=False,
                 action="store_true",
                 help="Text to speech using Microsoft Speech API")
parser.add_argument("--do_evaluate",
                 default=True,
                 action="store_true",
                 help="Evaluate speech transcriptions")  
parser.add_argument("--do_lufile",
                 default=False,
                 action="store_true",
                 help="Create LU-file")  
args = parser.parse_args()

# Set arguments
fname = args.input
mode = args.mode
subfolder = args.subfolder
tres = args.treshold
audio_files = args.audio_files
do_synthesize = args.do_synthesize
do_scoring = args.do_scoring
do_transcribe = args.do_transcribe
do_evaluate = args.do_evaluate
do_lufile = args.do_lufile

# Get config file
sys.path.append('./')
config = configparser.ConfigParser()
try:
    config.read('config.ini')
    output_folder = config['dir']['output_folder']
    app_id = config['luis']['app_id']
    key = config['luis']['key']
    region_luis = config['luis']['region']
    luis_endpoint = config['luis']['endpoint']
    slot = config['luis']['slot']
    speech_key = config['speech']['key']
    endpoint = config['speech']['endpoint']
    region_speech = config['speech']['region']
    synth_key = config['synth']['key']
    region_synth = config['synth']['region']
    resource_name = config['synth']['resource_name']
    language = config['synth']['language']
    font = config['synth']['font']
except Exception as e:
    sys.exit(f'[EXCEPT] - Config file could not be loaded -> {e}.')

if __name__ == '__main__':
    logging.warning('[INFO] - STARTING SPEECHTOOL')
    # Case management
    try:
        if any([do_scoring, do_synthesize, do_transcribe, do_evaluate]):
            output_folder, case, output_file = he.createCase(mode, output_folder, subfolder)
            shutil.copyfile(fname, f'{output_folder}{case}input/{os.path.basename(fname)}')
            logging.warning(f'[STATUS] - Created case {case} and copied input files to case folder')
        else:
            sys.exit('[ERROR] - Please activate at least one of the following modes: --do_synthesize, --do_transcribe, --do_scoring, --do_evaluate')
    except Exception as e:
        logging.info(f'[ERROR] -> {e}')

    # File reader
    if os.path.exists(f'{output_folder}{case}input/{os.path.basename(fname)}'):
        df = pd.read_csv(f'{output_folder}{case}input/{os.path.basename(fname)}', sep='\t', encoding='utf-8', index_col=None)
    
    # TTS
    if do_synthesize:
        logging.warning('[STATUS] - Starting text-to-speech synthetization')
        df = tts.batchSynthesize(df, synth_key, language, font, region_synth, resource_name, output_folder, case)
        logging.warning(f'[STATUS] - Finished text-to-speech synthetization of {len(df)} utterances')

    # Speech
    if do_transcribe:
        if audio_files != "":
            logging.warning('[STATUS] - Starting with speech-to-text conversion')
            stt.batchTranscribe(audio_files, output_folder, case, region_speech, speech_key, endpoint)
            transcription = pd.read_csv(f'{output_folder}{case}transcriptions.txt', sep="\t", names=['audio', 'rec'], encoding='utf-8', header=None, index_col=None)
            if 'audio' in list(df.columns):
                df = pd.merge(left=df, right=transcription, how='left', on='audio')

    # Speech Evaluation
    if do_evaluate:
        logging.warning('[STATUS] - Starting with ref/rec evaluation')
        if 'text' in list(df.columns) and 'rec' in list(df.columns):
            df.text = df.text.fillna("")
            df.rec = df.rec.fillna("")
            eva = ev.EvaluateTranscription()
            eva.calculate_metrics(df.text.values, df.rec.values, label=df.index.values, print_verbosiy=2)
            eva.print_errors(min_count=1)
        else:
            logging.error('[ERROR] - Cannot do evaluation, please verify that you both have "ref" and "rec" in your data!')

    # LUIS
    if do_scoring and 'intent' in list(df.columns):
        if mode == 'score':
            logging.warning('[STATUS] - Starting with LUIS scoring')
            data = sl.scoreLUIS(df, mode, app_id, luis_endpoint, key, tres, slot)
            data.to_csv(output_file, sep='\t', encoding='utf-8', index=False)
        elif mode == 'eval':
            logging.warning('[STATUS] - Starting with LUIS eval')
            data = pd.read_csv(fname, sep='\t', encoding='utf-8')
        # Classification Report
        print('[OUTPUT] - CLASSIFICATION REPORT (without drop)')
        print(classification_report(data['intent'], data['prediction']))
        print(f'[OUTPUT] - AFTER DROP ({tres})')
        print(classification_report(data['intent'], data['drop']))
        print('[OUTPUT] - Confusion Matrix:')
        print(confusion_matrix(data['intent'], data['prediction']))

    # Write transcript file
    try:
        df.to_csv(f'{output_folder}{case}transcriptions.txt', sep="\t", encoding="utf-8", index=False)
        logging.warning(f'[INFO] - Wrote transcription file to case.')
        logging.warning(f'[STATUS] - All set!')
    except Exception as e:
        logging.warn(f'[ERROR] - An error has occured -> {e}.')