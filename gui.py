#!/usr/bin/python

import Tkinter
import client


 # if command == "thumbsUp":
 #        self.db.thumbsUp(system.getDesktopImage())
 #      elif command == "thumbsDown":
 #        self.db.thumbsDown(system.getDesktopImage())
 #        self.next()
 #      elif command == "next":
 #        self.next()
 #      elif command == "update":

class DesktopGui(Tkinter.Tk):
    def __init__(self,parent):
        Tkinter.Tk.__init__(self,parent)
        self.parent = parent
        # self.overrideredirect(1)
        self.resizable(0,0)
        self.initialize()

    def initialize(self):
        self.grid()

        button = Tkinter.Button(self,text=u"Thumb Up", command=self.thumbUp)
        button.grid(column=1,row=0)

        button = Tkinter.Button(self,text=u"Next", command=self.next)
        button.grid(column=2,row=0)

        button = Tkinter.Button(self,text=u"Thumb Down", command=self.thumbDown)
        button.grid(column=3,row=0)



    def thumbUp(self):
    	client.handle("thumbsUp")

    def thumbDown(self):
    	client.handle("thumbsDown")

    def next(self):
    	client.handle("next")

    def update(self):
    	client.handle("update")

if __name__ == "__main__":
    app = DesktopGui(None)
    app.title('Desktop Changer')
    app.mainloop()
