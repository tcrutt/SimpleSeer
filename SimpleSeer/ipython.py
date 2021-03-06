
def load_ipython_extension(ipython):
    from .Session import Session
    from .realtime import ChannelManager, Channel
    from . import models as M
    from SimpleCV import Image, ImageSet, Color
    import zmq
    import bson
    
    from .util import load_plugins
    
    load_plugins()

    s = Session(".")
    ipython.push(
        dict(
            Frame = M.Frame,
            OLAP = M.OLAP,
            Chart = M.Chart,
            FrameSet = M.FrameSet,
            Inspection = M.Inspection,
            Measurement = M.Measurement,
            Image = Image,
            ImageSet = ImageSet,
            Dashboard = M.Dashboard,
            Color = Color,
            M=M,
            ObjectId = bson.ObjectId,
            cm=ChannelManager(),
            Channel=Channel),
        interactive=True)
    ipython.prompt_manager.in_template="SimpleSeer:\\#> "
    ipython.prompt_manager.out_template="SimpleSeer:\\#: "
    print 'SimpleSeer ipython extension loaded ok'

def unload_ipython_extension(ipython):
    # If you want your extension to be unloadable, put that logic here.
    pass

