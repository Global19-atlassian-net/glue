''' LUIS SCORING SCRIPT '''
''' tiwalz@microsoft.com '''

# Import required packages
import logging
import requests
import json
import pandas as pd
import sys
from datetime import datetime
import argparse
import shutil
import os
import configparser
import time
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
import params as pa

# Load and set configuration parameters
pa.get_config()

def request_luis(text):
    """Scores or loads a LUIS scoring file to assess the model quality and delivers insights
    Args:
        df: input data frame
        mode: choice between scoring and 
        appId: LUIS app ID
        key: LUIS subscription key
        slot: Staging slot, production or staging, default on production
        treshold: minimum confidence score for LUIS result, between 0.00 and 1.00, default on 0.85
    Returns:
        df: scoring data frame with predicted intents and scores
    Raises:
      ConnectionError: if file is not found
    """
    # Uncomment this if you are using the old url version having the region name as endpoint.
    # endpoint_url = f'{endpoint}.api.cognitive.microsoft.com'.
    # Below, you see the most current version of the api having the prediction resource name as endpoint.     
    endpoint_url = f'{pa.luis_endpoint}.cognitiveservices.azure.com'
    headers = {}
    params = {
        'query': text,
        'timezoneOffset': '0',
        'verbose': 'true',
        'show-all-intents': 'true',
        'spellCheck': 'false',
        'staging': 'false',
        'subscription-key': pa.luis_key
    }
    r = requests.get(f'https://{endpoint_url}/luis/prediction/v3.0/apps/{pa.luis_appid}/slots/{pa.luis_slot}/predict', headers=headers, params=params)
    # Check
    logging.debug(json.dumps(json.loads(r.text), indent=2))
    return r.json()

def luis_classification_report(df):
    print('[OUTPUT] - CLASSIFICATION REPORT (without reset by treshold):')
    print(classification_report(df['intent'], df['prediction']))
    print(f'[OUTPUT] - AFTER RESET BY TRESHOLD ({treshold}):')
    print(classification_report(df['intent'], df['drop']))
    print('[OUTPUT] - CONFUSION MATRIX:')
    print(confusion_matrix(df['intent'], df['prediction']))

def main(df, treshold=0.85, mode="score"):
    # Set lists for results
    predictions = []
    scores = []
    prediction_drop = []
    # Loop through text rows, predict and process values
    for index, row in df.iterrows():
        try:
            data = request_luis(row['text'])
            # Extract relevant information from results
            top_intent = data['prediction']['topIntent']
            top_score = data['prediction']['intents'][top_intent]['score']
            # Evaluat scores based on treshold and set None-intent if too low
            if top_score < treshold: 
                drop = "None"
            else:
                drop = top_intent
            logging.info(f"[INFO] {str(index+1)}/{len(df)} -> '{row['text']}' -> Original: {row['intent']}, Pred: {top_intent} ({top_score}, drop? {top_intent != row['intent']})")
            # Apennd scores and predictions to lists
            predictions.append(top_intent)
            scores.append(top_score)
            prediction_drop.append(drop)
            # Go to sleep for half a second
            time.sleep(0.5)
        except Exception as e:
            logging.error(f'[ERROR] - Request failed -> {e}')
            predictions.append("nan")
            scores.append("nan")
            prediction_drop.append("nan")
    # Append lists as columns to data frame
    df['prediction'] = predictions
    df['score'] = scores
    df['prediction_drop'] = prediction_drop
    # Create and print classification report
    luis_classification_report(df)
    return df

if __name__ == '__main__':
    df = main(pd.DataFrame({'intent': ['Book_Flight', 'Cancel_Flight'], 'text': ['I want to book a flight to Singapore.', 'I need to cancel my flight from Stuttgart to Singapore.']}))
    print(df)