import urllib2
import json
import logging

log = logging.getLogger("getters")

class UrlGetter(object):
  '''
  manages getting url.
  '''
  def get(self):
    '''
    gets valid urls
    :return: returns a list of tuples (url, name, priority)
    '''

class BingGetter(UrlGetter):
  def get(self):
    log.info('Pulling from Bing image of the day')
    url =  'failed on bing url'
    try:
      response = urllib2.urlopen('http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US')
      data = json.load(response)
      tups = []
      for image in data['images']:
        url = 'http://www.bing.com' + image['url']
        name = image['startdate']
        tups.append((url, name, 0))
      return tups
    except (urllib2.HTTPError, urllib2.URLError) as e:
      log.info("Exception was thrown %s %s" % (e, url))
        # traceback.format_exc()

class SubredditGetter(UrlGetter):
  def __init__(self, subreddit):
    self.subreddit = subreddit

  def get(self):
    #TODO: handle flickr with beautiful soup
    log.info("Pulling from %s" % self.subreddit)
    url = 'failed on subreddit url'
    try:
      response = urllib2.urlopen("http://www.reddit.com/r/%s/top/.json?sort=top&t=all" % subreddit)
      data = json.load(response)
      tups = []
      for child in data['data']['children']:
        url = child['data']['url']
        name = child['data']['subreddit_id'] + "-" +  child['data']['id']
        tups.append((url,name, 1))
      return tups
    except (urllib2.HTTPError, urllib2.URLError) as e:
      # traceback.format_exc()
      log.info(url)
      # print e.message