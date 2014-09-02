


Desktop Images Updater
=====================

Currently pulls from Cloud/Water/Fire/Earthporn subreddits, and Bing Images of the day

Requires
===========
sqlite3
python-crontab 

install
==============
is hella easy, just run "./daemon.py &" it will add cron jobs such that it will start on boot, 
and update images everyday

to interact with the daemon, just run ./client.py [thumbsUp|thumbsDown|next]. Thumbsdown will also change it to the next image
