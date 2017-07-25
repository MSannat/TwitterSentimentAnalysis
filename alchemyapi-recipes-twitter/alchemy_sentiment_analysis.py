#
#  Copyright 2015 AlchemyAI
#

##########################################################################################################
# This is a batch program as provided by IBM Alchemy API client.
# See Article for details: http://www.alchemyapi.com/developers/getting-started-guide/twitter-sentiment-analysis
# This client is customized to work as per the project requirement.
# Run this program from folder "alchemyapi-recipes-twitter" as
########### python alchemy_sentiment_analysis.py 'Trump_TX.json' 250
########### python alchemy_sentiment_analysis.py 'Trump_CA.json' 250
########### python alchemy_sentiment_analysis.py 'Hillary_TX.json' 250
########### python alchemy_sentiment_analysis.py 'Hillary_CA.json' 250
# First argument parameter is the JSON file stored in the JSON folder from the earlier run.
# Second argument parameter is number of tweets for sentiment analysis.
# IBM Alchemy API free account allows for free 1000 call each day .
# This can be divided into four JSON files each with 250 calls to Alchemy API.


import os, sys, string, time, re
import requests, json, urllib, urllib2, base64
import pymongo
from multiprocessing import Pool, Lock, Queue, Manager

def main(search_term, num_tweets):

    # Establish credentials for Twitter and AlchemyAPI
    credentials = get_credentials()
    
    # Get the Twitter bearer token
    auth = oauth(credentials)

    # Pull Tweets down from the Twitter API
    raw_tweets = search(search_term, num_tweets, auth)
    #raw_tweets = search()

    # De-duplicate Tweets by ID
    unique_tweets = dedup(raw_tweets)

    # Enrich the body of the Tweets using AlchemyAPI
    search_target = search_term.rsplit('_', 1)[0]
    enriched_tweets = enrich(credentials, unique_tweets, sentiment_target = search_target)

    # Store data in MongoDB
    collection_name = search_term.rsplit('.json', 1)[0]
    collection_name ="sentiment_%s" % (collection_name)
    store(enriched_tweets, collection_name)

    # Print some interesting results to the screen
    print_results(collection_name)

    return

def get_credentials():
    creds = {}
    creds['consumer_key']    = str()
    creds['consumer_secret'] = str()
    creds['apikey']      = str()

    # If the file credentials.py exists, then grab values from it.
    # Values: "twitter_consumer_key," "twitter_consumer_secret," "alchemy_apikey"
    # Otherwise, the values are entered by the user
    try:
        import credentials
        creds['consumer_key']    = credentials.twitter_consumer_key
        creds['consumer_secret'] = credentials.twitter_consumer_secret
        creds['apikey']          = credentials.alchemy_apikey 
    except:
        print "No credentials.py found"
        creds['consumer_key']    = raw_input("Enter your Twitter API consumer key: ")
        creds['consumer_secret'] = raw_input("Enter your Twitter API consumer secret: ")
        creds['apikey']          = raw_input("Enter your AlchemyAPI key: ")
        
    print "Using the following credentials:"
    print "\tTwitter consumer key:", creds['consumer_key']
    print "\tTwitter consumer secret:", creds['consumer_secret']
    print "\tAlchemyAPI key:", creds['apikey']

    # Test the validity of the AlchemyAPI key
    test_url = "http://access.alchemyapi.com/calls/info/GetAPIKeyInfo"
    test_parameters = {"apikey" : creds['apikey'], "outputMode" : "json"}
    test_results = requests.get(url=test_url, params=test_parameters)
    test_response = test_results.json()

    if 'OK' != test_response['status']:
        print "Oops! Invalid AlchemyAPI key (%s)" % creds['apikey']
        print "HTTP Status:", test_results.status_code, test_results.reason
        sys.exit()

    return creds

