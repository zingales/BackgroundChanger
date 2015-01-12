#!/usr/bin/python
import logging
from os.path import join as join_path
import socket, sys, os, urllib, sqlite3, random, imghdr, time, traceback
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
download_on_fetch = True


#TODO: 
#db schema   name url liked-default-0 priority-defalut-0 ignore-default-0
# priority is the priority of when you want to see it, it will shows images with priority =0 before, priority=1
# 5 means that you've already displayed it.

#TODO: create update command (checks for images without changing the image),
# add time stamp to update command
# check to see if the image exists if it doens't not download it (allows for db synchornization)
# create better batched commands
# completely connect and disconnect from the db to allow dropbox to synchornize db

class DBConnection(object):

  def __init__(self, dbimg):
    self.db = dbimg

  def __enter__(self):
    return self.db._connect()

  def __exit__(self ,type, value, traceback):
    self.db._disconnect()

class ImgDb(object):

  def _connect(self):
    if self.deep ==0:
      self.session = self.conn.cursor()
    self.deep+=1
    return self.session

  def _disconnect(self):
    self.deep-=1
    if self.deep ==0:
      self.conn.commit()
      self.session.close()
      self.session = None
    return

  def __init__(self, img_dir_path):

    def gen_connection():
      return sqlite3.connect(join_path(scriptDirectory, 'desktopPics.db'))

    self.conn = gen_connection()

    self.img_dir_path = img_dir_path
    self.deep = 0
    self.session = None
    self.download_on_fetch = True

    with DBConnection(self) as c:
      c.execute('CREATE TABLE IF NOT EXISTS  data (name text, url text primary key, liked integer default 0, priority integer default 0, ignore integer default 0)')
    self.selectedImagePriority = 5

  def url_exist(self, url):
    with DBConnection(self) as cursor:
      array = cursor.execute("SELECT url FROM data WHERE url=?", (url,)).fetchall()
      # we've seen this image before
      return len(array) != 0

  def importURLs(self, lst):
    '''
    :param lst: list has to be url, name, priority list
    :return:
    '''

    with DBConnection(self) as cursor:
      #todo make this do it all in one db connection instead of per image.
      found_one = False
      for tup in lst:
        url, name, priority = tup
        if not self.url_exist(url):
          found_one = True
          self.store_img_url(url, name, priority)
          if self.download_on_fetch:
            self.downloadImage(url, name)
      return found_one

  def select_image(self):
    with DBConnection(self) as c:
      array = []
      count = 0
      while len(array) == 0:
        array = c.execute("SELECT name, url, rowid FROM data WHERE priority=? AND ignore=0", (count,)).fetchall()
        count+=1
      if count > self.selectedImagePriority:
        log.info("You have no fresh images")
      selected = random.choice(array)
      name, url, id = selected
      if not self.downloadImage(url, name):
        raise Exception("error trying to download image: %s" % (url, ))

      c.execute("UPDATE data SET priority=? WHERE rowid=?", (self.selectedImagePriority, id))
      return name

  def store_img_url(self, url, name, priority):
    with DBConnection(self) as cursor:
      cursor.execute("INSERT INTO data (name, url, priority) VALUES (?, ?, ?);",
          (name, url, priority) )
   
  def downloadImage(self, url, name):
    if self.url_exist(url):
      return True
    with DBConnection(self) as cursor:
      path = join_path(self.img_dir_path, name)
      try:
        urllib.urlretrieve(url, path)
        fileExtension = imghdr.what(path)
        if fileExtension in ['jpg',  'jpeg', 'gif', 'png']:
          cursor.execute("UPDATE data SET name=? WHERE url=?;", (name + '.' + fileExtension, url) ) 
          os.rename(path, path+'.'+fileExtension)
        else:
          cursor.execute("UPDATE data SET ignore=? WHERE url=?;", (1, url) )
          os.unlink(path)
          return False
      except Exception as e:
          log.info("Exception was thrown %s, %s" % (e, url))
          traceback.format_exc()
          return False

      return True

  def thumbsDown(self, imageName):
    with DBConnection(self) as c:
      c.execute("UPDATE data SET liked=-1,priority=99 WHERE name=?",(imageName,))
    log.info("Thumbed Down")

  def thumbsUp(self, imageName):
    with DBConnection(self) as c:
      c.execute("UPDATE data SET liked=1 WHERE name=?",(imageName,))
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
class daemon(object):
  def __init__(self):
    self.last = time.time()-3600
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
    try:
      if command == "thumbsUp":
          self.db.thumbsUp(system.getDesktopImage())
      elif command == "thumbsDown":
          self.db.thumbsDown(system.getDesktopImage())
          self.next()
      elif command == "next":
          self.next()
      elif command == "update":
        self.update()
      elif command == "dailyUpdate":
          if time.time() - self.last > 3600:
              log.info("Running dailyUpdate at %s" % datetime.datetime.now().strftime("%H:%M:%S %d,%m,%y"))
              self.next()
              self.last = time.time()
          else:
              log.info("daily update waiting till %d seconds" % (3600-(time.time()-self.last)))
      elif command == "quit":
          sys.exit(0)
      else:
          log.info("command %s is not in the protocol" % command)
      log.info("Handle Done")
    except Exception as e:
      log.info("Error running handle")
      log.exception(e)

  def update(self):
    urls = []
    for getter in self.getters:
      urls.extend(getter.get())
    log.info('Done fetching images')
    self.db.importURLs(urls)
    log.info('Done saving images')

  def next(self):
    try:
      self.update()
    except Exception as e:
      log.info("Error trying to update")
      log.exception(e)
    #change image even if there is no internet
    name = self.db.select_image()

    path = join_path(self.dir_path, name)
    log.info("changing image")
    system.setDesktopImage(path)

if __name__ == "__main__":
  deamon = daemon()

  deamon.add_getter(img_getters.BingGetter())

  for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
    deamon.add_getter(img_getters.SubredditGetter(subreddit))

  #wallbase getter is suuuuuper slow
  deamon.add_getter(img_getters.WallbaseGetter())


  deamon.run()

