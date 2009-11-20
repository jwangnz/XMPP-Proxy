#!/usr/bin/env python
 
from __future__ import with_statement
 
import time
import random
 
from twisted.python import log
from twisted.internet import protocol, reactor, threads
from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ
 
from wokkel.xmppim import MessageProtocol, PresenceClientProtocol
from wokkel.xmppim import Presence, AvailablePresence

class XmppProxyHandler(object):

    def __init__(self, component, jid_act_as, jid_proxy_to):
        self.component = component
        self.jid_act_as = jid_act_as
        self.jid_proxy_to = jid_proxy_to

    def translate_jid(self, jid):
        jid = jid.replace("@", "_at_").replace(".", "_")
        if jid.find("/") > 0:
            jid = jid.replace("/", "@" + self.component + "/")
        else:
            jid = jid + "@" + self.component
        return jid

    def untranslate_jid(self, jid):
        return jid.replace("@" + self.component, "").replace("_at_", "@").replace("_", ".")

    def get_forward_jids(self, stanza):
        entity_from = JID(stanza["from"])
        entity_to = JID(stanza["to"])

        if entity_from.userhost() == self.jid_proxy_to:
            new_jid_to = self.untranslate_jid(entity_to.full())
            new_jid_from = self.jid_act_as
        else:
            new_jid_to = self.jid_proxy_to
            new_jid_from = self.translate_jid(entity_from.full())

        return new_jid_to, new_jid_from

class XmppProxyMessageProtocol(MessageProtocol, XmppProxyHandler):

    def __init__(self, component, jid_act_as, jid_proxy_to):
        MessageProtocol.__init__(self)
        XmppProxyHandler.__init__(self, component, jid_act_as, jid_proxy_to)

    def onMessage(self, message):
        self.forward_message(message)

    def forward_message(self, message):
        new_jid_to, new_jid_from = self.get_forward_jids(message)

        message["from"] = new_jid_from
        message["to"] = new_jid_to

        self.send(message)

class XmppProxyPresenceProtocol(PresenceClientProtocol, XmppProxyHandler):

    def __init__(self, component, jid_act_as, jid_proxy_to):
        PresenceClientProtocol.__init__(self)
        XmppProxyHandler.__init__(self, component, jid_act_as, jid_proxy_to)

    def _onPresence(self, presence):
        self.forward_presence(presence)

    def probe(self, jid_to, jid_from):
        presence = Presence(JID(jid_to), "probe")
        presence["from"] = jid_from
        self.send(presence)

    def forward_presence(self, presence):
        type = presence.getAttribute("type", "available")
        if type == "error":
            return

        entity_from = JID(presence["from"])
        entity_to = JID(presence["to"])

        new_jid_to, new_jid_from = self.get_forward_jids(presence)

        presence["to"] = new_jid_to
        presence["from"] = new_jid_from

        self.send(presence)

        if type == "subscribed":
            self.probe(entity_from.full(), entity_to.userhost())

        if type == "available" and entity_from.userhost() != self.jid_proxy_to:
            self.probe(self.jid_proxy_to, new_jid_from)