def oauth(credentials):

    print "Requesting bearer token from Twitter API"

    try:
        # Encode credentials
        encoded_credentials = base64.b64encode(credentials['consumer_key'] + ':' + credentials['consumer_secret'])        
        # Prepare URL and HTTP parameters
        post_url = "https://api.twitter.com/oauth2/token"
        parameters = {'grant_type' : 'client_credentials'}
        # Prepare headers
        auth_headers = {
            "Authorization" : "Basic %s" % encoded_credentials,
            "Content-Type"  : "application/x-www-form-urlencoded;charset=UTF-8"
            }

        # Make a POST call
        results = requests.post(url=post_url, data=urllib.urlencode(parameters), headers=auth_headers)
        response = results.json()

        # Store the access_token and token_type for further use
        auth = {}
        auth['access_token'] = response['access_token']
        auth['token_type']   = response['token_type']

        print "Bearer token received"
        return auth

    except Exception as e:
        print "Failed to authenticate with Twitter credentials:", e
        print "Twitter consumer key:", credentials['consumer_key']
        print "Twitter consumer secret:", credentials['consumer_secret']
        sys.exit()
        

def search(search_term, num_tweets, auth):
    # This collection will hold the Tweets as they are returned from Twitter
    data_dir ='json'
    fname= "../%s/%s" % (data_dir, search_term)
    collection = []
    #num_tweets =1000
    with open(fname, 'r') as f:
        for line in f:
            status = json.loads(line)
            try:
                #print status
                text = status['text'].encode('utf-8')
                #print text
            
                # Filter out retweets
                if status['retweeted'] == True:
                    continue
                if text[:3] == 'RT ':
                    continue
        
        
                tweet = {}
                if status['geo']:
                    # Configure the fields you are interested in from the status object
                    tweet['text']        = text
                    tweet['id']          = status['id']
                    tweet['time']        = status['created_at'].encode('utf-8')
                    tweet['screen_name'] = status['user']['screen_name'].encode('utf-8')
                    tweet['lat'] = status['geo']['coordinates'][0]
                    tweet['lon'] = status['geo']['coordinates'][1]
                
                
                    collection    += [tweet]
                if len(collection) >= num_tweets:
                    print "Search complete! Found %d tweets" % len(collection)
                    return collection
        
            except KeyError:
                continue
    



def enrich(credentials, tweets, sentiment_target = ''):
    # Prepare to make multiple asynchronous calls to AlchemyAPI
    apikey = credentials['apikey']
    pool = Pool(processes = 10)
    mgr = Manager()
    result_queue = mgr.Queue()
    # Send each Tweet to the get_text_sentiment function
    for tweet in tweets:
        pool.apply_async(get_text_sentiment, (apikey, tweet, sentiment_target, result_queue))

    pool.close()
    pool.join()
    collection = []
    while not result_queue.empty():
        collection += [result_queue.get()]
    
    print "Enrichment complete! Enriched %d Tweets" % len(collection)
    return collection

def get_text_sentiment(apikey, tweet, target, output):

    # Base AlchemyAPI URL for targeted sentiment call
    alchemy_url = "http://access.alchemyapi.com/calls/text/TextGetTextSentiment"
    
    # Parameter list, containing the data to be enriched
    parameters = {
        "apikey" : apikey,
        "text"   : tweet['text'],
        "outputMode" : "json",
        "showSourceText" : 1
        }

    try:

        results = requests.get(url=alchemy_url, params=urllib.urlencode(parameters))
        response = results.json()

    except Exception as e:
        print "Error while calling TextGetTargetedSentiment on Tweet (ID %s)" % tweet['id']
        print "Error:", e
        return

    try:
        if 'OK' != response['status'] or 'docSentiment' not in response:
            print "Problem finding 'docSentiment' in HTTP response from AlchemyAPI"
            print response
            print "HTTP Status:", results.status_code, results.reason
            print "--"
            return

        tweet['sentiment'] = response['docSentiment']['type']
        tweet['score'] = 0.
        if tweet['sentiment'] in ('positive', 'negative'):
            tweet['score'] = float(response['docSentiment']['score'])
        output.put(tweet)

    except Exception as e:
        print "D'oh! There was an error enriching Tweet (ID %s)" % tweet['id']
        print "Error:", e
        print "Request:", results.url
        print "Response:", response

    return

def dedup(tweets):
    used_ids = []
    collection = []
    for tweet in tweets:
        if tweet['id'] not in used_ids:
            used_ids += [tweet['id']]
            collection += [tweet]
    print "After de-duplication, %d tweets" % len(collection)
    return collection

