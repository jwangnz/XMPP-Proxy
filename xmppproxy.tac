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

j = jid.internJID(config.CONF.get("xmpp", "jid"))
proxy_to = jid.internJID(config.CONF.get("xmpp", "proxy_to"))
resource = config.CONF.get("xmpp", "resource")
component = config.CONF.get("xmpp", "component")
xmppcomponent = Component(config.CONF.get("xmpp", "host"), config.CONF.getint("xmpp", "port"), config.CONF.get("xmpp", "component"), config.CONF.get("xmpp", "pass"))
xmppcomponent.logTraffic = True

protocols = [xmpp_protocol.XmppProxyMessageProtocol, xmpp_protocol.XmppProxyPresenceProtocol]
for p in protocols:
    handler = p(component, j, proxy_to, resource)
    handler.setHandlerParent(xmppcomponent)

VersionHandler("XmppProxy", config.VERSION).setHandlerParent(xmppcomponent)
KeepAlive().setHandlerParent(xmppcomponent)
xmppcomponent.setServiceParent(application)
