import os
#import importlib.resources
#CUR_PATH = str(importlib.resources.files(__package__))

__version__ = "unknown"

CUR_PATH = os.path.dirname(os.path.realpath(__file__))

ver_file = os.path.join(CUR_PATH, '.version')
head_file = os.path.join(os.curdir, '.git', 'HEAD')

if os.path.exists(ver_file):
    with open(ver_file) as h:
        __version__ = str(h.read()).strip()
elif os.path.exists(head_file):
    with open(head_file) as h:
        __version__ = str(h.read()).strip()
