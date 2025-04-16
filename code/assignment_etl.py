import streamlit as st
import pandas as pd
import os
import requests
import json 
if __name__ == "__main__":
    import sys
    sys.path.append('code')
    from apicalls import get_google_place_details, get_azure_sentiment, get_azure_named_entity_recognition
else:
    from code.apicalls import get_google_place_details, get_azure_sentiment, get_azure_named_entity_recognition

PLACE_IDS_SOURCE_FILE = "code/cache/place_ids.csv"
CACHE_REVIEWS_FILE = "code/cache/reviews.csv"
CACHE_SENTIMENT_FILE = "code/cache/reviews_sentiment_by_sentence.csv"
CACHE_ENTITIES_FILE = "code/cache/reviews_sentiment_by_sentence_with_entities.csv"


def reviews_step(place_ids: str|pd.DataFrame) -> pd.DataFrame:
    '''
      1. place_ids --> reviews_step --> reviews: place_id, name (of place), author_name, rating, text 
    '''
    if isinstance(place_ids, str):
        place_df = pd.read_csv(place_ids)
    else:
        place_df = place_ids

    detail_list = []
    for i,row in place_df.iterrows():
        details = get_google_place_details(row["Google Place ID"])
        detail_list.append(details["result"])
    
    reviews = pd.json_normalize(detail_list, record_path="reviews", meta= [["place_id"],["name"]])
    reviews_df = reviews[["place_id", "name", "author_name", "rating", "text"]]
    reviews_df.to_csv(CACHE_REVIEWS_FILE, index = False, header = True)
    return reviews_df

def sentiment_step(reviews: str|pd.DataFrame) -> pd.DataFrame:
    '''
      2. reviews --> sentiment_step --> review_sentiment_by_sentence
    '''
    if isinstance(reviews, str):
        reviews_df = pd.read_csv(reviews)
    else:
        reviews_df = reviews

    sentiment_list = []
    for i,row in reviews_df.iterrows():
        sentiment = get_azure_sentiment(row["text"])
        # Getting results in form of dict, adding values from review_df
        sentiment_result = sentiment["results"]["documents"][0]
        sentiment_result["place_id"] = row["place_id"]
        sentiment_result["name"] = row["name"]
        sentiment_result["author_name"] = row["author_name"]
        sentiment_result["rating"] = row["rating"]
        sentiment_list.append(sentiment_result)
    
    sentiments = pd.json_normalize(sentiment_list, record_path="sentences",
                                    meta=["place_id", "name", "author_name", "rating"])
    sentiments.rename(columns={"text":"sentence_text", "sentiment":"sentence_sentiment"}, inplace=True)
    sentiments_df = sentiments[["place_id", "name", "author_name", "rating",
                                 "sentence_text", "sentence_sentiment",
                                 "confidenceScores.positive", "confidenceScores.neutral",
                                 "confidenceScores.negative"]]
    sentiments_df.to_csv(CACHE_SENTIMENT_FILE, index = False, header = True)
    return sentiments_df 


def entity_extraction_step(sentiment: str|pd.DataFrame) -> pd.DataFrame:
    '''
      3. review_sentiment_by_sentence --> entity_extraction_step --> review_sentiment_entities_by_sentence
    '''
    if isinstance(sentiment, str):
        sentiment_df = pd.read_csv(sentiment)
    else:
        sentiment_df = sentiment
    
    extraction_list = []
    for i,row in sentiment_df.iterrows():
        entities = get_azure_named_entity_recognition(row["sentence_text"])
        entity_results = entities["results"]["documents"][0]
        entity_results["place_id"] = row["place_id"]
        entity_results["name"] = row["name"]
        entity_results["author_name"] = row["author_name"]
        entity_results["rating"] = row["rating"]
        entity_results["sentence_text"] = row["sentence_text"]
        entity_results["sentence_sentiment"] = row["sentence_sentiment"]
        entity_results["confidenceScores.positive"] = row["confidenceScores.positive"]
        entity_results["confidenceScores.neutral"] = row["confidenceScores.neutral"]
        entity_results["confidenceScores.negative"] = row["confidenceScores.negative"]
        extraction_list.append(entity_results)
      
    entities = pd.json_normalize(extraction_list, record_path="entities",
                                  meta= ["place_id", "name", "author_name", "rating",
                                 "sentence_text", "sentence_sentiment",
                                 "confidenceScores.positive", "confidenceScores.neutral",
                                 "confidenceScores.negative"])
    entities.rename(columns={"text":"entity_text", "category":"entity_category",
                              "subcategory":"entity_subCategory", "confidenceScore":"confidenceScores.entity"}, inplace=True)
    entities_df = entities[["place_id", "name", "author_name", "rating","sentence_text",
                             "sentence_sentiment","confidenceScores.positive",
                               "confidenceScores.neutral","confidenceScores.negative",
                               "entity_text", "entity_category", "entity_subCategory",
                               "confidenceScores.entity"]]
    entities_df.to_csv(CACHE_ENTITIES_FILE, index = False, header = True)
    return entities_df


if __name__ == '__main__':
    # Testing that ETL steps work
    print("Current working dir:", os.getcwd())
    reviews_step(PLACE_IDS_SOURCE_FILE)
    sentiment_step(CACHE_REVIEWS_FILE)
    entity_extraction_step(CACHE_SENTIMENT_FILE)

    #TEST DATAFRAME
    entity_df = pd.read_csv(CACHE_ENTITIES_FILE)
    print(entity_df)