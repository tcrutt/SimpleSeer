from .Session import Session
from celery import Celery
from celery import task
from celery.exceptions import RetryTaskError
from celery.contrib import rdb

from bson import ObjectId
from gridfs import GridFS
import Image as PIL
from SimpleCV import Image

from .util import ensure_plugins, jsonencode

from . import celeryconfig

session = Session()
celery = Celery()
celery.config_from_object(celeryconfig)
ensure_plugins()

from .realtime import ChannelManager
from . import models as M

import logging
log = logging.getLogger()


@task()
def ping_worker(number):
    """
    Test workers
    """
    print "ping worker with number {}".format(number)
    return number + 1
    

"""
@task()
def backfill_tolerances(measurement_ids, frame_id):
    f = M.Frame.objects.get(id = frame_id)
    
    results = []
    for m_id in measurement_ids: 
        m = M.Measurement.objects.get(id = m_id)
        results += m.tolerance(f, f.results)
    
    return (f.id, results)
"""  

@task()
def backfill_meta(frame_id, inspection_ids, measurement_ids):
    from SeerCloud.OLAPUtils import RealtimeOLAP
    from SeerCloud.models.OLAP import OLAP
    from .Filter import Filter
    
    try:
        f = M.Frame.objects.get(id = frame_id)
        
        # Scrubber may clear old images from frames, so can't backfill on those
        if f.imgfile:
            for i_id in inspection_ids:
                try:
                    i = M.Inspection.objects.get(id=i_id)
                    
                    if not i.parent:
                        if not i.camera or i.camera == f.camera: 
                            f.features += i.execute(f)
                except Exception as e:
                    print 'Error on inspection %s: %s' % (i_id, e)
                    
            for m_id in measurement_ids:
                try:
                    m = M.Measurement.objects.get(id=m_id)
                    m.execute(f, f.features)
                except Exception as e:
                    print 'Error on measurement %s: %s' % (m_id, e)
            
            f.save()    
            
            # Need the filter format for realtime publishing
            ro = RealtimeOLAP()
            ff = Filter()
            allFilters = {'logic': 'and', 'criteria': [{'type': 'frame', 'name': 'id', 'eq': frame_id}]}
            res = ff.getFrames(allFilters)[1]
            
            for m_id in measurement_ids:
                try:
                    m = M.Measurement.objects.get(id=m_id)
                    
                    # Publish the charts
                    charts = m.findCharts()
                    for chart in charts:
                        olap = OLAP.objects.get(name=chart.olap)
                        data = ff.flattenFrame(res, olap.olapFilter)
                        data = chart.mapData(data)
                        ro.sendMessage(chart, data)
                except Exception as e:
                    print 'Could not publish realtime for %s: %s' % (m_id, e)
        else:
            print 'no image on frame.  skipping'
    except Exception as e:
        print 'Error on frame %s: %s' % (frame_id, e)        
    
    print 'Backfill done on %s' % frame_id
    return frame_id
    
    

@task()
def execute_inspections(inspection_ids, gridfs_id, frame_meta):
    # Works like execute_inspection below, but takes multiple inspection ID's
    
    # If no inspection_ids, assume all inspections
    if not inspection_ids:
        inspection_ids = [ i.id for i in M.Inspection.objects ]
    
    db = M.Inspection._get_db()
    fs = GridFS(db)
    image = Image(PIL.open(fs.get(gridfs_id)))
    
    frame = M.Frame()
    frame.image = image
    frame.metadata = frame_meta
    
    features = []
    
    for insp_id in inspection_ids:
        insp = M.Inspection.objects.get(id=insp_id)
        
        try:
            features += insp.execute(frame)
            print 'Finished inspection %s on image %s' % (insp_id, gridfs_id)
        except:
            print 'Inspection Failed'
    
    print 'Finished inspections on image %s' % gridfs_id
    return [ f.feature for f in features ]

@task()
def execute_inspection(inspection_id, gridfs_id, frame_meta):
    """
    Run an inspection given an image's gridfs id, and the inspection id
    """    
    insp = M.Inspection.objects.get(id = inspection_id)
    
    db = insp._get_db()
    fs = GridFS(db)
    image = Image(PIL.open(fs.get(gridfs_id)))
    
    frame = M.Frame()
    frame.image = image
    frame.metadata = frame_meta
    
    try:
        features = insp.execute(frame)
    except:
        print "inspection failed"
        features = []
    
    print "Finished running inspection {} on image {}".format(inspection_id, gridfs_id)
    return ([f.feature for f in features], inspection_id)

    
@task()
def update_frame(frameid, inspection):
    '''
    **SUMMARY**
    This function is called using simpleseer worker objects.

    To start a worker create a simpleseer project, then from that directory run:

    >>> simpleseer worker

    Start another terminal window and then run the following from
    the project directory.  This will act as a task master to all the
    workers attached to the project, these workers can run on seperate
    machines as long as they point to the same database.
    If they are sharing the same database, they should have task delegated
    to them as long as they have the same code base running.

    >>> simpleseer shell
    >>> from SimpleSeer.commands.worker import update_frame

    To test that the function works correctly before shipping off to workers
    you just need to run:

    >>> update_frame((str(frame.id), 'inspection_name_here')

    Now to send the task to to the actual workers you run:

    >>> results = []
    >>> for frame in M.Frame.objects():
          results.append(update_frame.delay(str(frame.id), 'inspection_name_here'))

    The 'inspection_name_here' would be the inspection you want the
    worker to apply to the frame id passed in. For instance 'fastener'.

    To get back results from the workers you can now run:

    >>> [r.get() for r in results]

    Note that this will wait until that worker is finished with their task
    so this may take a while if one of the workers in the results list
    are not done.
    

    **PARAMETERS**
    * *frameid* - This is the actually id of the frame you want the worker to work on
    * *inspection* - The inspection method you want to run on the frame, the worker must have this plugin installed
    
    '''
    
    frame = M.Frame.objects(id=frameid)
    if not frame:
      print "Frame ID (%s) was not found" % frameid
      raise RetryTaskError("Frame ID (%s) was not found" % frameid)
    
    frame = frame[0]
    inspections = M.Inspection.objects(method = inspection)
    if not inspections:
      print 'Inspection method (%s) not found' % inspection
      return 'Inspection method (%s) not found' % inspection
    insp = inspections[0]

    print "analysing features for frame %s" % str(frame.id)
    try:
        img = frame.image
        if not img:
           Exception("couldn't read image")
    except:
        print "could not read image for frame %s" % str(frame.id)
        raise Exception("couldn't read image")

    if not img:
        print "image is empty"
        return "image is empty"

        
    if insp.id in [feat.inspection for feat in frame.features]:
        frame.features = [feat for feat in frame.features if feat.inspection != insp.id]
    

    frame.features += insp.execute(img)
    frame.save()
    print "saved features for frame %s" % str(frame.id)
    return 'frame %s update successful' % str(frame.id)
