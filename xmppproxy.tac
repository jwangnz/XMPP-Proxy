#!/usr/bin/env python

import sys
sys.path.insert(0, "lib/wokkel")
sys.path.insert(0, "lib")

from twisted.application import service
from twisted.internet import task, reactor
from twisted.words.protocols.jabber import jid
from twisted.web import client
from wokkel.component import Component
from wokkel.generic import VersionHandler
from wokkel.keepalive import KeepAlive
from wokkel.disco import DiscoHandler

from xmppproxy import xmpp_protocol
from xmppproxy import config

application = service.Application("XmppProxy")

xmppcomponent = Component(config.CONF.get("xmpp", "host"), config.CONF.getint("xmpp", "port"), config.CONF.get("xmpp", "component"), config.CONF.get("xmpp", "pass"))
xmppcomponent.logTraffic = False

component = config.CONF.get("xmpp", "component")
jid_act_as = config.CONF.get("xmpp", "jid_act_as")
jid_proxy_to = config.CONF.get("xmpp", "jid_proxy_to")

protocols = [xmpp_protocol.XmppProxyMessageProtocol, xmpp_protocol.XmppProxyPresenceProtocol]
for p in protocols:
    handler = p(component, jid_act_as, jid_proxy_to)
    handler.setHandlerParent(xmppcomponent)

VersionHandler("XmppProxy", config.VERSION).setHandlerParent(xmppcomponent)
KeepAlive().setHandlerParent(xmppcomponent)
xmppcomponent.setServiceParent(application)
