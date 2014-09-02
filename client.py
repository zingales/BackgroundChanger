#!/usr/bin/python
import socket
import sys
import os

scriptDirectory = os.path.dirname(os.path.realpath(__file__))
# socket_address = scriptDirectory + '/uds_socket'
socket_address = ('localhost', 8888)
print socket_address
def sendMessage(message):
    # Create a UDS socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    print 'connecting to %s, %s' % socket_address
    try:
        sock.connect(socket_address)
    except socket.error, msg:
        print msg
        sys.exit(1)

    try:
        # Send data
        print 'sending "%s"' % message
        sock.sendall(message)
    finally:
        sock.close()

def main():
    sendMessage(sys.argv[1])

if __name__ == "__main__":
    main()
