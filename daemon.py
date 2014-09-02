#!/usr/bin/python
import socket, sys, os, urllib, urllib2, json, sqlite3, random, imghdr, time, traceback
from subprocess import Popen, PIPE
from crontab import CronTab
from sys import platform
from os.path import join as join_path
import ctypes as windows_functions

scriptDirectory = os.path.dirname(os.path.realpath(__file__))
# server_address = scriptDirectory + 'uds_socket'
server_address = ('localhost', 8888)
images_directory = 'pics'

conn = None
last = time.time()
#TODO: change schema so no two urls or names can be the same
#db schema   name url liked-default-0 seen-defalut-0 ignore-default-0

#requires crontab

MAC_SET_SCRIPT = '''/usr/bin/sqlite3 /Users/G/Library/Application\ Support/Dock/desktoppicture.db<<END
UPDATE data SET value="%s" WHERE ROWID=2;
END
killall Dock'''

MAC_GET_COMMAND= ['/usr/bin/sqlite3', '/Users/G/Library/Application Support/Dock/desktoppicture.db', 'select * from data where rowid=2']


getDesktopImage = None
setDesktopImage = None
# ------------------------------------------------------
# ----------------- OS specific ------------------------
# ------------------------------------------------------

def mac_setDesktopImage(imagePath):
    Popen(MAC_SET_SCRIPT%imagePath, shell=True)

def mac_getDesktopImage():
    p = Popen(MAC_GET_COMMAND, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    uri, _ =  p.communicate()
    name = uri.rstrip().split("/")[-1]
    return name

def linux_getCurrentImageName():
    command ="gsettings get org.gnome.desktop.background picture-uri".split(" ")
    p = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    uri, _ =  p.communicate()
    name = uri.rstrip().split("/")[-1][:-1]
    return name
    #uri is of the form file:///path/to/file

def linux_changeDesktopImage(imagePath):
    command = "gsettings set org.gnome.desktop.background picture-uri file://%s" % imagePath
    command = command.split(" ")
    Popen(command)

def windows_setDesktopImage(imagePath):
    SPI_SETDESKWALLPAPER = 20 
    windows_functions.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, str(imagePath) , 0)

def windows_getDesktopImage():
    return ""

if platform == "linux" or platform == "linux2":
    getDesktopImage = linux_getCurrentImageName
    setDesktopImage = linux_changeDesktopImage
    print "Linux os detected"
elif platform == "darwin":
    getDesktopImage = mac_getDesktopImage
    setDesktopImage = mac_setDesktopImage
    print "Darwin os detected"
elif platform == "win32":
    setDesktopImage = windows_setDesktopImage
    getDesktopImage = windows_getDesktopImage
else:
    print "os not supported"
    sys.exit(1)

# -----------------------------------------------
# ----------------On Startup---------------------
# -----------------------------------------------
def start():
    #connect to db
    global conn
    print 'Connecting To Pics DB'
    conn = sqlite3.connect(join_path(scriptDirectory, 'desktopPics.db'))
    c = conn.cursor()
    c.execute('create table if not exists data (name text, url text primary key, liked integer default 0, seen integer default 0, ignore integer default 0)')
    conn.commit()
    sock = makeDomainSocket()

    dir_path = join_path(scriptDirectory, images_directory)
    if not os.path.exists(dir_path):
        print "Created Image Directory: ", dir_path
        os.makedirs(dir_path)
    #createCronJobs()
    
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

def createCronJobs():
    #start cronjob
    cron_client = CronTab(tabfile='lol.tab')
    iter =  cron_client.find_comment("Desktop Image Changer client")
    try:
        print "Client Cron Task Found"
        iter.next()
    except StopIteration:
        print 'Installing Client Cron Task'
        job = cron_client.new(scriptDirectory + "/client.py dailyUpdate",
            comment="Desktop Image Changer client")
        job.every().dom()
        cron_client.write()

    cron_daemon = CronTab(tabfile='lol.tab')
    iter =  cron_daemon.find_comment("Desktop Image Changer daemon")
    try:
        print "Daemon Cron Task Found"
        iter.next()
    except StopIteration:
        print 'Installing Daemon Cron Task'
        job = cron_daemon.new(scriptDirectory + "/daemon.py &",
            comment="Desktop Image Changer daemon")
        job.every_reboot()
        cron_daemon.write()

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
    print 'Starting up socket listner on(%s, %s)' % server_address
    sock.bind(server_address)

    sock.listen(1)
    return sock


#------------------------------------------------
#------------------Utility-----------------------
#------------------------------------------------

def pullPornImages(subreddit):
    #TODO: handle flickr with beautiful soup
    print "Pulling from ", subreddit
    url = 'failed pulling from subreddit'
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
    print 'Pulling from bing'
    response = urllib2.urlopen('http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US')
    data = json.load(response)
    for image in data['images']:
        url = 'http://www.bing.com' + image['url']
        name =  image['startdate']+ ".jpg"
        downloadImage(url, name)


def downloadImage(url, name):
    #super hack
    name += ".jpg"
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
    # except (urllib.error.HTTPError, urllib.error.URLError) as e:
    except Exception as e:
        print "Exceptino was thrown", e, url
        traceback.format_exc()
        

def genrate_path(name):
    return join_path(scriptDirectory, images_directory, name)

# ------------------------------------------------------
# ----------------- Commands From Client----------------
# ------------------------------------------------------
def handle(command):
    global last
    if command == "thumbsUp":
        thumbsUp(getDesktopImage())
    elif command == "thumbsDown":
        thumbsDown(getDesktopImage())
    elif command == "next":
        next()
    elif command == "dailyUpdate":
        if time.time() - last > 3600:
            next()
            last = time.time()
    elif command == "quit":
        sys.exit(0)
    else:
        print "command %s is not in the protocol" % command

def next():
    #pullBingImages()
    for subreddit in ['waterporn', 'fireporn', 'earthporn', 'cloudporn']:
        pullPornImages(subreddit)
    print 'Done Pulling Images'
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
    setDesktopImage(path)

def thumbsDown(imageName):
    c = conn.cursor()
    c.execute("update data set liked=-1 where name=?",(imageName,))
    conn.commit()
    next()

def thumbsUp(imageName):
    c = conn.cursor()
    c.execute("update data set liked=1 where name=?",(imageName,))
    conn.commit()




if __name__ == "__main__":
    start()
    # path = "/Users/G/Pictures/Desktop/tree.jpg"
    # set_desktop_background(path)
