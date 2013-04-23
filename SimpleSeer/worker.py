from .Session import Session
from celery import Celery
from celery import task
from celery.exceptions import RetryTaskError
from celery.contrib import rdb

from bson import ObjectId
from gridfs import GridFS

from .util import ensure_plugins, jsonencode

from .realtime import ChannelManager
from . import models as M

import logging
log = logging.getLogger()

from . import celeryconfig
celery = Celery()
celery.config_from_object(celeryconfig)
            
ensure_plugins()
            

def nextInInterval(frame, field, interval):
    currentValue = 0
    try:
        currentValue = getattr(frame, field)
    except:
        currentValue = frame.metadata[field]
        field = 'metadata__' + field
    
    roundValue = currentValue - (currentValue % interval)
    kwargs = {'%s__gte' % field: roundValue, '%s__lt' % field: currentValue, 'camera': frame.camera}
    if M.Frame.objects(**kwargs).count() == 0:
        return True
    return False

class Foreman():
# Manages a lot of worker-related tasks
# This is a borg (speed worker status, plugin checks)

    _useWorkers = False
    _initialized = False
    
    __sharedState = {}
    
    def __init__(self):
        self.__dict__ = self.__sharedState
            
        if not self._initialized:
            self._useWorkers = self.workerRunning()
            self._initialized = True

    def workerRunning(self):
        i = celery.control.inspect()
        if i.active_queues() is not None:
            return True
        else:
            return False

    def process_inspections(self, frame, inspections):
        inspKwargs = {'camera': frame.camera, 'parent__exists': False}
        if inspections:
            inspKwargs['id__in'] = inspections
        
        filteredInsps = M.Inspection.objects(**inspKwargs)
        
        if self._useWorkers:
            return self.worker_inspection_iterator(frame, filteredInsps)    
        else:
            return self.serial_inspection_iterator(frame, filteredInsps)

    def process_measurements(self, frame, measurements):
        pass

    def worker_inspection_iterator(self, frame, insps):
        from time import sleep
        
        scheduled = []
        for i in insps:
            scheduled.append(self.inspection_execute.delay(frame.id, i.id))
        
        completed = 0
        while completed < len(insps):
            ready = []
            
            # List of scheduled items ready
            for idx, s in enumerate(scheduled):
                if s.ready():
                    ready.insert(0, idx)
                    
            # Get the completed results
            for idx in ready:
                async = scheduled.pop(idx)
                features = async.get()
                for feat in features:
                    yield feat
                completed += 1
            
            sleep(0.1)

    def serial_inspection_iterator(self, frame, insps):
        for i in insps:
            features = i.execute(frame)
            for feat in features:
                yield feat

    @task
    def inspection_execute(fid, iid):
        try:
            frame = M.Frame.objects.get(id=fid)
            inspection = M.Inspection.objects.get(id=iid)
            features = inspection.execute(frame)
            return features        
        except Exception as e:
            log.info(e)
            print e