def store(tweets, collection_name):
    # Instantiate your MongoDB client
    mongo_client = pymongo.MongoClient()
    # Retrieve (or create, if it doesn't exist) the twitter_db database from Mongo
    db = mongo_client.twitter_db
    
    if collection_name in db.collection_names():
        if ( db[collection_name].count() != 0 ) :
            #print 'collection already exists'
            db[collection_name].delete_many({})
    
   
    db_tweets = db[collection_name]

    for tweet in tweets:
        db_id = db_tweets.insert(tweet)

    db_count = db_tweets.count()

    print("Tweets stored in MongoDB! collection: %s. Number of documents in twitter_db: %d" % (collection_name, db_count))
   
    return

def print_results(collection_name):

    print ''
    print ''
    print '###############'
    print '#    Stats    #'
    print '###############'
    print ''
    print ''    
    
    db = pymongo.MongoClient().twitter_db
    tweets = db[collection_name]

    num_positive_tweets = tweets.find({"sentiment" : "positive"}).count()
    num_negative_tweets = tweets.find({"sentiment" : "negative"}).count()
    num_neutral_tweets = tweets.find({"sentiment" : "neutral"}).count()
    num_tweets = tweets.find().count()
 

    if num_tweets != sum((num_positive_tweets, num_negative_tweets, num_neutral_tweets)):
        print "Counting problem!"
        print "Number of tweets (%d) doesn't add up (%d, %d, %d)" % (num_tweets, 
                                                                     num_positive_tweets, 
                                                                     num_negative_tweets, 
                                                                     num_neutral_tweets)
        sys.exit()

    most_positive_tweet = tweets.find_one({"sentiment" : "positive"}, sort=[("score", -1)])
    most_negative_tweet = tweets.find_one({"sentiment" : "negative"}, sort=[("score", 1)])

    print "SENTIMENT BREAKDOWN"
    print "Number (%%) of positive tweets: %d (%.2f%%)" % (num_positive_tweets, 100*float(num_positive_tweets) / num_tweets)
    print "Number (%%) of negative tweets: %d (%.2f%%)" % (num_negative_tweets, 100*float(num_negative_tweets) / num_tweets)
    print "Number (%%) of neutral tweets: %d (%.2f%%)" % (num_neutral_tweets, 100*float(num_neutral_tweets) / num_tweets)
    print ""
        
    print "MOST POSITIVE TWEET"
    print "Text: %s" % most_positive_tweet['text']
    print "User: %s" % most_positive_tweet['screen_name']
    print "Time: %s" % most_positive_tweet['time']
    print "Score: %f" % float(most_positive_tweet['score'])
    print ""
    
    print "MOST NEGATIVE TWEET"
    print "Text: %s" % most_negative_tweet['text']
    print "User: %s" % most_negative_tweet['screen_name']
    print "Time: %s" % most_negative_tweet['time']
    print "Score: %f" % float(most_negative_tweet['score'])
    return




    try:
        mean_results = list(tweets.aggregate([{"$group" : {"_id": "$sentiment", "avgScore" : { "$avg" : "$score"}}}]))
        avg_pos_score = mean_results[0]['avgScore']
        print "AVERAGE POSITIVE TWEET SCORE: %f" % float(avg_pos_score)
        if len(mean_results) >1:
            avg_neg_score = mean_results[1]['avgScore']
            print "AVERAGE NEGATIVE TWEET SCORE: %f" % float(avg_neg_score)

    except IndexError:
        print 'no avg score'

    return

if __name__ == "__main__":

    if not len(sys.argv) == 3:
        print "ERROR: invalid number of command line arguments"
        print "SYNTAX: python alchemy_sentiment_analysis.py <JSON_FILE_NAME> <NUM_TWEETS>"
        print "\t<JSON_FILE_NAME> : the JSON file to be used for Sentiment Analysis such as trump_TX.json"
        print "\t<NUM_TWEETS>  : the preferred number of Tweets to pull from Twitter's API"
        sys.exit()

    else:
        main(sys.argv[1], int(sys.argv[2]))
