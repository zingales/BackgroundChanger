import os
from sys import platform, exit
from os.path import join as join_path
from subprocess import Popen, PIPE
import logging

scriptPath = os.path.dirname(os.path.realpath(__file__))
scriptDirectory = os.path.basename(scriptPath)
log = logging.getLogger("os_specific")


class System(object):

  def createCronJobs(self):
    pass

  def setDesktopImage(self, image):
    pass

  def getDesktopImage(self):
    pass

  def async_start(self):
    pass


class OSX(System):

  ClientXML = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>desktopChanger.client</string>
	<key>ProgramArguments</key>
	<array>
		<string>%s</string>
		<string>dailyUpdate</string>
	</array>
	<key>StartCalendarInterval</key>
	<dict>
		<key>Hour</key>
		<integer>0</integer>
		<key>Minute</key>
		<integer>0</integer>
	</dict>
</dict>
</plist>'''

  ServerXML = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>desktopChanger.server</string>
	<key>ProgramArguments</key>
	<array>
		<string>%s</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
</dict>
</plist>'''

  MAC_SET_SCRIPT = '''/usr/bin/sqlite3 /Users/G/Library/Application\ Support/Dock/desktoppicture.db<<END
UPDATE data SET value="%s" WHERE ROWID=2;
END
killall Dock'''

  MAC_GET_COMMAND= ['/usr/bin/sqlite3', '/Users/G/Library/Application Support/Dock/desktoppicture.db',
                    'select * from data where rowid=2']

  def __init__(self):
    self.luanchdPath = os.path.expanduser("~/Library/LaunchAgents")
    self.clientPath = join_path(self.luanchdPath, "DesktopChangerClient.plist")
    self.serverPath = join_path(self.luanchdPath, "DesktopChangerServer.plist")

  def createCronJobs(self):
    #create cron jobs that doen't exist
    if not os.path.exists(self.clientPath):
      log.info("Creating Client Agent")
      with open(self.clientPath, 'w') as client:
        client.write(self.ClientXML % join_path(scriptPath, "client.py"))
      os.chmod(self.clientPath, 0644)
    if not os.path.exists(self.serverPath):
      log.info("Creating Server Agent")
      with open(self.serverPath, 'w') as server:
        server.write(self.ServerXML % join_path(scriptPath, "daemon.py"))
      os.chmod(self.serverPath, 0644)

    #launch cron jobs
    Popen(['launchctl','load', self.clientPath])

  def setDesktopImage(self,imagePath):
    Popen(self.MAC_SET_SCRIPT%imagePath, shell=True)
    log.info("desktop image set")

  def getDesktopImage(self):
    p = Popen(self.MAC_GET_COMMAND, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    uri, _ =  p.communicate()
    name = uri.rstrip().split("/")[-1]
    return name

  def async_start(self):
    # make sure the neccisary plist are there
    self.createCronJobs()
    serverPath = join_path(self.luanchdPath, "DesktopChangerServer.plist")
    Popen(['launchctl', 'load', serverPath])


class WIN32(System):
  import ctypes as windows_functions

  def __init__(self):
    self.lastImage = "unknown"
    pass

  def createCronJobs(self):
    if not os.path.exists(join_path(scriptPath, 'client.bat')):
      log.info("Generating client.bat, please schedule a daily task for this batch file")
      with open('client.bat', 'w') as f:
        f.write("python "+join_path(scriptPath, 'client.py') +" dailyUpdate")
    if not os.path.exists(join_path(scriptPath, 'daemon.bat')):
      log.info("Generating daemon.bat, please schedule a task to run on boot for this batch file")
      with open('daemon.bat', 'w') as f:
        f.write("start /B python "+join_path(scriptPath, 'daemon.py'))

  def setDesktopImage(self, imagePath):
    self.lastImage = imagePath
    SPI_SETDESKWALLPAPER = 20
    self.windows_functions.windll.user32.SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, str(imagePath) , 0)

  def getDesktopImage(self):
    return self.lastImage

  def async_start(self):
    pass


class Linux(System):
  def __init__(self):
    pass

  from crontab import CronTab

  def getCurrentImageName(self):
    command ="gsettings get org.gnome.desktop.background picture-uri".split(" ")
    p = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    uri, _ =  p.communicate()
    name = uri.rstrip().split("/")[-1][:-1]
    return name
    #uri is of the form file:///path/to/file

  def changeDesktopImage(self,imagePath):
    command = "gsettings set org.gnome.desktop.background picture-uri file://%s" % imagePath
    command = command.split(" ")
    Popen(command)

  def createCronJobs(self):
    #start cronjob
    cron_client = self.CronTab()
    iter =  cron_client.find_comment("Desktop Image Changer client")
    try:
      log.info("Client Cron Task Found")
      iter.next()
    except StopIteration:
      log.info('Installing Client Cron Task')
      job = cron_client.new(scriptPath+ "/client.py dailyUpdate",
        comment="Desktop Image Changer client")
      job.every().dom()
      cron_client.write()

    cron_daemon = self.CronTab()
    iter =  cron_daemon.find_comment("Desktop Image Changer daemon")
    try:
      log.info("Daemon Cron Task Found")
      iter.next()
    except StopIteration:
      log.info('Installing Daemon Cron Task')
      job = cron_daemon.new(scriptPath+ "/daemon.py &",
        comment="Desktop Image Changer daemon")
      job.every_reboot()
      cron_daemon.write()

  def async_start(self):
    Popen(('python %s &' %  join_path(scriptDirectory, 'daemon.py')).split(' '))




def load_system():

  if platform == "darwin":
    log.info("Darwin os detected")
    return OSX()

  elif platform == "win32":
    log.info("Windows OS detected")
    return WIN32()

  elif platform == "linux" or platform == "linux2":
    log.info("linux os detected")
    return Linux()
  else:
    log.info("os not supported")
    exit(1)
