#from pika import BlockingConnection, ConnectionParameters, BasicProperties
from amqplib import client_0_8 as amqp

from socketio.namespace import BaseNamespace
import gevent

from .Session import Session
from .base import jsonencode, jsondecode

import logging
log = logging.getLogger(__name__)

class ChannelManager(object):
    
    def __init__(self, shareConnection=True):
        self._init = True
        self._config = Session()
        self._response = {}
        
        # Greenlets don't like shared connections
        self._shareConnection = shareConnection
        if shareConnection:
            self._connection = amqp.Connection(host=self._config.rabbitmq)
            
    def __repr__(self):
        return '<ChannelManager>' 
        
    def publish(self, exchange, message):
        if not self._shareConnection:
            conn = amqp.Connection(host=self._config.rabbitmq)
        else:
            conn = self._connection
        channel = conn.channel()
        channel.exchange_declare(exchange=exchange, type='fanout')
        msg = amqp.Message(jsonencode(message))
        
        channel.basic_publish(msg, exchange=exchange, routing_key='')
        channel.close()
        
    def subscribe(self, exchange, callback):
        log.info('Subscribe to %s' % exchange)                     
        if not self._shareConnection:
            conn = amqp.Connection(host=self._config.rabbitmq)
        else:
            conn = self._connection        
        
        channel = conn.channel()
        
        channel.exchange_declare(exchange=exchange, type='fanout')
        (queue_name, msgs, consumers) = channel.queue_declare(exclusive=True)
        
        channel.queue_bind(exchange=exchange, queue=queue_name)
        channel.basic_consume(callback=callback, queue=queue_name)
        
        try:    
            while True:
                channel.wait()
        except:
            channel.close()
    
    def rpcSendRequest(self, workQueue, request):
        from random import choice
        
        if not self._shareConnection:
            conn = amqp.Connection(host=self._config.rabbitmq)
        else:
            conn = self._connection
        
        corrid = ''.join([ choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(20) ])
        self._response[corrid] = None
        
        
        def on_response(msg):
            if corrid == msg.properties['correlation_id']:
                self._response[corrid] = jsondecode(msg.body)
                
        channel = conn.channel()
        (callback_queue, msgs, consumers) = channel.queue_declare(exclusive=True)
        
        channel.basic_consume(callback=on_response, no_ack=True, queue=callback_queue)
        
        msg = amqp.Message(jsonencode(request))
        msg.properties['correlation_id'] = corrid
        msg.properties['reply_to'] = callback_queue
        
        channel.basic_publish(msg, exchange='', routing_key=workQueue)
        
        while self._response[corrid] is None:
            channel.wait()
            log.info('RPC request on %s' % workQueue)
            
        return self._response.pop(corrid)
    
    def rpcRecvRequest(self, workQueue, callback):
        if not self._shareConnection:
            conn = amqp.Connection(host=self._config.rabbitmq)
        else:
            conn = self._connection
                    
        def on_request(msg):
            res = callback(msg.body)
            resMsg = amqp.Message(jsonencode(res))
            resMsg.properties['correlation_id'] = msg.properties['correlation_id']
            
            msg.channel.basic_publish(resMsg, exchange='', routing_key=msg.properties['reply_to'])
            msg.channel.basic_ack(delivery_tag=msg.delivery_tag)
        
        channel = conn.channel()
        channel.queue_declare(queue=workQueue)
            
        channel.basic_qos(prefetch_size=0, prefetch_count=1, a_global=False)
        channel.basic_consume(callback=on_request, queue=workQueue)
        
        log.info('RPC worker waiting on %s' % workQueue)
        while True:
            channel.wait()
        
    def exchangeExists(self, name):    
        exists = True
        inUse = False
        
        if not self._shareConnection:
            conn = amqp.Connection(host=self._config.rabbitmq)
        else:
            conn = self._connection
        
        channel = conn.channel()
        
        try:
            channel.exchange_delete(exchange=name, if_unused=True)
        except Exception as e:
            if e[0] == 404:
                exists = False
            if e[0] == 406:
                inUse = True
            
        return exists and inUse
            
class RealtimeNamespace(BaseNamespace):

    def initialize(self):
        self._channels = {}  # _channels[exchange] = greenlet
        self._channel_manager = ChannelManager(shareConnection=False)

    def disconnect(self, *args, **kwargs):
        for name in self._channels.keys():
            self._unsubscribe(name)
        super(RealtimeNamespace, self).disconnect(*args, **kwargs)

    def on_subscribe(self, name):
        self._subscribe(name)

    def on_unsubscribe(self, name):
        self._unsubscribe(name)

    def on_publish(self, name, payload):
        jsondict = jsondecode(payload)
        self._channel_manager.publish(str(name), jsondict)

    def _subscribe(self, name):
        greenlet = gevent.spawn_link_exception(self._relay, name)
        self._channels[name] = greenlet
        
    def _unsubscribe(self, name):
        if name not in self._channels: return
        greenlet = self._channels.pop(name)
        greenlet.kill()
    
    def _relay(self, exchange):
        
        def callback(msg):
            self.emit('message:' + exchange, dict(
                    channel=exchange,
                    data=jsondecode(msg.body)))
        
        self._channel_manager.subscribe(exchange, callback) 
                    
#this is a little syntax sugar for debugging pubsub
class Channel():
    manager = None
    channelname = None
    
    def __init__(self, name):
        self.manager = ChannelManager(shareConnection=False)
        self.channelname = name
        
    def publish(self, **kwargs):
        self.manager.publish(self.channelname + "/", kwargs)
    
    def listen(self):
        
        def callback(msg):
            print jsondecode(msg.body)
        
        self.manager.subscribe(self.channelname + "/", callback)
        
# A logging handler that sends messages via pubsub
class PubSubHandler(logging.Handler):
    
    _channel = None
    _cm = None
    
    def __init__(self, channel='logging/'):
        super(PubSubHandler, self).__init__()
        self._channel = channel
        
        # This might be running in a greenlet, so do not share connection
        self._cm = ChannelManager(shareConnection=False)
        
    def emit(self, msg):
        self._cm.publish(self._channel, {'ts': msg.created, 'file': msg.filename, 'level': msg.levelname, 'msg': msg.msg})
         
