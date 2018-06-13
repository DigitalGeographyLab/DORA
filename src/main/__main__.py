import traceback

import sys

sys.path.append('/dgl/codes/DORA/')

import src.main.doraInit as dora
from src.main.util import Logger

try:
    dora.main()
except Exception as err:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    Logger.getInstance().exception(''.join('>> ' + line for line in lines))