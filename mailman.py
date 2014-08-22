import irc.bot
import irc.strings
import subprocess as os
import threading
import time
import sys

_BOT_SUFFIX = "_mailman"

class B64OIRC(irc.bot.SingleServerIRCBot):
    def __init__(self, owner, server, channel, port):
        global _BOX_SUFFIX
        self.owner = owner
        self.channel = channel
        self.nickname = owner+_BOT_SUFFIX
        self.target = {}
        self.source = {}
        self.accept = False
        self.locked = False
        self.sink = ""
        self.interpret = True
        self._COMMANDS = ["send", "receive", "cancel"]
        irc.bot.SingleServerIRCBot.__init__(self, [(server,port)], self.nickname, self.nickname)

    def on_welcome(self, context, event):
        context.join(self.channel)

    def on_join(self, context, event):
        pass

    def on_pubmsg(self, context, event):
        self.do(context, event)

    def on_privmsg(self, context, event):
        self.do(context, event)

    def do(self, context, event):
        if self.accept:
            self.eat(context, event)
        else:
            self.understand(context, event)

    def is_owner(self, context, event):
        user = event.source.split("!")[0]
        if(user != self.owner):
            return False
        return True

    def understand(self, context, event):
        if not self.interpret:
            return
        text = event.arguments[0]
        chunks = text.split(" ")
        for command in self._COMMANDS:
            if chunks[0] == ":"+command:
                print(command)
                getattr(self, command)(context,event)

    def get_args(event):
        return event.arguments[0].split(" ")

    def get_transmitter(event):
        return event.source.split("!")[0]

    def send(self, context, event):
        global _BOT_SUFFIX

        chunks = self.get_args(event)
        transmitter = self.get_transmitter(event)

        if len(chunks) != 3:
            context.privmsg(self.channel, "Format: :send <user> <filename>")
            return

        parameters = {'user': chunks[1], 'filename': chunks[2]}
        
        if transmitter == self.owner:
            self.target['user'] = parameters['user']
            self.target['filename'] = parameters['filename']
            context.privmsg(self.channel, "Target acquired.")

        if parameters['user'] == self.owner:
            self.source['user'] = transmitter+_BOX_SUFFIX
            self.source['filename'] = parameters['filename']
            context.privmsg(self.channel, "Awaiting receive.")
        
        context.privmsg(self.channel, "Locked.")
        self.locked = True

    def cancel(self, context, event):
        self.locked = False
        self.target = {}
        self.source = {}
        
    def receive(self, context, event):
        if not self.locked:
            context.privmsg(self.channel, "Not locked in.")
            return

        transmitter = self.get_transmitter(event)

        if transmitter == self.owner and len(self.target) == 0:
            context.privmsg(self.channel, "Owner has accepted.")
            self.accept = True
            return
        
        if transmitter == self.target['user']:
            fileinput = ""
            os.call("gzip "+self.target['filename']+"; base64 "+self.target['filename']+".gz | tr -d '\n' > out", shell=True)
            with open("out","r") as fh:
                data = fh.read()
            
            index = 0
            target = self.channel
            msg_length = 510-len(target)-50
            context.privmsg(target, "File is {0} bytes.".format(len(fileinput)))
            while pos < len(fileinput):
                context.privmsg(target, data[index:index+msg_length])
                pos += msglen
                time.sleep(1)

            context.privmsg(self.channel, ":eof")
            self.target = {}
            self.locked = False
 
    def eat(self, context, event):
        transmitter = self.get_transmitter(event)

        if transmitter != self.source['user']:
            return

        chunks = get_args(event)
        parameters = {'command': chunks[0]}

        if(parameters['command'] == ":eof"):
            context.privmsg(self.channel, "EOF encountered. Writing file.")
            if(len(self.sink) > 0):
                with open("in", "w") as fh:
                    fh.write(self.sink)
                os.call("base64 -d in > "+self.source['filename']+".gz; gunzip "+self.source['filename']+".gz;", shell=True)
                context.privmsg(self.channel, ":complete")
            self.sink = ""
            self.source = {}
            self.accept = False
            self.locked = False
        else:
            data = event.arguments[0]
            self.sink += data

def main():
    if(len(sys.argv) != 4):
        print("Usage: python howard.py username server channel\nNote: bash is a bitch, remember # is comment in bash.")
    your_irc_username = sys.argv[1]
    server = sys.argv[2]
    channel = sys.argv[3]
    B64OIRC(your_irc_username, server, channel, 6667).start()

main()
