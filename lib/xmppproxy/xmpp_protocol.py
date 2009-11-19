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


CHATSTATE_NS = 'http://jabber.org/protocol/chatstates'

message_conn = None
presence_conn = None
roster_conn = None

class ComponentPresence(domish.Element):
    def __init__(self, entity, to=None, type=None):
        domish.Element.__init__(self, (None, "presence"))
        if type:
            self["type"] = type

        self["from"] = entity.userhost() 

        if to is not None:
            self["to"] = to.full()

class ComponentAvailablePresence(ComponentPresence):
    def __init__(self, entity, to=None, show=None, statuses=None, priority=0):
        super(ComponentAvailablePresence, self).__init__(entity, to=to, type=None)


        if show in ['away', 'xa', 'chat', 'dnd']:
            self.addElement('show', content=show)

        if statuses is not None:
            for lang, status in statuses.iteritems():
                s = self.addElement('status', content=status)
                if lang:
                    s[(NS_XML, "lang")] = lang

        if priority != 0:
            self.addElement('priority', content=unicode(int(priority)))

class XmppProxyMessageProtocol(MessageProtocol):

    def __init__(self, component, jid_act_as, jid_proxy_to, resource):
        super(XmppProxyMessageProtocol, self).__init__()
        self.component = component
        self.jid_act_as = jid_act_as.full()
        self.jid_proxy_to = jid_proxy_to.userhost()
        self.resource = resource

    def connectionInitialized(self):
        super(XmppProxyMessageProtocol, self).connectionInitialized()
        log.msg("Connected!")

        global message_conn
        message_conn = self

    def connectionLost(self, reason):
        log.msg("Disconnected!")

        global message_conn
        if message_conn == self:
            message_conn = None


    def typing_notification(self, jid):
        """Send a typing notification to the given jid."""
 
        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = self.jid_act_as
        # msg.addElement((CHATSTATE_NS, 'composing'))
        self.send(msg)

    def create_message(self):
        msg = domish.Element((None, "message"))
        # msg.addElement((CHATSTATE_NS, 'active'))
        return msg

    def send_plain(self, jid, from_jid, content):
        msg = self.create_message()
        msg["to"] = jid
        msg["from"] = from_jid
        msg["type"] = 'chat'
        #msg.addElement("body", content=content)
        msg.addElement("body", content=content)
 
        self.send(msg)
 
    def send_html(self, jid, body, html):
        msg = self.create_message()
        msg["to"] = jid
        msg["from"] = self.jid_act_as
        msg["type"] = 'chat'
        html = u"<html xmlns='http://jabber.org/protocol/xhtml-im'><body xmlns='http://www.w3.org/1999/xhtml'>"+unicode(html)+u"</body></html>"
        msg.addRawXml(u"<body>" + body + u"</body>")
        msg.addRawXml(unicode(html))
 
        self.send(msg)

    def onError(self, msg):
        log.msg("Error received for %s: %s" % (msg['from'], msg.toXml()))

    def onMessage(self, msg):
        log.msg("chat body message: %s" % msg.toXml())
        try:
            self.__onMessage(msg);
        except KeyError:
            log.err()
        except UnicodeEncodeError:
            log.err()

    def __onMessage(self, msg):
        if msg.getAttribute("type") == 'chat' and hasattr(msg, "body") and msg.body:
            from_entity = JID(msg["from"])
            to_entity = JID(msg["to"])
            if from_entity.userhost() == self.jid_proxy_to:
                to_jid = to_entity.userhost().replace("@"+self.component, "").replace("_at_", "@").replace("_", ".")
                self.send_plain(to_jid, self.jid_act_as, unicode(msg.body))
            else:
                from_jid = from_entity.userhost().replace("@", "_at_").replace(".", "_") + "@"+self.component+"/bot"
                self.send_plain(self.jid_proxy_to, from_jid, unicode(msg.body))
        else:
            log.msg("Non-chat/body message: %s" % msg.toXml())


