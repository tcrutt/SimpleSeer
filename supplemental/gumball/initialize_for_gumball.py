#!/usr/bin/env python

from SimpleSeer.base import *
from SimpleSeer.Session import Session

if (len(sys.argv) > 1):
   config_file = sys.argv[1] 
else:
   config_file = "gumball.cfg"

Session(config_file)

from SimpleSeer.models import Inspection, Measurement, Frame, OLAP, Result, Chart
from SimpleSeer.models import Result, Inspection, Measurement, Frame
 

Frame.objects.delete()
Inspection.objects.delete()
Measurement.objects.delete()
OLAP.objects.delete()
Result.objects.delete()
Chart.objects.delete()

insp = Inspection( name= "Region", 
  method="region", 
  parameters = { "x": 100, "y": 100, "w": 440, "h": 280 })
   
insp.save()

meas = Measurement( name="Gumball Color", label="Color", method = "closestcolorml", inspection = insp.id)
meas.save()

meas1 = Measurement( name="Delivery Color", label="Color", method = "closestcolor_manual", inspection = insp.id )
meas1.save()

meas3 = Measurement( name="Delivery Time", label="Seconds", method = "timebetween_manual", inspection = insp.id, 
  parameters = dict( inspection = insp.id ))
meas3.save()



## Histogram of color of gumballs evaluated
o1 = OLAP()
o1.name = 'EvaledColor'  
o1.maxLen = 1000 
o1.queryType = 'measurement_id' 
o1.queryId = meas.id 
o1.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o1.since = None
o1.before = None
o1.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'field': 'string', 'default': 5}
o1.customFilter = {} 
o1.statsInfo = []
o1.save()

c1 = Chart()
c1.name = 'Color Evaluated'
c1.olap = o1.name
c1.style = 'column'
c1.minval = 0
c1.maxval = 100
c1.xtype = 'linear'
c1.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c1.labelmap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c1.accumulate = True
c1.renderorder = 2
c1.halfsize = True
c1.realtime = True
c1.dataMap = ['capturetime','string']
c1.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c1.save()


## Histogram of color of gumballs delivered
o2 = OLAP()
o2.name = 'DeliveredColor'  
o2.maxLen = 1000 
o2.queryType = 'measurement_id' 
o2.queryId = meas1.id 
o2.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o2.since = None
o2.before = None
o2.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'field': 'string', 'default': 5}
o2.customFilter = {} 
o2.statsInfo = []
o2.save()

c2 = Chart()
c2.name = 'Color Delivered'
c2.olap = o2.name
c2.style = 'column'
c2.minval = 0
c2.maxval = 100
c2.xtype = 'linear'
c2.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c2.labelmap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c2.accumulate = True
c2.renderorder = 3
c2.halfsize = True
c2.realtime = True
c2.dataMap = ['capturetime','string']
c2.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c2.save()


## Delivery time
o3 = OLAP()
o3.name = 'DeliveryTime'  
o3.maxLen = 1000 
o3.queryType = 'measurement_id' 
o3.queryId = meas3.id 
o3.fields = ['capturetime','numeric', 'measurement_id', 'inspection_id', 'frame_id']
o3.since = None
o3.before = None
o3.customFilter = {} 
o3.statsInfo = []
o3.save()

c3 = Chart()
c3.name = 'Delivery Time'
c3.olap = o3.name
c3.style = 'spline'
c3.minval = 0
c3.maxval = 100
c3.xtype = 'datetime'
c3.colormap = {}
c3.labelmap = {}
c3.accumulate = False
c3.renderorder = 100
c3.halfsize = False
c3.realtime = True
c3.dataMap = ['capturetime','numeric']
c3.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c3.save()


## Yellow gumball delivered
o4 = OLAP()
o4.name = 'DeliveredYellow'  
o4.maxLen = 1000 
o4.queryType = 'measurement_id' 
o4.queryId = meas.id 
o4.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o4.since = None
o4.before = None
o4.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'default':5, 'field': 'string'}
o4.customFilter = {'field': 'string', 'val': 'yellow'} 
o4.statsInfo = []
o4.postProc = {'movingCount':'string'}
o4.notNull = True
o4.save()

c4 = Chart()
c4.name = 'Delivered Candies by Color'
c4.olap = o4.name
c4.style = 'spline'
c4.minval = 0
c4.maxval = 100
c4.xtype = 'datetime'
c4.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c4.labelmap = {}
c4.accumulate = False
c4.renderorder = 4
c4.halfsize = False
c4.realtime = True
c4.dataMap = ['capturetime','string']
c4.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c4.save()


## Green gumball delivered
o5 = OLAP()
o5.name = 'DeliveredGreen'  
o5.maxLen = 1000 
o5.queryType = 'measurement_id' 
o5.queryId = meas.id 
o5.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o5.since = None
o5.before = None
o5.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'default':5, 'field': 'string'}
o5.customFilter = {'field': 'string', 'val': 'green'} 
o5.statsInfo = []
o5.postProc = {'movingCount':'string'}
o5.notNull = True
o5.save()

