import urllib2, urllib
import json
import logging
from HTMLParser import HTMLParser
from collections import namedtuple

ImgInfo = namedtuple('ImgInfo', 'url name priority source')

log = logging.getLogger("getters")

class UrlGetter(object):

  def __init__(self, name, priority):
    self.priority = priority
    self.name = name


  '''
  manages getting url.
  '''
  def get(self):
    '''
    gets valid urls
    :return: returns a list of tuples (url, name, priority)
    '''

class BingGetter(UrlGetter):

  def __init__(self, priority):
    super(BingGetter, self).__init__("Bing", priority)
    

  def get(self):
    log.debug('Pulling from Bing image of the day')
    url =  'failed on bing url'
    try:
      response = urllib2.urlopen('http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US')
      data = json.load(response)
      tups = []
      for image in data['images']:
        url = 'http://www.bing.com' + image['url']
        name = 'Bing-'+image['startdate']
        # tups.append((url, name, self.priority))
        info = ImgInfo(url, name, self.priority, self.name)
        tups.append(info)
      return tups
    except (urllib2.HTTPError, urllib2.URLError) as e:
      log.info("Exception was thrown %s %s" % (e, url))
      return []
        # traceback.format_exc()

class SubredditGetter(UrlGetter):
  def __init__(self, subreddit, priority):
    super(SubredditGetter, self).__init__(subreddit, priority)
    self.subreddit = subreddit
    self.main_url = "http://www.reddit.com/r/%s/top/.json?sort=top&t=all" % self.subreddit


  def get(self):
    #TODO: handle flickr with beautiful soup
    log.debug("Pulling from %s" % self.subreddit)
    try:
      response = urllib2.urlopen(self.main_url)
      data = json.load(response)
      tups = []
      for child in data['data']['children']:
        url = child['data']['url']
        name = child['data']['subreddit_id'] + "-" +  child['data']['id']
        info = ImgInfo(url, name, self.priority, self.subreddit)
        tups.append(info)
      return tups
    except (urllib2.HTTPError, urllib2.URLError) as e:
      # traceback.format_exc()
      log.info("failed pulling main url from %s" % self.subreddit)
      return []
      # print e.message

def get_html(url):
  header = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5'}
  return urllib2.urlopen(urllib2.Request(url, None, header)).read()

class WallbaseGetter(UrlGetter):
  # TODO learn to get from this url

  class WallBaseMainParser(HTMLParser, object):
    def __init__(self):
      super(WallbaseGetter.WallBaseMainParser, self).__init__()
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
      super(WallbaseGetter.WallBasePreviewParser, self).__init__()
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

  def __init__(self, priority):
    super(WallbaseGetter, self).__init__("wallhaven", priority)
    #self.main_url = 'http://alpha.wallhaven.cc/search?categories=111&purity=110&ratios=16x9&sorting=favorites&order=desc'
    self.main_url = 'http://alpha.wallhaven.cc/search?categories=111&purity=100&sorting=favorites&order=desc&page=1'

  def get(self):
    log.debug('Pulling from WallHaven')
    html = get_html(self.main_url)
    # print "this html i got from main website", html
    p1 = WallbaseGetter.WallBaseMainParser()
    p1.feed(html)
    tuples = []
    for tup in p1.tuples:
      tuples.append(self._get_image_link(tup))
    return tuples

  def _get_image_link(self, img_url):
    name = img_url.split("/")[-1]
    name = "wallhaven-"+name
    html = get_html(img_url)
    p1 = WallbaseGetter.WallBasePreviewParser()
    p1.feed(html)
    return ImgInfo(p1.url, name, self.priority, self.name)

#simple desktops
#http://simpledesktops.com/browse/1/

class SimpleDesktopGetter(UrlGetter):

  class SimpleDesktopParser(HTMLParser, object):
    def __init__(self):
      super(SimpleDesktopGetter.SimpleDesktopParser, self).__init__()
      self.tuples = []

    def handle_starttag(self, tag, attrs):
      if tag == 'img':
        for name, value in attrs:
          if name == "src" and value.startswith('http://static.simpledesktops.com/uploads/desktops/'):
            self.tuples.append(value)

  def __init__(self, priority):
    super(SimpleDesktopGetter, self).__init__("SimpleDesktop", priority)
    self.main_url = 'http://simpledesktops.com/browse/1/'

  def get(self):
    log.debug('Pulling from SimpleDesktop')
    html = get_html(self.main_url)
    p1 = SimpleDesktopGetter.SimpleDesktopParser()
    tuples = []
    p1.feed(html)
    for link in p1.tuples:
      elms = link.split(".")
      elms = elms[:-2]
      name = 'SimpleDesktop-'+elms[-2].split("/")[-1]
      url = ".".join(elms)
      info = ImgInfo(url, name, self.priority, self.name)
      tuples.append(info)
    return tuples


if __name__ == '__main__':
  print SimpleDesktopGetter(1).get()