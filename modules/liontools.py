#cfg
import os
import time
import torch
from cfg import creds

#ai
import openai
import transformers
import huggingface_hub as hf
import json


#data
import pandas as pd
import tweepy
import csv
import datetime
import cleantext

#netsci
import networkx as nx
import matplotlib.pyplot as plt


#lab class to initialize the lab, check gpu, validate apis for AI ad Data subclass
class Lab:
    def __init__(self):
        self.initialized = False
        self.openAI_validated = False
        self.openAI_key = ""
        self.hf_validated = False
        self.hf_token = ""
        self.roberta_base_sentiment = "cardiffnlp/twitter-roberta-base-sentiment-latest" #this is the good one
        #self.roberta_base_sentiment="mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis" #this is just faster for demoing
        #self.roberta_base_sentiment = "cardiffnlp/twitter-roberta-base-sentiment"
        #self.distilbert_base_uncased_emotion = "bhadresh-savani/distilbert-base-uncased-emotion"
        #self.bertweet_emotion = "Emanuel/bertweet-emotion-base"
        self.distilbert_base_uncased_emotion = "joeddav/distilbert-base-uncased-go-emotions-student"
        self.roberta_base_emotion = "arpanghoshal/EmoRoBERTa"
        self.twitter_validated = False
        self.twitter_consumer_key = ""
        self.twitter_consumer_secret = ""
        self.twitter_access_token = ""
        self.twitter_access_secret = ""
        self.twitter_api=""
        self.twitter_auth = ""



    def initialize(self):
        print("Lab booting up...")
        time.sleep(1.25) #delay 1.25s
        print()
        # Check GPU status
        if torch.cuda.is_available():
            print("GPU found. Lab compute accelerated.")
            print()
        else:
            print("No GPU detected. Lab running with nominal compute.")
            print()
            time.sleep(.5) #delay 1.25s
        # Initialize lab
        self.initialized = True
        
    
    def validate(self):
    # Validate OpenAI API credentials
        try:
            openai.api_key = creds.ai_secret
            self.openAI_key = creds.ai_secret
            self.openAI_validated = True
            print("OpenAI API credentials validated")
            print()
        except KeyError:
            print("OpenAI key invalid.")
            print()
            
    # Validate HuggingFace credentials
        try:
            hf_token = creds.hf_token
            self.hf_token = hf_token
            print("Logging into Huggingface...")
            print()
            time.sleep(.25)
            hf.login(hf_token)
            self.hf_validated = True
            print()
        except KeyError:
            print("Huggingface token invalid.")
            print()


