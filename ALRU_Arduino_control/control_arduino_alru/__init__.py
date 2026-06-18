from .boards import BOARDS
from .control_alru import *

class Arduino(Board):
    def __init__(self, *args, **kwargs):
        args = list(args)
        args.append(BOARDS['arduino'])
        super(Arduino, self).__init__(*args, **kwargs)

    def __str__(self):
        return "Arduino {0.name} on {0.sp.port}".format(self)