c5 = Chart()
c5.name = 'Candies by Color Green'
c5.olap = o5.name
c5.chartid = c4.id
c5.style = 'spline'
c5.minval = 0
c5.maxval = 100
c5.xtype = 'datetime'
c5.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c5.labelmap = {}
c5.accumulate = False
c5.renderorder = c4.renderorder + 1
c5.halfsize = False
c5.realtime = True
c5.dataMap = ['capturetime','string']
c5.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c5.save()




## Purple gumball delivered
o6 = OLAP()
o6.name = 'DeliveredPurple'  
o6.maxLen = 1000 
o6.queryType = 'measurement_id' 
o6.queryId = meas.id 
o6.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o6.since = None
o6.before = None
o6.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'default':5, 'field': 'string'}
o6.customFilter = {'field': 'string', 'val': 'purple'} 
o6.statsInfo = []
o6.postProc = {'movingCount':'string'}
o6.notNull = True
o6.save()

c6 = Chart()
c6.name = 'Candies by Color Purple'
c6.olap = o6.name
c6.chartid = c4.id
c6.style = 'spline'
c6.minval = 0
c6.maxval = 100
c6.xtype = 'datetime'
c6.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c6.labelmap = {}
c6.accumulate = False
c6.renderorder = c4.renderorder + 1
c6.halfsize = False
c6.realtime = True
c6.dataMap = ['capturetime','string']
c6.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c6.save()


## Orange gumball delivered
o7 = OLAP()
o7.name = 'DeliveredOrange'  
o7.maxLen = 1000 
o7.queryType = 'measurement_id' 
o7.queryId = meas.id 
o7.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o7.since = None
o7.before = None
o7.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'default':5, 'field': 'string'}
o7.customFilter = {'field': 'string', 'val': 'orange'} 
o7.statsInfo = []
o7.postProc = {'movingCount':'string'}
o7.notNull = True
o7.save()

c7 = Chart()
c7.name = 'Candies by Color Orange'
c7.olap = o7.name
c7.chartid = c4.id
c7.style = 'spline'
c7.minval = 0
c7.maxval = 100
c7.xtype = 'datetime'
c7.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c7.labelmap = {}
c7.accumulate = False
c7.renderorder = c4.renderorder + 1
c7.halfsize = False
c7.realtime = True
c7.dataMap = ['capturetime','string']
c7.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c7.save()



## Red gumball delivered
o8 = OLAP()
o8.name = 'DeliveredRed'  
o8.maxLen = 1000 
o8.queryType = 'measurement_id' 
o8.queryId = meas.id 
o8.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o8.since = None
o8.before = None
o8.valueMap = {'red': 0, 'green': 1, 'yellow': 2, 'organge': 3, 'purple': 4, 'default':5, 'field': 'string'}
o8.customFilter = {'field': 'string', 'val': 'red'} 
o8.statsInfo = []
o8.postProc = {'movingCount':'string'}
o8.notNull = True
o8.save()

c8 = Chart()
c8.name = 'Candies by Color Red'
c8.olap = o8.name
c8.chartid = c4.id
c8.style = 'spline'
c8.minval = 0
c8.maxval = 100
c8.xtype = 'datetime'
c8.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c8.labelmap = {}
c8.accumulate = False
c8.renderorder = c4.renderorder + 1
c8.halfsize = False
c8.realtime = True
c8.dataMap = ['capturetime','string']
c8.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c8.save()


## PassFail
o9 = OLAP()
o9.name = 'PassFail'  
o9.maxLen = 1000 
o9.queryType = 'measurement_id' 
o9.queryId = meas1.id 
o9.fields = ['capturetime','string', 'measurement_id', 'inspection_id', 'frame_id']
o9.since = None
o9.before = None
o9.valueMap = {'purple': 0, 'default':1, 'field': 'string'}
o9.customFilter = {} 
o9.statsInfo = []
o9.save()

c9 = Chart()
c9.name = 'Candies Overview'
c9.olap = o9.name
c9.style = 'marpleoverview'
c9.minval = 0
c9.maxval = 100
c9.xtype = 'datetime'
c9.colormap = {'0': 'red', '1': 'green', '2': 'yellow','3': u'orange','4': 'purple'}
c9.labelmap = {}
c9.accumulate = False
c9.renderorder = c4.renderorder + 1
c9.halfsize = False
c9.realtime = True
c9.dataMap = ['capturetime','string']
c9.metaMap = ['measurement_id', 'inspection_id', 'frame_id']
c9.save()

print "DANGER, WILL ROBINSON: For testing purposes in virtual env, delivered candies by color based on evaled candy."
