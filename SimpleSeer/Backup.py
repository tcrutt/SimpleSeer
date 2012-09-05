from yaml import load, dump
from datetime import datetime

import models as M

from .realtime import ChannelManager


class Backup:
    
    @classmethod
    def exportAll(overwrite = True):
        # Serializes (json-ifies) non-data objects 
        # By default saves to file names seer_export.json, overwriting previous file
        # Pass overwrite = False to append timestamp to file name (preventing overwrite of previous file)
    
        exportable = ['Inspection', 'Measurement', 'Watcher', 'OLAP', 'Chart']
        
        toExport = []
        
        for exportName in exportable:
            objClass = M.__getattribute__(exportName)
            for obj in objClass.objects:
                # yaml dump does not take kindly to mongoeninge docs, so just store the dict
                toExport.append({'type': exportName, 'obj': obj.__dict__})
        
        yaml = dump(toExport)
        
        ts = ''
        if not overwrite:
            ts = '_%s' % datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = 'seer_export%s.yaml' % ts
        
        f = open(filename, 'w')
        f.write(yaml)
        f.close()
        
    @classmethod
    def listen(self):
        
        cm = ChannelManager()
        sock = cm.subscribe('meta/')
        
        while True:
            cname = sock.recv()
            Export.exportAll()

    @classmethod
    def importAll(self, fname=None):
        
        if not fname:
            fname = 'seer_export.yaml'
            
        f = open(fname, 'r')
        yaml = f.read()
        f.close()
        
        objs = load(yaml)
        
        for o in objs:
            model = M.__getattribute__(o['type'])()
            
            for k, v in o['obj']['_data'].iteritems():
                if k is not None and v is not None:
                    model.__setattr__(k, v)
            model.id = o['obj']['_id']
            
            model.save()
            
    