class XmppProxyPresenceProtocol(PresenceClientProtocol):

    lost = None
    connected = None

    def __init__(self, component, jid_act_as, jid_proxy_to, resource):
        super(XmppProxyPresenceProtocol, self).__init__()
        self.component = component
        self.jid_act_as = jid_act_as
        self.jid_proxy_to = jid_proxy_to.userhost()
        self.resource = resource

    def connectionInitialized(self):
        super(XmppProxyPresenceProtocol, self).connectionInitialized()

        self.connected = time.time()

        global presence_conn
        presence_conn = self

    def update_presence(self, entity, from_entity, show=None, statuses=None):
        status = "Jiwai gtalk proxy by geowhy.org"
        status = ""
        if statuses is None:
            statuses = { None: None }
        self.available(entity, show, statuses, from_entity)

    def connectionLost(self, reason):
        self.connected = None
        self.lost = time.time()

    def _set_status(self, entity, status, to_entity, show=None, statuses=None):
        if status is None:
            status = "available"

        if status != "offline":
            log.msg("_set_status: %s %s" % (entity.full(), status))
            self.update_presence(entity, to_entity, show, { None: "\xe5\x8f\xbd\xe6\xad\xaa\xef\xbc\x81\xe5\x8f\xbd\xe6\xad\xaa\xef\xbc\x81\xe5\x8f\xbd\xe6\xad\xaa\xef\xbc\x81\xe5\x8f\xbd\xe6\xad\xaa\xef\xbc\x81\xe5\x8f\xbd\xe6\xad\xaa\xef\xbc\x81".decode("utf-8")} )
            if entity.userhost() != self.jid_proxy_to:
                from_jid = entity.userhost().replace("@", "_at_").replace(".", "_") + "@"+self.component+"/" + self.resource
                self.update_presence(JID(self.jid_proxy_to), JID(from_jid), show, statuses)
        else:
            self._send_presence(entity, "unavailable", to_entity)
            if entity.userhost() != self.jid_proxy_to:
                from_jid = entity.userhost().replace("@", "_at_").replace(".", "_") + "@"+self.component+"/" + self.resource
                self._send_presence(JID(self.jid_proxy_to), "unavailable", JID(from_jid))

    def available(self, entity=None, show=None, statuses=None, from_entity=None):
        if from_entity is None: 
            from_entity = self.jid_act_as
        presence = ComponentAvailablePresence(from_entity, entity, show, statuses)
        self.send(presence)

    def _send_presence(self, entity, type, from_entity):
        to_jid = entity.userhost()
        log.msg("_send_presence %s %s" % (entity.userhost(), type))
        presence = ComponentPresence(self.jid_act_as, to=entity, type=type)
        if to_jid == self.jid_proxy_to:
            self.send(ComponentPresence(from_entity, to=entity, type=type))
        else:
            self.send(ComponentPresence(self.jid_act_as, to=entity, type=type))

    def subscribe(self, entity, from_entity):
        self._send_presence(entity, "subscribe", from_entity)

    def subscribed(self, entity, from_entity):
        self._send_presence(entity, "subscribed", from_entity)

    def unsubscribe(self, entity, from_entity):
        self._send_presence(entity, "unsubscribe", from_entity)

    def unsubscribed(self, entity, from_entity):
        self._send_presence(entity, "unsubscribed", from_entity)

    def _onPresence(self, presence):
        if True:
            entity = JID(presence["to"])
            to_jid = entity.userhost()
            if to_jid == self.jid_act_as.userhost() or to_jid.find("_at_") > 0:
                super(XmppProxyPresenceProtocol, self)._onPresence(presence)
            else:
                log.msg("presence not for component: %s" % presence.toXml())

    def _onPresenceProbe(self, presence):
        entity = JID(presence['from'])
        to_entity = JID(presence['to'])
        self.update_presence(entity, to_entity)
        log.msg("probe send "+presence.toXml())

    def _onPresenceAvailable(self, presence):
        entity = JID(presence["from"])

        show = unicode(presence.show or '')
        if show not in ['away', 'xa', 'chat', 'dnd']:
            show = None

        statuses = self._getStatuses(presence)

        try:
            priority = int(unicode(presence.priority or '')) or 0
        except ValueError:
            priority = 0

        to_entity = JID(presence["to"])
        self.availableReceived(entity, show, statuses, priority, to_entity)

    def _onPresenceUnavailable(self, presence):
        entity = JID(presence["from"])

        statuses = self._getStatuses(presence)

        to_entity = JID(presence["to"])
        self.unavailableReceived(entity, statuses, to_entity)

    def _onPresenceSubscribed(self, presence):
        self.subscribedReceived(JID(presence["from"]), JID(presence["to"]))

    def _onPresenceSubscribe(self, presence):
        self.subscribeReceived(JID(presence["from"]), JID(presence["to"]))

    def _onPresenceUnsubscribe(self, presence):
        self.unsubscribeReceived(JID(presence["from"]), JID(presence["to"]))

    def _onPresenceUnsubscribed(self, presence):
        self.unsubscribedReceived(JID(presence["from"]), JID(presence["to"]))

    def probeReceived(self, entity):
        log.msg("Probe received from %s" % (entity.userhost()))

    def availableReceived(self, entity, show=None, statuses=None, priority=0, to_entity=None):
        log.msg("Available from %s (%s, %s, pri=%s)" % (
            entity.full(), show, statuses, priority))

        self._set_status(entity, show, to_entity, show=show, statuses=statuses)
 
    def unavailableReceived(self, entity, statuses=None,  to_entity=None):
        log.msg("Unavailable from %s" % entity.full())

        self._set_status(entity, "offline", to_entity)


    def subscribedReceived(self, entity, to):
        log.msg("Subscribed received from %s" % (entity.userhost()))

        self._set_status(entity, "subscribed", to)
        if entity.userhost() != self.jid_proxy_to:
            new_jid = entity.userhost().replace("@", "_at_").replace(".", "_") + "@" + self.component
            self.subscribe(JID(self.jid_proxy_to), JID(new_jid))

    def unsubscribedReceived(self, entity, to):
        log.msg("Unsubscribed received from %s" % (entity.userhost()))

        self.unsubscribe(entity, to)
        self.unsubscribed(entity, to)

        self._set_status(entity, "unsubscribed", to)

    def subscribeReceived(self, entity, to):
        log.msg("Subscribe received from %s" % (entity.userhost()))
        self.subscribed(entity, to)
        self.subscribe(entity, to)

        self._set_status(entity, "subscribe", to)

    def unsubscribeReceived(self, entity, to):
        log.msg("Unsubscribe received from %s" % (entity.userhost()))
        self.unsubscribe(entity, to)
        self.unsubscribed(entity, to)
        
        self._set_status(entity, "unsubscribe", to)
