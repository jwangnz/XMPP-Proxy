#!/usr/bin/env python
 
from __future__ import with_statement
 
import time

import struct
 
from twisted.python import log
from twisted.internet import protocol, reactor, threads
from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ
 
from wokkel.xmppim import MessageProtocol, PresenceClientProtocol
from wokkel.xmppim import Presence, AvailablePresence

def translate_jid(jid, component):
    return jid.replace("@", "_at_").replace(".", "_")+"@"+component

def untranslate_jid(jid, component):
    return jid.replace("@"+component, "").replace("_at_", "@").replace("_", ".")

class XmppProxyMessageProtocol(MessageProtocol):

    def __init__(self, component, jid_act_as, jid_proxy_to):
        super(XmppProxyMessageProtocol, self).__init__()
        self.component = component
        self.jid_act_as = JID(jid_act_as).full()
        self.jid_proxy_to = JID(jid_proxy_to).userhost()

    def connectionInitialized(self):
        super(XmppProxyMessageProtocol, self).connectionInitialized()
        log.msg("Connected!")

    def connectionLost(self, reason):
        log.msg("Disconnected!")


    def onMessage(self, msg):
        log.msg("chat body message: %s" % msg.toXml())
        self.forward_msg(msg)

    def forward_msg(self, msg):
        entity_from = JID(msg["from"])
        entity_to = JID(msg["to"])

        if entity_from.userhost() == self.jid_proxy_to:
            new_jid_to = untranslate_jid(entity_to.userhost(), self.component)
            new_jid_from = self.jid_act_as
        else:
            new_jid_to = self.jid_proxy_to
            new_jid_from = translate_jid(entity_from.userhost(), self.component)

        msg["from"] = new_jid_from
        msg["to"] = new_jid_to
        self.send(msg)

class XmppProxyPresenceProtocol(PresenceClientProtocol):

    def __init__(self, component, jid_act_as, jid_proxy_to) :
        super(XmppProxyPresenceProtocol, self).__init__()
        self.component = component
        self.jid_act_as = JID(jid_act_as).full()
        self.jid_proxy_to = JID(jid_proxy_to).userhost()

    def _onPresence(self, presence):
        self.forward_presence(presence)

    def forward_presence(self, presence):
        type = presence.getAttribute("type", "available")
        if type == "error":
            log.msg("got error presence: " % presence.toXml())
            return

        entity_from = JID(presence["from"]);
        entity_to = JID(presence["to"]);

        if entity_from.userhost() == self.jid_proxy_to:
            new_jid_to = untranslate_jid(entity_to.userhost(), self.component)
            new_jid_from = self.jid_act_as
        else:
            new_jid_to = self.jid_proxy_to
            new_jid_from = translate_jid(entity_from.userhost(), self.component)

        presence["from"] = new_jid_from
        presence["to"] = new_jid_to
        self.send(presence)

        if type == "unavailable" or type == "subscribed":
            new_presence = Presence(JID(entity_from.userhost()), "probe")
            new_presence["from"] = entity_to.userhost()
            self.send(new_presence)

