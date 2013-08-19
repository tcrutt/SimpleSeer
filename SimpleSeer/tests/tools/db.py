
import mongoengine
from filesystem import delete_and_mkdir
import subprocess
import time


class DBtools(object):
    db_instance = {}

    replConfig = {
        "_id" : "rs0",
        "version" : 1,
        "members" : [{
            "_id" : 0,
            "host" : "localname:27020"
        },{
            "_id" : 1,
            "host" : "skybox:27019",
            "priority" : 0.0001
        },{
            "_id" : 2,
            "host" : "skybox:27018",
            "arbiterOnly" : True
        }]}
    arbiter = "127.0.0.1:27020"


    def __init__(self,*args,**kwargs):
    	self.dbs = kwargs.get('dbs',{})

    def spinup_mongo(self,type,postsleep=5):
        delete_and_mkdir("/tmp/{0}".format(type))
        self.db_instance[type] = subprocess.Popen(self.dbs[type])
        time.sleep(postsleep)

    def killall_mongo(self):
        for key in self.db_instance.keys():
            self.kill_mongo(key)

    def kill_mongo(self,instance):
        print "killing {0}".format(instance)
        self.db_instance[instance].kill()
        del self.db_instance[instance]


    def init_replset(self,postsleep=11):
        mongoengine.connection.disconnect()

        from pymongo import MongoClient
        from bson.code import Code
        conn = MongoClient(self.arbiter)
        conn.admin.command("replSetInitiate",self.replConfig)
        time.sleep(postsleep)