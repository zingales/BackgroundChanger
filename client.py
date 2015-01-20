#!/usr/bin/python
import socket
import sys
import os
from subprocess import Popen

socket_address = ('localhost', 8888)
#TODO get freedback

def sendMessage(message):
    # Create a UDS socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    print 'connecting to %s, %s' % socket_address
    try:
        sock.connect(socket_address)
    except socket.error, msg:

        return False
    try:
        # Send data
        print 'sending "%s"' % message
        sock.sendall(message)
        return True
    finally:
        sock.close()

def handle(command):
    #TODO: check if client already started
    #TODO: figure out why you have to press enter every time for new line
    if command == "start":
        import daemon 
        daemon.load_system().asynch_start()
    else:
        return sendMessage(command)


def thumbUp():
    return handle("thumbsUp")

def thumbDown():
    return handle("thumbsDown")

def next():
    return handle("next")

def update():
    return handle("update")

def main():
    handle(sys.argv[1])

if __name__ == "__main__":
    main()
