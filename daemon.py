#!/usr/bin/python
import socket, sys, os, urllib, urllib2, json, sqlite3, random, imghdr, time, traceback
import datetime
import logging
from os.path import join as join_path
import os_specific

#set up logging
scriptDirectory = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(filename=join_path(scriptDirectory, 'daemon.log'),level=logging.DEBUG)
log = logging.getLogger("daemon")

system = os_specific.load_system()


# server_address = scriptDirectory + 'uds_socket'
server_address = ('localhost', 8888)
images_directory = 'pics'


conn = None
last = time.time()-3600
#TODO: change schema so no two urls or names can be the same
#db schema   name url liked-default-0 priority-defalut-0 ignore-default-0
# priority is the priority of when you want to see it, it will shows images with priority =0 before, priority=1
# 5 means that you've already displayed it.

#TODO: save images with the correct file extension
#TODO: change os importing, such that you don't need libraries that you don't need.

#requires crontab


# (getDesktopImage, setDesktopImage, createCronJobs, asynch_start) = os_specific.load()


# -----------------------------------------------
# ----------------On Startup---------------------
# -----------------------------------------------
def start():
    #connect to db
    global conn
    log.info("===========================")
    log.info('Connecting To Pics DB')
    conn = sqlite3.connect(join_path(scriptDirectory, 'desktopPics.db'))
    c = conn.cursor()
    c.execute('create table if not exists data (name text, url text primary key, liked integer default 0, priority integer default 0, ignore integer default 0)')
    conn.commit()
    sock = makeDomainSocket()
    c.close()

    dir_path = join_path(scriptDirectory, images_directory)
    if not os.path.exists(dir_path):
        log.info("Created Image Directory: %s" % dir_path)
        os.makedirs(dir_path)
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
            handle(data)
        finally:
            # Clean up the connection
            connection.close()



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


#------------------------------------------------
#------------------Utility-----------------------
#------------------------------------------------

def pullPornImages(subreddit):
    #TODO: handle flickr with beautiful soup
    log.info("Pulling from %s" % subreddit)
    url = 'failed on subreddit url'
    try:
        response = urllib2.urlopen("http://www.reddit.com/r/%s/top/.json?sort=top&t=all" % subreddit)
        data = json.load(response)
        for child in data['data']['children']:
            url = child['data']['url']
            name = child['data']['subreddit_id'] + "-" +  child['data']['id']
            downloadImage(url,name, 1)
    except (urllib2.HTTPError, urllib2.URLError) as e:
        # traceback.format_exc()
        log.info(url)
        # print e.message

def pullBingImages():
    log.info('Pulling from Bing image of the day')
    url =  'failed on bing url'
    try:
        response = urllib2.urlopen('http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US')
        data = json.load(response)
        for image in data['images']:
            url = 'http://www.bing.com' + image['url']
            name =  image['startdate']
            downloadImage(url, name, 0)
    except (urllib2.HTTPError, urllib2.URLError) as e:
        log.info("Exception was thrown %s %s" % (e, url))
        # traceback.format_exc()


def downloadImage(url, name, priority):
    cursor = conn.cursor()
    array = cursor.execute("select url from data where url=?", (url,)).fetchall()
    # we've seen this image before
    if len(array) != 0:
        return
    path = genrate_path(name)
    try:
        urllib.urlretrieve(url, path)
        fileExtension = imghdr.what(path)
        if fileExtension in ['jpg',  'jpeg', 'gif', 'png']:
            os.rename(path, path+'.'+fileExtension)
            cursor.execute("INSERT INTO data (name, url, priority) VALUES (?, ?, ?);",
                (name + '.' + fileExtension, url, priority))
            conn.commit()
        else:
            cursor.execute("INSERT INTO data (name, url, ignore) VALUES (?, ?, ?);",
                (name, url, 1))
            os.unlink(path)
    # except (urllib.error.HTTPError, urllib.error.URLError) as e:
    except Exception as e:
        log.info("Exception was thrown %s, %s" % (e, url))
        traceback.format_exc()
    cursor.close()


def genrate_path(name):
    return join_path(scriptDirectory, images_directory, name)

# ------------------------------------------------------
# ----------------- Commands From Client----------------
# ------------------------------------------------------
def handle(command):
    global last
    if command == "thumbsUp":
        thumbsUp(system.getDesktopImage())
    elif command == "thumbsDown":
        thumbsDown(system.getDesktopImage())
    elif command == "next":
        next()
    elif command == "dailyUpdate":
        if time.time() - last > 3600:
            log.info("Running dailyUpdate at %s" % datetime.datetime.now().strftime("%H:%M:%S %d,%m,%y"))
            next()
            last = time.time()
        else:
            log.info("daily update watinging till %d seconds" % (3600-(time.time()-last)))
    elif command == "quit":
        sys.exit(0)
    else:
        log.info("command %s is not in the protocol" % command)
    log.info("Handle Done")

def next():
    pullBingImages()
    for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
        pullPornImages(subreddit)
    log.info('Done Updating Images')
    c = conn.cursor()
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
    conn.commit()
    c.close()
    path = genrate_path(name)
    log.info("changing image")
    system.setDesktopImage(path)

def thumbsDown(imageName):
    c = conn.cursor()
    c.execute("update data set liked=-1,priority=99 where name=?",(imageName,))
    conn.commit()
    log.info("Thumbed Down")
    next()

def thumbsUp(imageName):
    c = conn.cursor()
    c.execute("update data set liked=1 where name=?",(imageName,))
    conn.commit()
    log.info("Thumbed Up")




if __name__ == "__main__":
    start()
    # path = "/Users/G/Pictures/Desktop/tree.jpg"
    # set_desktop_background(path)
