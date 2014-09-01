#!/usr/bin/python
import socket, sys, os, urllib2, json, sqlite3, urllib, random, imghdr, time, traceback
from subprocess import Popen, PIPE
from crontab import CronTab

server_address = './uds_socket'
images_directory = 'pics'
currentDirectory = os.getcwd()
conn = None
last = time.time()
#TODO: change schema so no two urls or names can be the same
#db schema   name url liked-default-0 seen-defalut-0 ignore-default-0

# -----------------------------------------------
# ----------------On Startup---------------------
# -----------------------------------------------
def start():
    #connect to db
    global conn
    print 'connecting to db'
    conn = sqlite3.connect('/home/evan/Desktop/playground/Gshit/desktopPics.db')
    c = conn.cursor()
    c.execute('create table if not exists data (name text, url text primary key, liked integer default 0, seen integer default 0, ignore integer default 0)')
    conn.commit()
    sock = makeDomainSocket()

    #start cronjob
    cron = CronTab()
    scriptDirectory = os.path.dirname(os.path.realpath(__file__))
    iter =  cron.find_comment("desktop image crontab")
    try:
        iter.next()
    except StopIteration:
        print 'making new cronjob'
        job = cron.new(scriptDirectory + "/client.py dailyUpdate",
            comment="desktop image crontab")
        job.day.every(1)
        cron.write()
    #start socket

    while True:
        # Wait for a connection
        #TODO: when get info from client, handle it and close connection, wait to accept another
        connection, client_address = sock.accept()
        connection.settimeout(None)
        try:
            # Receive the data in small chunks and retransmit it
            data = connection.recv(1024) #YUNO BLOCK!!!!
            print 'received "%s"' % data
            if data == "":
                continue
            handle(data)
        finally:
            # Clean up the connection
            connection.close()


def makeDomainSocket():
    # Make sure the socket does not already exist
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    # Create a UDS socket
    sock =  socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # Bind the socket to the port
    print 'starting up on %s' % server_address
    sock.bind(server_address)

    sock.listen(1)
    return sock


#------------------------------------------------
#------------------Utility-----------------------
#------------------------------------------------

def pullPornImages(subreddit):
    #TODO: handle flickr with beautiful soup
    url = 'Not Defined'
    try:
        response = urllib2.urlopen("http://www.reddit.com/r/%s/top/.json?sort=top&t=all" % subreddit)
        data = json.load(response)
        for child in data['data']['children']:
            url = child['data']['url']
            name = child['data']['subreddit_id'] + "-" +  child['data']['id']
            downloadImage(url,name)
    except urllib2.HTTPError as e:
        traceback.format_exc()
        print url
        print e.message

def pullBingImages():
    print 'pullBingImages()'
    response = urllib2.urlopen('http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US')
    data = json.load(response)
    for image in data['images']:
        url = 'http://www.bing.com' + image['url']
        name =  image['startdate']+ ".jpg"
        downloadImage(url, name)


def downloadImage(url, name):
    cursor = conn.cursor()
    array = cursor.execute("select url from data where url=?", (url,)).fetchall()
    # we've seen this image before
    if len(array) != 0:
        return
    path = genrate_path(name)
    try:
        urllib.urlretrieve(url, path)
        if imghdr.what(path) in ['jpg',  'jpeg', 'gif', 'png']:
            cursor.execute("INSERT INTO data (name, url) VALUES (?, ?);",
                (name, url))
            conn.commit()
        else:
            cursor.execute("INSERT INTO data (name, url, ignore) VALUES (?, ?, ?);",
                (name, url, 1))
            os.unlink(path)
    except (urlib.error.HTTPError, urlib.error.URLError) as e:
        traceback.format_exc()
        print url
        print e


def genrate_path(name):
    return images_directory +"/"+name

# ------------------------------------------------------
# ----------------- Commands From Client----------------
# ------------------------------------------------------
def handle(command):
    global last
    if command == "thumbsUp":
        thumbsUp(linux_getCurrentImageName())
    elif command == "thumbsDown":
        thumbsDown(linux_getCurrentImageName())
    elif command == "next":
        next()
    elif command == "dailyUpdate":
        if time.time() - last > 3600:
            next()
            last = time.time()

    else:
        print "command %s is not in the protocol" % command

def next():
    #pullBingImages()
    for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
        pullPornImages(subreddit)
    print 'pulled images'
    c = conn.cursor()
    array = c.execute("select name, rowid from data where seen=0 and ignore=0").fetchall()
    if len(array) == 0:
        print 'you have no fresh images :('
        return
    selected = random.choice(array)
    name, id = selected
    c.execute("update data set seen=1 where rowid=?", (id,))
    conn.commit()
    path = genrate_path(name)
    linux_changeDesktopImage(path)

def thumbsDown(imageName):
    c = conn.cursor()
    c.execute("update data set liked=-1 where name=?",(imageName,))
    conn.commit()
    next()

def thumbsUp(imageName):
    c = conn.cursor()
    c.execute("update data set liked=1 where name=?",(imageName,))
    conn.commit()


# ------------------------------------------------------
# ----------------- OS specific ------------------------
# ------------------------------------------------------
def linux_getCurrentImageName():
    command ="gsettings get org.gnome.desktop.background picture-uri".split(" ")
    p = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    uri, _ =  p.communicate()
    name = uri.rstrip().split("/")[-1][:-1]
    return name
    #uri is of the form file:///path/to/file

def linux_changeDesktopImage(imagePath):
    imagePath = currentDirectory + "/" + imagePath
    command = "gsettings set org.gnome.desktop.background picture-uri file://%s" % imagePath
    command = command.split(" ")
    Popen(command)


def main():
    start()

if __name__ == "__main__":
    start()
