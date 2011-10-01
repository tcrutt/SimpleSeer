from base import *
from Session import Session

class Watcher(MappedClass):
    """
    The Watcher reviews results in Seer, and has two handler patterns:
      - self.conditions takes any parameters in the Parameters object
        and returns a Statistic object.  Multiple conditions can be added and
        are considered implicitly ANDed.  It must refer to a class method.
      - self.handlers are function references that are fired if all conditions return statistic objects,
        and must be a class method.  They are sent the statistics as their parameter.
    
    A typical watcher will have a sample size, and wil look in the Seer() to see
    the most recently recorded measurements.  It can check state on the entire system,
    and may potentially reference the Web, Control, and Display interfaces.  They
    also are responsible for recording any Results and Statistics.    
    
    w = Watcher(
        name = "blob is big enough",
        enabled = 1,
        conditions = ["threshold_greater"],
        parameters = { "threshold_greater": { "threshold": 5000, "samples: 5", "measurement": "Largest Blob", "label": "area" },
        handlers = ["log_statistics"])
    w.check()
    """
    class __mongometa__:
        session = Session().getORMSession()
        name = 'watcher'
        
    _id = ming.orm.FieldProperty(ming.schema.ObjectId)    
    name = ming.orm.FieldProperty(str)
    conditions = ming.orm.FieldProperty(ming.schema.Array(str))
    handlers = ming.orm.FieldProperty(ming.schema.Array(str))#this might be a relation 
    enabled = ming.orm.FieldProperty(int)
    parameters = ming.orm.FieldProperty(ming.schema.Object)
    
    def check(self):
        """
        When the wather runs check, each of its conditions are checked.  If
        all conditions return Statistic objects, they are sent to each
        handler.
        """
        statistics = []
        for condition in self.conditions:
            function_ref = getattr(self, condition)
            stat = function_ref(**self.parameters[condition])
            
            if not stat:
                return False
                
            statistics.append(stat)
    
        for handler in handlers:
            function_ref = getattr(self, condition)
            function_ref(statistics)
        
        return True
    
    
    #These are "core" watcher methods
    
    def threshold_greater(self, threshold, samples, measurement, label):
        
    
    
    def log_statistics(self, statistics):
        for stat in statistics:
            stat.saveResults()
            stat.m.save()
    
    
ming.orm.Mapper.compile_all()   
