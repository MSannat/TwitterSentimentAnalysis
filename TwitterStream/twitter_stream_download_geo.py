##########################################################################################################
# This is a batch program. Please run this program on terminal as - "twitter_stream_download_geo.py"
# from the folder 'TwitterStream'.
######## python twitter_stream_download_geo.py -q trump -l CA  ###############
######## python twitter_stream_download_geo.py -q trump -l TX  ###############
######## python twitter_stream_download_geo.py -q hillary -l CA  ###############
######## python twitter_stream_download_geo.py -q hillary -l TX  ###############
# The batch program expects two command line arguments: -q for twitter query and -l for location (State abbreviation)
# The first run with the parameters : -q trump -l CA, will produce the list of tweets for the query "trump" in the state "California"
# and write the tweets to file jason/trump_CA.json and store the same to Mongo DB collection "trump_CA"

# Before the batch program is run please configure following:
# Tweepy and PyMongo modules are installed
# A running MongoDB daemon (see readme.txt)
# config.py with Twitter Auth configuration
# Check presence of directory 'json' at the same level as the folder 'TwitterStream'
##########################################################################################################

import tweepy
from tweepy import Stream
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
import time
import argparse
import string
import config
import json
import pymongo


def get_parser():
    """Get parser for command line arguments."""
    parser = argparse.ArgumentParser(description="Twitter Downloader")
    parser.add_argument("-q",
                        "--query",
                        dest="query",
                        help="Query/Filter",
                        default='-')
    parser.add_argument("-l",
                        "--location",
                        dest="location",
                        help="Location/Filter")
    
    return parser


class MyListener(StreamListener):
    """StreamListener for streaming Twitter data."""

    def __init__(self, location, query):
        
        fname = query + '_' + location
        query_fname = format_filename(fname)
        data_dir ='json'
        self.fname = fname
        self.outfile = "../%s/%s.json" % (data_dir, query_fname)
        open("../%s/%s.json" % (data_dir, query_fname), 'w').close()
        mongo_client = pymongo.MongoClient()
        db = mongo_client.twitter_db
        if fname in db.collection_names():
            if ( db[fname].count() != 0 ) :
                #print 'collection already exists'
                db[fname].delete_many({})

    

    def on_data(self, data):
        try:
            mongo_client = pymongo.MongoClient()
            db = mongo_client.twitter_db
            collection = db[self.fname]
            tweet = json.loads(data)
            collection.insert(tweet)
            with open(self.outfile, 'a') as f:
                f.write(data)
                print(data)
                return True
        except BaseException as e:
            print("Error on_data: %s" % str(e))
            time.sleep(5)
        return True

    def on_error(self, status):
        print(status)
        return True


def format_filename(fname):
    """Convert file name into a safe string.

    Arguments:
        fname -- the file name to convert
    Return:
        String -- converted file name
    """
    return ''.join(convert_valid(one_char) for one_char in fname)


def convert_valid(one_char):
    """Convert a character into '_' if invalid.

    Arguments:
        one_char -- the char to convert
    Return:
        Character -- converted char
    """
    valid_chars = "-_.%s%s" % (string.ascii_letters, string.digits)
    if one_char in valid_chars:
        return one_char
    else:
        return '_'

@classmethod
def parse(cls, api, raw):
    status = cls.first_parse(api, raw)
    setattr(status, 'json', json.dumps(raw))
    return status

if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    auth = OAuthHandler(config.consumer_key, config.consumer_secret)
    auth.set_access_token(config.access_token, config.access_secret)
    api = tweepy.API(auth)
    twitter_stream = Stream(auth, MyListener(args.location, args.query.replace (" ", "_")))
    if (args.location == 'CA'):
        twitter_stream.filter( track = [args.query], locations = [-124.63,32.44,-113.47,42.2] )
    elif (args.location == 'TX'):
        twitter_stream.filter( track = [args.query], locations = [-107.31,25.68,-93.25,36.7] )
    else:
        raise ValueError("Please pass either CA or TX as location argument: -l.")

    #texas = [-107.31,25.68,-93.25,36.7]
    #california = [-124.63,32.44,-113.47,42.2]




