


Desktop Images Updater
=====================

An extenable Desktop background "manager". Currently what it does is pull images via URLGetters (look at img_getters.py for specifics), and randomly selects an image based on priority. 


Requires
===========
* sqlite3
* python 2.7
* apscheduler

On Linux it also requires
* python-crontab


Running
==============
The script should install everything it needs when it needs it, as long as you've fufilled the requirements. So running and installing are identical as far as the user is concerned. 

Note: still working on getting the daemon to restart after boot on windows. 

To get started I reccomend running the daemon in the background if you can

on unix type system 'nohup python daemon.py &' should get you up and running. 

on windows running python ./daemon.py will run the deamon (however not in the background)

you can find the log in deamon.log

If you don't like using the command line to thumbsUp|thumbsdown|next your background you can open up the very minimal gui by running gui.py. 
Gui is completely independant of the actual daemon, so feel free to start and stop it as often as you'd like. 

