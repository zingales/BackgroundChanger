#!/usr/local/bin/python
import logging
from os.path import join as join_path
import socket, sys, os, urllib, sqlite3, random, imghdr, time, traceback
import datetime
from apscheduler.schedulers.background import BackgroundScheduler


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

def downloadImage(url, path):
  urllib.urlretrieve(url, path)

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
      self.conn = self.gen_connection()
      self.session = self.conn.cursor()
    self.deep+=1
    return self.session

  def _disconnect(self):
    self.deep-=1
    if self.deep ==0:
      self.conn.commit()
      self.session.close()
      self.conn.close()
      self.session = None
    return

  def __init__(self, img_dir_path):

    def gen_connection():
      return sqlite3.connect(join_path(scriptDirectory, 'desktopPics.db'))

    self.gen_connection = gen_connection

    self.img_dir_path = img_dir_path
    self.deep = 0
    self.session = None
    self.download_on_fetch = True

    with DBConnection(self) as c:
      c.execute('CREATE TABLE IF NOT EXISTS  data (name text, url text primary key, liked integer default 0, priority integer default 0, ignore integer default 0, source text)')
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
      count = 0
      for info in lst:
        if not self.url_exist(info.url):
          count+=1
          self.store_img_url(info)
          if self.download_on_fetch:
            self.guaranteeImage(info.url, info.name)
      return count

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
      if not self.guaranteeImage(url, name):
        raise Exception("error trying to download image: %s" % (url, ))

      c.execute("UPDATE data SET priority=? WHERE rowid=?", (self.selectedImagePriority, id))
      return name

  def get_valid_images(self):
    with DBConnection(self) as cursor:
      array = cursor.execute("SELECT name, url FROM data WHERE ignore=0 and liked!=-1", tuple() ).fetchall()
      return array


  def store_img_url(self, info):
    assert instanceof(info, img_getters.ImgInfo)
    # url, name, priority):
    with DBConnection(self) as cursor:
      cursor.execute("INSERT INTO data (name, url, priority, source) VALUES (?, ?, ?, ?);",
          (info.name, info.url, info.priority, info.source) )
 
  def guaranteeImage(self, url, name):
    path = join_path(self.img_dir_path, name)
    if os.path.exists(path):
      return True
    with DBConnection(self) as cursor:
      try:
        downloadImage(url, path)
        fileExtension = imghdr.what(path)
        if fileExtension in ['jpg',  'jpeg', 'gif', 'png']:
          cursor.execute("UPDATE data SET name=? WHERE url=?;", (name + '.' + fileExtension, url) ) 
          os.rename(path, path+'.'+fileExtension)
        else:
          log.info("found bad image at " + url)
          cursor.execute("UPDATE data SET ignore=? WHERE url=?;", (1, url) )
          os.unlink(path)
          return False
      except Exception as e:
          log.info("Exception was thrown %s, %s" % (e, url))
          traceback.format_exc()
          return False

      return True

  def info(self, imageName):
    with DBConnection(self) as c:
      array = c.execute("SELECT url, liked, source, priority FROM data WHERE name=?", (imageName,) ).fetchall()
      url, liked , source, priority= array[0]
      log.info("info about image %s : source=%s, liked=%s, url=%s, priority=%s" % (imageName, source, liked, priority, url) )

  def thumbsDown(self, imageName):
    with DBConnection(self) as c:
      c.execute("UPDATE data SET liked=-1,priority=99 WHERE name=?",(imageName,))
    log.info("Thumbed Down")

  def thumbsUp(self, imageName):
    with DBConnection(self) as c:
      c.execute("UPDATE data SET liked=1 WHERE name=?",(imageName,))
    log.info("Thumbed Up")

def makeDomainSocket():
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
    self.updateInterval = 3600 * 10
    self.nextInterval = 3600*24
    #in the past when the computer woke from sleep it would fire alot of missed scheduled tasks
    # this is coalesce them all into one
    self.cooldown = min(1800, self.updateInterval, self.nextInterval)
    self.lastUpdate = time.time()-self.cooldown
    self.lastNext = time.time()-self.cooldown
    self.dir_path = join_path(scriptDirectory, images_directory)
    self.db = ImgDb(self.dir_path)
    self.getters = []
    self.scheduler = BackgroundScheduler()

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

    #add update tasks
    self.scheduler.add_job(self.next, 'interval', 
      seconds=self.nextInterval, id='update job', coalesce=True, max_instances=1)
    self.scheduler.add_job(self.update, 'interval', 
      seconds=self.updateInterval, id='next job', coalesce=True, max_instances=1)
    
    log.info("starting scheduler")
    self.scheduler.start()    

    #start socket
    while True:
        # Wait for a connection
        #TODO: when get info from client, handle it and close connection, wait to accept another
        connection, client_address = sock.accept()
        connection.settimeout(None)
        try:
            # Receive the data in small chunks and retransmit it
            data = connection.recv(1024) #YUNO BLOCK!!!!
            if data == "":
                continue
            log.debug('received "%s"' % data)
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
      elif command == "info":
        self.db.info(system.getDesktopImage())
      elif command == "next":
        self.next()
      elif command == "update":
        self.update()
      elif command == "forceDownload":
        self.forceDownload()
      elif command == "quit":
        log.info("quitting now")
        self.scheduler.shutdown()
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
      log.debug('Done fetching from ' + getter.name)
      if not self.db.importURLs(urls):
        log.debug('No fresh images from ' + getter.name)
    log.info('Done saving images')

  def forceDownload(self):
    #download all valid images in database
    log.info("getting all images in db")
    for name, url in self.db.get_valid_images():
      self.db.guaranteeImage(url, name)



  def next(self):
    #change image even if there is no internet
    name = self.db.select_image()

    path = join_path(self.dir_path, name)
    log.info("changing image")
    system.setDesktopImage(path)

if __name__ == "__main__":
  deamon = daemon()

  deamon.add_getter(img_getters.BingGetter(3))

  for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
    deamon.add_getter(img_getters.SubredditGetter(subreddit, 2))

  #wallbase getter is suuuuuper slow
  deamon.add_getter(img_getters.WallbaseGetter(0))

  deamon.add_getter(img_getters.SimpleDesktopGetter(1))


  deamon.run()



