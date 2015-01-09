#!/usr/bin/python
import logging
from os.path import join as join_path
import socket, sys, os, urllib, urllib2, json, sqlite3, random, imghdr, time, traceback
import datetime

scriptDirectory = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(filename=join_path(scriptDirectory, 'daemon.log'),level=logging.DEBUG)

#imports that require logging setup
import os_specific
import img_getters

log = logging.getLogger("daemon")

system = os_specific.load_system()


# server_address = scriptDirectory + 'uds_socket'
server_address = ('localhost', 8888)
images_directory = 'pics'


last = time.time()-3600
#TODO: change schema so no two urls or names can be the same
#db schema   name url liked-default-0 priority-defalut-0 ignore-default-0
# priority is the priority of when you want to see it, it will shows images with priority =0 before, priority=1
# 5 means that you've already displayed it.

#TODO: save images with the correct file extension
#TODO: change os importing, such that you don't need libraries that you don't need.

#requires crontab


def genrate_path(self, name):
      return join_path(scriptDirectory, images_directory, name)

# (getDesktopImage, setDesktopImage, createCronJobs, asynch_start) = os_specific.load()

class ImgDb(object):
  def __init__(self, img_dir_path):
    self.conn = sqlite3.connect(join_path(scriptDirectory, 'desktopPics.db'))
    c = self.conn.cursor()
    c.execute('create table if not exists data (name text, url text primary key, liked integer default 0, priority integer default 0, ignore integer default 0)')
    self.conn.commit()
    c.close()
    self.img_dir_path = img_dir_path

  def url_exist(self, url):
    raise NotImplementedError()

  def downloadImgaes(self, lst):
    '''
    :param lst: list has to be url, name, priority list
    :return:
    '''
    #todo make this do it all in one db connection instead of per image.
    for tup in lst:
      self._downloadImage(**tup)


  def select_image(self):
    c = self.conn.cursor()
    array = []
    count = 0
    while len(array) == 0:
        array = c.execute("select name, rowid from data where priority=? and ignore=0", (count,)).fetchall()
        count+=1
    if count > 5:
        log.info("you have no fresh images")
    selected = random.choice(array)
    name, id = selected
    c.execute("update data set priority=5 where rowid=?", (id,))
    self.conn.commit()
    c.close()
    return name



  def _downloadImage(self,url, name, priority):
      cursor = self.conn.cursor()
      array = cursor.execute("select url from data where url=?", (url,)).fetchall()
      # we've seen this image before
      if len(array) != 0:
          return
      path = join_path(self.img_dir_path, name)
      try:
          urllib.urlretrieve(url, path)
          fileExtension = imghdr.what(path)
          if fileExtension in ['jpg',  'jpeg', 'gif', 'png']:
              os.rename(path, path+'.'+fileExtension)
              cursor.execute("INSERT INTO data (name, url, priority) VALUES (?, ?, ?);",
                  (name + '.' + fileExtension, url, priority))
              self.conn.commit()
          else:
              cursor.execute("INSERT INTO data (name, url, ignore) VALUES (?, ?, ?);",
                  (name, url, 1))
              os.unlink(path)
      # except (urllib.error.HTTPError, urllib.error.URLError) as e:
      except Exception as e:
          log.info("Exception was thrown %s, %s" % (e, url))
          traceback.format_exc()
      cursor.close()

  def thumbsDown(self, imageName):
      c = self.conn.cursor()
      c.execute("update data set liked=-1,priority=99 where name=?",(imageName,))
      self.conn.commit()
      log.info("Thumbed Down")

  def thumbsUp(self, imageName):
      c = self.conn.cursor()
      c.execute("update data set liked=1 where name=?",(imageName,))
      self.conn.commit()
      log.info("Thumbed Up")


def makeDomainSocket():
    # Make sure the socket does not already exist
    # try:
    #     os.unlink(server_address)
    # except OSError:
    #     if os.path.exists(server_address):
    #         raise

    # Create a UDS socket
    sock =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the port
    log.info('Starting up socket listner on(%s, %s)' % server_address)
    sock.bind(server_address)

    sock.listen(1)
    return sock
# -----------------------------------------------
# ----------------On Startup---------------------
# -----------------------------------------------
class daomon(object):
  def __init__(self):
    self.dir_path = join_path(scriptDirectory, images_directory)

    self.db = ImgDb(self.dir_path)
    self.getters = []

  def add_getter(self, getter):
    self.getters.append(getter)

  def run(self):
    #connect to db
    log.info("===========================")
    log.info('Connecting To Pics DB')
    sock = makeDomainSocket()

    if not os.path.exists(self.dir_path):
        log.info("Created Image Directory: %s" % self.dir_path)
        os.makedirs(self.dir_path)
    system.createCronJobs()

    #start socket

    while True:
        # Wait for a connection
        #TODO: when get info from client, handle it and close connection, wait to accept another
        connection, client_address = sock.accept()
        connection.settimeout(None)
        try:
            # Receive the data in small chunks and retransmit it
            data = connection.recv(1024) #YUNO BLOCK!!!!
            log.info('received "%s"' % data)
            if data == "":
                continue
            self.handle(data)
        finally:
            # Clean up the connection
            connection.close()


  # ------------------------------------------------------
  # ----------------- Commands From Client----------------
  # ------------------------------------------------------
  def handle(self, command):
      global last
      if command == "thumbsUp":
          self.db.thumbsUp(system.getDesktopImage())
      elif command == "thumbsDown":
          self.db.thumbsDown(system.getDesktopImage())
          self.next()
      elif command == "next":
          self.next()
      elif command == "dailyUpdate":
          if time.time() - last > 3600:
              log.info("Running dailyUpdate at %s" % datetime.datetime.now().strftime("%H:%M:%S %d,%m,%y"))
              next()
              last = time.time()
          else:
              log.info("daily update waiting till %d seconds" % (3600-(time.time()-last)))
      elif command == "quit":
          sys.exit(0)
      else:
          log.info("command %s is not in the protocol" % command)
      log.info("Handle Done")

  def update(self):
    urls = []
    for getter in self.getters:
      urls.extend(getter.get())
    self.db.downloadImgaes(urls)
    log.info('Done Updating Images')

  def next(self):
    try:
      self.update()
    except as e:
      log.info("Error trying to update")
      log.exception(e)
    name = self.db.select_image()

    path = join_path(self.dir_path, name)
    log.info("changing image")
    system.setDesktopImage(path)


if __name__ == "__main__":
  deamon = daomon()

  deamon.add_getter(img_getters.BingGetter())
  for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
    deamon.add_getter(img_getters.SubredditGetter(subreddit))

  deamon.run()
    # path = "/Users/G/Pictures/Desktop/tree.jpg"
    # set_desktop_background(path)
