from .models.OLAP import OLAP
from .models.Chart import Chart
from .models.Measurement import Measurement
from .models.Inspection import Inspection

from .Filter import Filter

from gevent import Greenlet, sleep
from datetime import datetime, timedelta
from time import mktime

from .util import utf8convert
from .realtime import ChannelManager

from random import randint
import pandas as pd

import logging
log = logging.getLogger(__name__)


class OLAPFactory:
    
    def createTransient(self, filters, originalChart):
        # A transient OLAP is one that should be delted when no subscriptions are listening
        # This is needed for OLAPs that publish realtime but are the result of filters
        
        from .models.Chart import Chart
        
        # First, create the core OLAP
        originalOLAP = OLAP.objects(name = originalChart.olap)[0]
        o = self.fromFilter(filters, originalOLAP)
        o.transient = datetime.now()
        o.save()
        
        # Create the chart to point to it
        # For a chart only used for realtime, we realy only care about the data maps
        c = Chart()
        c.name = originalChart.name + '_' + str(randint(1, 1000000))
        c.metaMap = originalChart.metaMap
        c.dataMap = originalChart.dataMap
        c.olap = o.name
        c.save()
    
    def removeTransient(self, chartName):
        from .models.Chart import Chart
        
        cs = Chart.objects(name = chartName)
        if cs:
            c = cs[0]
        else:
            log.warn('Asked to cleanup %s, but it does not exist' % chartName)
            return
            
        os = OLAP.objects(name = c.olap)
        if os:
            o = os[0]
        else:
            log.warn('No OLAPs associated with %s' % chartName)
            return
            
        if o.transient:
            log.info('Deleting transient OLAP: %s' % o.name)
            o.delete()
            log.info('Deleting associated chart: %s' % c.name)
            c.delete()
        else:
            log.info('Nobody listening to OLAP %s' % o.name)
        
        
        
    def fromFilter(self, filters, oldOLAP = None):
        
        newOLAP = OLAP()
        if oldOLAP:
            newOLAP.olapFilter = oldOLAP.mergeParams(filters)
        else:
            newOLAP.olapFilter = filters
            
        return self.fillOLAP(newOLAP)
    
    def fromFields(self, fields):
        # Create an OLAP object from a list of fields desired
        # Each field should be specified in the same was as Filter fields
        #   type: one of (frame, framefeature, measurement)
        #   name: if a frame, specify the field name
        #         otherwise use dotted notation for the frame/measurement name.field name
        
        for f in fields:
            f['exists'] = 1
        
        # Put together the OLAP
        o = OLAP()
        o.olapFilter = fields
        
        # Fill in the rest with default values
        return self.fillOLAP(o)
        
    def fromObject(self, obj):
        # Create an OLAP object from another query-able object
        
        # Find the type of object and 
        # get a result to do some guessing on the data types
        
        filters = []
        
        f = Filter()
        inspKeys, measKeys = f.keyNamesHash()
        
        if type(obj) == Measurement:
            filterKeys = measKeys
            filterType = 'measurement'
        elif type(obj) == Inspection:
            filterKeys = inspKeys
            filterType = 'framefeature'
        else:
            log.warn('OLAP factory got unknown type %s' % str(type(obj)))
            filterKeys = []
            filterType = 'unknown'
            
        for key in filterKeys:
            filters.add({'type': filterType, 'name': obj.name + '.' + key, 'exists':1})
        
        
        # Put together the OLAP
        o = OLAP()
        o.olapFilter = filters
        
        # Fill in the rest with default values
        return self.fillOLAP(o)
        
    
    def fillOLAP(self, o):
        # Fills in default values for undefined fields of an OLAP
        
        if o.olapFilter:
            o.name = o.olapFilter[0]['name'] + '_' + str(randint(1, 1000000))
        else:
            o.name = 'GeneratedOLAP_' + str(randint(1, 1000000))
            
        # Default to max query length of 1000
        if not o.maxLen:
            o.maxLen = 1000
            
        # No mapping of output values
        if not o.valueMap:
            o.valueMap = []
    
        # No since constratint
        if not o.since:
            o.since = None
        
        # No before constraint
        if not o.before:
            o.before = None
            
        # Finally, run once to see if need to aggregate
        if not o.statsInfo:
            results = o.execute()
            
            # If to long, do the aggregation
            if len(results) > o.maxLen:
                self.autoAggregate(results, autoUpdate=False)
            
        # Return the result
        # NOTE: This OLAP is not saved 
        return o
        

    