class AI(Lab):
    def __init__(self):
        super().__init__()

    # get response from gpt3
    def get_response(self, prompt):
        """Get response from the GPT-3 model using OpenAI's API.

        Args:
        - prompt (str): The prompt to pass to the GPT-3 model.

        Returns:
        - str: The response generated by the GPT-3 model.
        """
        model_engine = "text-davinci-003"
        prompt = (f"{prompt}"
                 )
        respose = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.5,
        )
        message = respose.choices[0].text
        return message
    
    # for topic summarization from gpt3
    def gpt_clean_topics(self, prompt):
        """Similar to get response but temp and top p adjusted to support more consistency in outputs.

        Args:
        - prompt (str): The prompt to pass to the GPT-3 model. MUST USE ":" STOP SEQUENCE FOR OPTIMIZED PERFORMANCE.

        Returns:
        - str: The response generated by the GPT-3 model.
        """
        model_engine = "text-davinci-003"
        prompt = (f"{prompt}"
                 )
        response = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            temperature=0,
            max_tokens=50,
            # n=1, not totally sure what this does
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=[":"]
        )
        topic = response.choices[0].text
        return topic

    
    # for topic summarization from gpt3
    def gpt_zShot_topic(self, text):
        """Zero shot topic classification with GPT-3.

        Args:
        - prompt (str): The prompt to pass to the GPT-3 model.

        Returns:
        - str: The response generated by the GPT-3 model.
        """
        model_engine = "text-davinci-003"
        prompt = (f"Assign a topic label to the text: {text}\n\nAnswer:"
                 )
        response = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            temperature=0,
            max_tokens=50,
            # n=1, not totally sure what this does
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=":"
        )
        topic = response.choices[0].text
        return topic
    
    def normalize_gpTopics(self, df):
        '''
        This function takes a dataframe with the zShot_Topic column and converts the unique topics to a list. 
        It passes that list to GPT-3 to convert that list of topics to a new list of topics.
        '''
        #for long dataframes we need to break up the list for the prompt bc token length
        def split_list(long_list):
            '''
            Returns a list of lists from a longer lists. Breaks up the longer list into smaller ones of max length 25.
            '''
            max_length = 25
            num_sublists = (len(long_list) + max_length - 1) // max_length
            sublist_length = len(long_list) // num_sublists
            sublists = []
            for i in range(num_sublists):
                start_index = i * sublist_length
                end_index = (i + 1) * sublist_length
                sublists.append(long_list[start_index:end_index])
            if len(long_list) % num_sublists != 0:
                sublists[-1].extend(long_list[sublist_length*num_sublists:])
            return sublists

        topics = list(df['zShot_Topic'].unique())
        topic_sublists = split_list(topics)

        final_response_dict = {}
        for sublist in topic_sublists:
            prompt=(f'''
            Create simplified set of topics for each topic in the list. The new set topics should aim to distill similar topics into a singular topic.
            Re-use topics that are applicable across otherrs.

            Return a dictionary.
            Example:

            list = ['Honda', 'Toyota', 'Red', 'Blue', 'Chair']
            dict = {{'Honda':'Car', 'Toyota':'Car', 'Red':'Color', 'Blue', 'Color', 'Chair':'Furniture'}}

            list = {sublist}
            dict =
            ''')
            model_engine = "text-davinci-003"
            completion = openai.Completion.create(
                engine=model_engine,
                prompt=prompt,
                temperature=0,
                max_tokens=1024,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop="="
            )
            response = completion.choices[0].text

            string = str(response)
            new_string = string.replace("'", "\"")
            response_dict = json.loads(new_string)
            final_response_dict.update(response_dict)
        
        # Use .map() to create a new column that maps values in 'my_column' to their corresponding values in 'my_dict'
        df['gpt_normalized_Topic'] = df['zShot_Topic'].map(final_response_dict)
        return df
    
    
    #get text embeddings from gpt3
    def get_embedding(self, text):
        text = text.replace("\n", " ")
        embedding = openai.Embedding.create(
            input = [text],
            model="text-similarity-davinci-001")
        return embedding['data'][0]['embedding']
    
    def analyze_sentiment(self, text, model=None):
        """Get sentiment of text from passed model. Defaults to roberta_base_sentiment_latest.

        Args:
        - text (str): The text to pass to the model.
        - model (obj) : the predefined HF model object.

        Returns:
        - str: The model response; sentiment output.
        """
        if model is None:
            model = self.roberta_base_sentiment
        nlp = transformers.pipeline("sentiment-analysis", model=model)
        try:
            sentiment = nlp(text)
        except:
            sentiment = [{'label': 'neutral', 'score': 0.0}]
        return sentiment
    
    
    def get_sentiment_features(self, df):
        """Add label and score columns to a dataframe of text based on sentiment analysis.

        Args:
        - df (DataFrame obj): The dataframe to pass to the model.

        Returns:
        - DataFrame: The original dataframe with label and score columns added.
        """
        # apply the analyze_sentiment function to the sentiment column
        sentiment_scores = df['content'].apply(self.analyze_sentiment)

        # extract the label and score values from the dictionaries
        df['label'] = sentiment_scores.apply(lambda x: x[0]['label'])
        df['score'] = sentiment_scores.apply(lambda x: x[0]['score'])

        return df

    def analyze_emotion(self, text, emo_model=None):
        """Get sentiment of text from passed model. Defaults to distilbert.

        Args:
        - text (str): The text to pass to the model.
        - model (obj) : the predefined HF model object.

        Returns:
        - str: The model response; emotion output.
        """
        if emo_model is None:
            model = self.distilbert_base_uncased_emotion
        elif emo_model == 'roberta':
            model = self.roberta_base_emotion
        elif emo_model == 'distilbert':
            model = self.distilbert_base_uncased_emotion
        else:
            print("available models: 'roberta', 'distilbert'")
        nlp = transformers.pipeline("text-classification",model=model)
        try:
            emotion = nlp(text)
            if emotion[0]['score']<0.10: # i don't want low probability outputs, these generally suck
                emotion = [{'label': 'neutral', 'score': 0.0}] #make it neutral otherwise
        except:
            emotion = [{'label': 'neutral', 'score': 0.0}]
        
        return emotion
    
    
    def get_emotion_features(self, df):
        """Add label and score columns to a dataframe of text based on emotion analysis.

        Args:
        - df (DataFrame obj): The dataframe to pass to the model.

        Returns:
        - DataFrame: The original dataframe with label and score columns added.
        """
        # apply the analyze_sentiment function to the sentiment column
        emo_scores = df['content'].apply(self.analyze_emotion)

        # extract the label and score values from the dictionaries
        df['label'] = emo_scores.apply(lambda x: x[0]['label'])
        df['score'] = emo_scores.apply(lambda x: x[0]['score'])

        return df


    
class Data(Lab):
    def __init__(self):
        super().__init__()
        
    # helper functions
    # note: if using datetime object, can use this function to get the week for an individual tweet
    # note: every python data type handles this slightly differently! Check the type!
    def get_sentiment_stats(self, df):
        # Count the occurrences of each label
        sent_count = df.groupby('label').size().reset_index(name='count')

        # Calculate mean and standard deviation for each label
        sent_mean = df.groupby('label').agg({'score': ['mean', 'std']}).reset_index()
        sent_mean.columns = ['label', 'mean', 'std']

        # Calculate median for each label
        sent_median = df.groupby('label')['score'].median().reset_index(name='median')

        # Calculate minimum and maximum for each label
        sent_min = df.groupby('label')['score'].min().reset_index(name='min')
        sent_max = df.groupby('label')['score'].max().reset_index(name='max')

        # Merge all statistics into a single dataframe
        sent_stats = sent_count.merge(sent_mean
                  , on='label').merge(sent_median
                  , on='label').merge(sent_min
                  , on='label').merge(sent_max
                  , on='label').sort_values(by='count', ascending=False)
        return sent_stats
    
class NetSci(Lab):
    def __init__(self):
        super().__init__()
        
    
    def map_topic_net(self, df, circular=False):

        plt.rcParams['font.family'] = 'font_name'

        G = nx.Graph()

        users = list(df['username'].unique())
        topics = list(df['gpt_normalized_Topic'].unique())

        G.add_nodes_from(users, bipartite=0) # bipartite=0 specifies that these nodes belong to the user partition
        G.add_nodes_from(topics, bipartite=1) # bipartite=1 specifies that these nodes belong to the topic partition


        edges = [(row['username'], row['gpt_normalized_Topic']) for idx, row in df.iterrows()]
        G.add_edges_from(edges)

        if circular==True:
            pos = nx.circular_layout(G)
        else:
            pos = nx.bipartite_layout(G, users)

        net = nx.draw(G, pos=pos, with_labels=True)
        return net, G

