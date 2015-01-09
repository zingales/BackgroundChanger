import urllib2, urllib
import json
import logging
from HTMLParser import HTMLParser

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
      return []
        # traceback.format_exc()

class SubredditGetter(UrlGetter):
  def __init__(self, subreddit):
    self.subreddit = subreddit
    self.main_url = "http://www.reddit.com/r/%s/top/.json?sort=top&t=all" % self.subreddit


  def get(self):
    #TODO: handle flickr with beautiful soup
    log.info("Pulling from %s" % self.subreddit)
    try:
      response = urllib2.urlopen(self.main_url)
      data = json.load(response)
      tups = []
      for child in data['data']['children']:
        url = child['data']['url']
        name = child['data']['subreddit_id'] + "-" +  child['data']['id']
        tups.append((url,name, 1))
      return tups
    except (urllib2.HTTPError, urllib2.URLError) as e:
      # traceback.format_exc()
      log.info("failed pulling main url from %s" % self.subreddit)
      return []
      # print e.message

class WallBaseMainParser(HTMLParser, object):
  def __init__(self):
    super(WallBaseMainParser, self).__init__()
    self.tuples = []

  def handle_starttag(self, tag, attrs):
    link = None
    if tag == 'a':
      correct = False
      for name, value in attrs:
        if name == "class" and value == "preview":
          correct = True
        if name == "href":
          link = value
      if correct:
        self.tuples.append(link)


class WallBasePreviewParser(HTMLParser, object):
  def __init__(self):
    super(WallBasePreviewParser, self).__init__()
    self.url = None
  def handle_starttag(self, tag, attrs):
    link = None
    if tag == 'img':
      correct = False
      for name, value in attrs:
        if name == "id" and value == "wallpaper":
          correct = True
        if name == "src":
          link = value
      if correct:
        self.url = "http:" + link

class WallbaseGetter(UrlGetter):
  # TODO learn to get from this url
  def __init__(self):
    #self.main_url = 'http://alpha.wallhaven.cc/search?categories=111&purity=110&ratios=16x9&sorting=favorites&order=desc'
    self.main_url = 'http://alpha.wallhaven.cc/search?categories=111&purity=100&ratios=16x9&sorting=favorites&order=desc'

  def get(self):
    log.info('Pulling from WallHaven')
    f = urllib.urlopen(self.main_url)
    html = f.read()
    p1 = WallBaseMainParser()
    p1.feed(html)
    tuples = []
    for tup in p1.tuples:
      tuples.append(self._get_image_link(tup))
    return tuples


  def _get_image_link(self, img_url):
    name = img_url.split("/")[-1]
    name = "wallhaven-"+name
    f = urllib.urlopen(img_url)
    html = f.read()
    p1 = WallBasePreviewParser()
    p1.feed(html)
    return p1.url, name, 0

if __name__ == '__main__':
  print WallbaseGetter().get()