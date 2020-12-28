''' NLP TOOLS FOR MICROSOFT COGNITIVE SERVICES '''
''' tiwalz@microsoft.com '''
''' Supports Text-To-Speech (TTS), Speech-To-Text (STT) and LUIS-Scoring '''

# Import standard packages
import os
import sys
import shutil
import logging
import argparse
import configparser
import pandas as pd

# Import custom modules
import luis
import stt
import tts
import params as pa
import helper as he
import evaluate as eval

''' COMMAND EXAMPLES '''
# python .\src\main.py --do_synthesize --input input/scoringfile.txt

# Parse arguments
parser = argparse.ArgumentParser()
args = pa.get_params(parser)

# Set arguments
fname = args.input
luis_treshold = args.treshold
audio_files = args.audio
do_synthesize = args.do_synthesize
do_scoring = args.do_scoring
do_transcribe = args.do_transcribe
do_evaluate = args.do_evaluate

# Get config
pa.get_config()

# Set logger
logging.getLogger().setLevel(logging.INFO)

if __name__ == '__main__':
    logging.info('[INFO] - Starting Cognitive Services Tools - v0.1')

    # Case Management
    if any([do_scoring, do_synthesize, do_transcribe, do_evaluate]):
        output_folder, case = he.create_case(pa.output_folder)
        logging.info(f'[INFO] - Created case {case}')
        try:
            shutil.copyfile(fname, f'{output_folder}/{case}/input/{os.path.basename(fname)}')
            df_reference = pd.read_csv(f'{output_folder}/{case}/input/{os.path.basename(fname)}', sep=';', encoding='utf-8', index_col=None)
            logging.info(f'[INFO] - Copied input file(s) to case folder')
        except Exception as e:
            if do_synthesize or do_scoring:
                logging.error(f'[ERROR] - Could not find input file, but it is required for --do_transcribe and/or --do_scoring -> {e}')
                sys.exit()
            else:
                logging.warning('[WARNING] - Could not find input file, but we can continue here')
                df_reference = pd.DataFrame()
    else:
        logging.error('[ERROR] - Please activate at least one of the following modes: --do_synthesize, --do_transcribe, --do_scoring, --do_evaluate (see --help for further information)!')
        sys.exit()

    # TTS
    if do_synthesize:
        logging.info(f'[STATUS] - Starting text-to-speech synthetization of {len(df_reference)} utterances')
        df_reference = tts.main(df_reference, f'{output_folder}/{case}', pa.stt_endpoint)
        df_reference[['audio_synth', 'text']].to_csv(f'{output_folder}/{case}/stt_transcription.txt', sep = "\t", header = None, index = False)
        logging.info(f'[STATUS] - Finished text-to-speech synthetization of {len(df_reference)} utterances')

    # STT
    if do_transcribe:
        if audio_files != None:
            logging.info('[STATUS] - Starting with speech-to-text conversion')
            stt_results = stt.main(f'{audio_files}/', f'{output_folder}/{case}')
            transcription = pd.DataFrame(list(stt_results), columns=['audio', 'rec'])
            logging.debug(transcription)
            transcription.to_csv(f'{output_folder}/{case}/tts_transcriptions.txt', sep = "\t", header = None, index=False)
            # Merge 
            if 'audio' in list(df_reference.columns):
                df_reference = pd.merge(left = df_reference, right = transcription, how = 'left', on = 'audio')
                logging.info(f'[STATUS] - Merged imported reference transcriptions and recognitions')
        else:
            logging.error('[ERROR] - It seems like you did not pass a path to audio files, cannot do transcriptions')
            sys.exit()

    # Speech Evaluation
    if do_evaluate:
        logging.info('[STATUS] - Starting with reference vs. recognition evaluation')
        if 'text' in list(df_reference.columns) and 'rec' in list(df_reference.columns):
            eval.main(df_reference)
            logging.info('[STATUS] - Evaluated reference and recognition transcriptions')
        else:
            logging.error('[ERROR] - Cannot do evaluation, please verify that you both have "ref" and "rec" in your data!')

    # LUIS Scoring
    if do_scoring:
        logging.info('[STATUS] - Starting with LUIS scoring')
        logging.info(f'[INFO] - Set LUIS treshold to {pa.luis_treshold}')
        if 'intent' in list(df_reference.columns):
            luis_scoring = luis.main(df_reference)
            luis_scoring.to_csv(f'{output_folder}/{case}/luis_scoring.txt', sep = '\t', encoding = 'utf-8', index=False)
        else:
            logging.error('[ERROR] - Cannot do LUIS scoring, please verify that you have an "intent"-column in your data.')   

    # Write transcript file
    try:
        df_reference.to_csv(f'{output_folder}/{case}/transcriptions_full.txt', sep = '\t', encoding = 'utf-8', index = False)
        logging.info(f'[STATUS] - Wrote transcription file to case folder')
        logging.info(f'[STATUS] - Finished with the run {case}!')
    except Exception as e:
        logging.error(f'[ERROR] - An error has occured -> {e}')