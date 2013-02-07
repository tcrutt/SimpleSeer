import pymongo
from collections import defaultdict

from SimpleSeer.realtime import ChannelManager    
    
from . import Frame, Measurement, Inspection
from ..worker import backfill_meta

import logging
log = logging.getLogger(__name__)

class MetaSchedule():
    
    _db = None
    _parallel_tasks = 10
    
    __shared_state = {}
    
    def __init__(self):
        self.__dict__ = self.__shared_state
        
        if not self._db:
            self._db = Frame._get_db()
            self._db.metaschedule.ensure_index('frame_id')
            self._db.metaschedule.ensure_index('semaphore')
        
            from ..Session import Session
            s = Session()
            self.cleanup(s.procname)
    
    def cleanup(self, procname):
        log.info('Cleaning up metadata for process %s' % procname)
        self._db.metaschedule.remove({'semaphore': 1}) 
        
    def enqueue(self, field, field_id):
        to_add = []
        for f in Frame.objects:
            if f.imgfile:
                # Add the measurement to the frame/measurement grid.  Create the entry if it does not exist
                to_add.append({'frame_id': f.id, 'field_id': field_id})
        
        if to_add:
            to_check = to_add.pop()
            while to_check:
                # make sure the current entry is not locked:
                if self._db.metaschedule.find({'frame_id': to_check['frame_id'], 'semaphore': 1}).count() == 0:
                    self._db.metaschedule.update({'frame_id': to_check['frame_id'], 'semaphore': 0}, {'$push': {field: to_check['field_id']}}, True)
                else:
                    # otherwise, put it back
                    to_add.append(to_check)
                    
                if to_add:
                    to_check = to_add.pop()
                else:
                    to_check = None
        
    def enqueue_inspection(self, insp_id):
        self.enqueue('inspections', insp_id)
    
    def enqueue_measurement(self, meas_id):
        self.enqueue('measurements', meas_id)
    
    def enqueue_tolerance(self, meas_id):
        self.enqueue('tolerances', measurement_id)
        
    def run_complete_async(self, insps, meass):
        from SimpleSeer.worker import metaschedule_run_complete
        metaschedule_run_complete.delay(insps, meass)
        
    def run_async(self):
        from SimpleSeer.worker import metaschedule_run
        metaschedule_run.delay()
        
    def run(self):
        from time import sleep
        from . import ResultEmbed, FrameFeature
        from bson import ObjectId
        
        scheduled = []
        completed = 0
        
        while self._db.metaschedule.find().count() > 0 or len(scheduled) > 0:
            
            # If I'm ready to schedule another task and there are tasks to schedule
            #print self._db.metaschedule.find().count()
            if len(scheduled) < self._parallel_tasks and self._db.metaschedule.find({'semaphore': 0}).count() > 0:
                # Update the semaphore field to lock other frames with the same id from running
                meta = self._db.metaschedule.find_and_modify(query = {'semaphore': 0}, update = {'$inc': {'semaphore': 1}})
                if meta:
                    #print 'scheduling %s' % meta['frame_id']
                    scheduled.append(backfill_meta.delay(meta['frame_id'], meta.get('inspections', []), meta.get('measurements', [])))
            else:
                # wait for the queue to clear a bit
                #print 'sleepy time'
                sleep(0.2)
            
            complete_indexes = []
            if len(scheduled) > 0:
                for index, s in enumerate(scheduled):
                    if s.ready():
                        # Note, want index in reverse order so can pop withouth changes indexes later
                        complete_indexes.insert(0,index)
            
            for index in complete_indexes:
                async = scheduled.pop(index)
                frame_id = async.get()
                #print 'completed %s' % frame_id
                
                # Clear the entry from the queue
                self._db.metaschedule.find_and_modify({'frame_id': ObjectId(frame_id), 'semaphore': 1}, {}, remove=True)
                
                # Print progress stats
                completed += 1
                
                ChannelManager().publish('worker/', dict(u='data', m={'waiting': self._db.metaschedule.find().count() + len(scheduled), 'complete': completed}))
                log.info('Backfill waiting: %s, scheduled: %s, completed: %s' % (self._db.metaschedule.find().count(), len(scheduled), completed))
        
        log.info('Done backfilling')