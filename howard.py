import irc.bot
import irc.strings
import subprocess as os
import threading
import time

class B64OIRC(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, owner, server, port):
        self.owner = owner
        self.channel = channel
        self.nickname = owner+"_mailman"
        self.target = {}
        self.source = {}
        self.sending = False
        self.accept = False
        self.locked = False
        self.sink = ""
        self.awaiting_confirmation = False
        self.interpret = True
        self._COMMANDS = ["send", "receive", "cancel"]
        self._DATA_URI = "data:application/x-gzip;base64,"
        self._TRUSTED = ["jimmt", "jimmt_mailman", "leeee", "leeee_mailman"]
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
            #context.privmsg(user, self.owner+" is my owner, asswipe; fuck off!")
            return False
        return True

    def get_user(self, event):
        return event.source.split("!")[0]

    def understand(self, context, event):
        if not self.interpret:
            return
        text = event.arguments[0]
        chunks = text.split(" ")
        for command in self._COMMANDS:
            if chunks[0] == ":"+command:
                print(command)
                getattr(self, command)(context,event)

    def send(self, context, event):
        chunks = event.arguments[0].split(" ")
        if len(chunks) != 3:
            context.privmsg(self.channel, "Not enough arguments. Arguments: "+str(chunks))
            return
        user = chunks[1]
        filename = chunks[2]
        
        if self.is_owner(context, event):
            self.target['filename'] = filename
            self.target['user'] = user+"_mailman"
            context.privmsg(self.channel, "Target acquired.")

        if not self.awaiting_confirmation and user == self.owner:
            self.source['user'] = event.source.split("!")[0]+"_mailman"
            self.source['filename'] = filename
            self.awaiting_confirmation = True
            context.privmsg(self.channel, "Awaiting receive.")
            
        context.privmsg(self.channel, "Locked.")
        self.locked = True

    def cancel(self, context, event):
        self.locked = False
        self.awaiting_confirmation = False
        
    def receive(self, context, event):
        if not self.locked:
            context.privmsg(self.channel, "Not locked.")
            return
        user = self.get_user(event)
        context.privmsg(self.channel, user)
        if self.is_owner(context, event):
            context.privmsg(self.channel, "is owner and accepted")
            self.accept = True
            return
        
        if user+"_mailman" == self.target['user']:
            fileinput = ""
            os.call("gzip "+self.target['filename']+"; base64 "+self.target['filename']+".gz | tr -d '\n' > out", shell=True)
            with open("out","r") as fh:
                fileinput = fh.read()
            
            pos = 0
            msglen = 510-len(self._DATA_URI)-len(event.source)-len(event.target)
            while pos < len(fileinput):
                context.privmsg(self.channel, self._DATA_URI+fileinput[pos:pos+msglen])
                pos += msglen
                time.sleep(1)

            context.privmsg(self.channel, ":eof")
            self.target = {}
 
    def eat(self, context, event):
        user = self.get_user(event)
        if user != self.source['user']:
            context.privmsg(self.channel, "No interfering.")
            return
        chunks = event.arguments[0].split(" ")
        if(chunks[0] == ":eof"):
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
                self.awaiting_confirmation = True
        else:
            data = event.arguments[0].split(",")
            if(data[0] == self._DATA_URI[:-1]):
                context.privmsg(self.channel, "Received chunk.")
                self.sink = self.sink + data[1:]


    def quack(self):
        self.start()

def bot_instance(bot):
    threading.Thread(target=bot.start).start()

def main():
    bot_instance(B64OIRC("#b64oirc", "leeee","irc.rizon.net", 6667))
    #time.sleep(5)
    #bot_instance(B64OIRC("#b64oirc", "hrffr", "irc.rizon.net", 6667))
    

main()