class RealtimeOLAP():
    
    def realtime(self, frame):
        
        charts = Chart.objects() 
        
        print 'starting...'
        
        for chart in charts:
            # If no statistics, send result on its way
            # If there are stats, it will be handled later by stats scheduler
            olap = OLAP.objects(name=chart.olap)[0]
            if not olap.statsInfo:
                data = chart.chartData(realtime = True)
                if data:
                    self.sendMessage(chart, data)
                
    def sendMessage(self, chart, data):
        if (len(data) > 0):
            msgdata = dict(
                chart = str(chart.name),
                data = data)
        
            chartName = 'Chart/%s/' % utf8convert(chart.name) 
            ChannelManager().publish(chartName, dict(u='data', m=msgdata))
            

class ScheduledOLAP():
    
    def runSked(self):
        
        log.info('Starting statistics schedules')
        
        glets = []
        
        glets.append(Greenlet(self.skedLoop, 'minute'))
        glets.append(Greenlet(self.skedLoop, 'hour'))
        glets.append(Greenlet(self.skedLoop, 'day'))
        
        # Start all the greenlets
        for g in glets:
            g.start()
            
        # Join all the greenlets
        for g in glets:
            g.join()
                
    def skedLoop(self, interval):
        
        from datetime import datetime
        from .models.Chart import Chart
        
        nextTime = datetime.utcnow()
        
        while (True):
            log.info('Checking for OLAPs running every %s' % interval)
            
            # Split the time into components to make it easier to round
            year = nextTime.year
            month = nextTime.month
            day = nextTime.day
            hour = nextTime.hour
            minute = nextTime.minute
            
            # Setup the start and end time for the intervals
            if interval == 'minute':
                endBlock = datetime(year, month, day, hour, minute)
                startBlock = endBlock - timedelta(0, 60)
                nextTime = endBlock + timedelta(0, 61)
                sleepTime = 60
            elif interval == 'hour':
                endBlock = datetime(year, month, day, hour, 0)
                startBlock = endBlock - timedelta(0, 3600)
                nextTime = endBlock + timedelta(0, 3661)
                sleepTime = 3600
            elif interval == 'day':
                endBlock = datetime(year, month, day, 0, 0)
                startBlock = endBlock - timedelta(1, 0)
                nextTime = endBlock + timedelta(1, 1)
                sleepTime = 86400
            
            # OLAPs assume time in epoch seconds
            startBlockEpoch = mktime(startBlock.timetuple())
            endBlockEpoch = mktime(endBlock.timetuple())

            # Find all OLAPs that run on this time interval
            os = OLAP.objects(groupTime = interval) 
    
            # Have each OLAP send the message
            for o in os:
                
                log.info('%s running per %s' % (o.name, interval)) 
                
                o.since = startBlockEpoch
                o.before = endBlockEpoch
                data = o.execute()
                
                cs = Chart.objects(olap = o.name)
                    
                for c in cs:
                    chartData = c.mapData(data)
                    ro = RealtimeOLAP() # To get access to the sendMessage fn
                    ro.sendMessage(o, chartData, c.name)
                
                
            # Set the beginning time interval for the next iteraction
            sleepTime = (nextTime - datetime.utcnow()).total_seconds()
            
            # Wait until time to update again
            sleep(sleepTime)
