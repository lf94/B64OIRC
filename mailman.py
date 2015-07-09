import irc.bot
import irc.strings
import subprocess as os
import threading
import time
import sys

_BOT_SUFFIX = "_mailman"
_COMMAND_PREFIX = ":"
_FREQUENCY = 2

class B64OIRC(irc.bot.SingleServerIRCBot):
    def __init__(self, owner, server, channel, port):
        global _BOT_SUFFIX
        
        self.owner = owner
        self.channel = channel
        self.nickname = owner+_BOT_SUFFIX
        self.target = {}
        self.source = {}
        self.accept = False
        self.locked = False
        self.sink = ""
        self.interpret = True # Set to false if you want no commands interpreted
        self.commands = ["send", "receive", "cancel"]
        
        super().__init__([(server,port)], self.nickname, self.nickname)
        self.connection.set_rate_limit(2)

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
            self.consume(context, event)
        elif self.interpret:
            self.understand(context, event)

    def owner(self, user):
        return user == self.owner

    def understand(self, context, event):
        global _COMMAND_PREFIX
        
        chunks = self.get_args(event)
        for command in self.commands:
            if chunks[0] == _COMMAND_PREFIX+command:
                print(command)
                getattr(self, command)(context,event)

    def get_args(self, event):
        return event.arguments[0].split(" ")

    def get_transmitter(self, event):
        return event.source.split("!")[0]

    def cancel(self, context, event):
        context.privmsg(self.channel, "Cancelled transaction.")
        self.locked = False
        self.target = {}
        self.source = {}

    def send(self, context, event):
        global _BOT_SUFFIX

        chunks = self.get_args(event)
        transmitter = self.get_transmitter(event)

        if len(chunks) != 3:
            context.privmsg(self.channel, "Format: :send <user> <filename>")
            return

        parameters = {'user': chunks[1], 'filename': chunks[2]}

        # The owner is sending data and the bot acknowledges.
        if owner(transmitter):
            self.target['user'] = parameters['user']
            self.target['filename'] = parameters['filename']
            context.privmsg(self.channel, "Target acquired.")

        # Another owner is sending data to our bot, and waits for approval.
        if owner(parameters['user']):
            self.source['user'] = transmitter+_BOT_SUFFIX
            self.source['filename'] = parameters['filename']
            context.privmsg(self.channel, "Awaiting receive.")
        
        context.privmsg(self.channel, "Locked.")
        self.locked = True
        
    def receive(self, context, event):
        # Ensure we have "locked in" to a target or source.
        if not self.locked:
            context.privmsg(self.channel, "Not locked in.")
            return

        transmitter = self.get_transmitter(event)

        # If there is no target, it means we are receiving.
        if transmitter == self.owner and len(self.target) == 0:
            context.privmsg(self.channel, "Owner has accepted.")
            self.accept = True
            return

        # If there is a target, they have accepted and we begin sending.
        if transmitter == self.target['user']:
            os.call("gzip "+self.target['filename']+"; base64 "+self.target['filename']+".gz | tr -d '\n' > out", shell=True)
            with open("out","r") as fh:
                # In the IRC package, client.py sends PRIVMSG %s :%s.
                # We take that, and calculate our max size of the datagram.
                msg_length = (512 - len("PRIVMSG  :")) - len(self.channel);
                data = fh.read(msg_length)
                while data != '':
                    context.privmsg(self.channel, data)
                    data = fh.read(msg_length)

            context.privmsg(self.channel, ":eof")
            self.target = {}
            self.locked = False
 
    def consume(self, context, event):
        transmitter = self.get_transmitter(event)

        if transmitter != self.source['user']:
            return

        chunks = self.get_args(event)
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
        print("Usage: python mailman.py owner server channel\nNote: bash is a bitch, remember # is comment in bash.")
        return
    owner = sys.argv[1]
    server = sys.argv[2]
    channel = sys.argv[3]
    B64OIRC(owner, server, channel, 6667).start()

main()
