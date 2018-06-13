import sys
import threading
import time
import traceback

sys.path.append('/dgl/codes/DORA/')

from src.main.util import Logger

import src.main.doraInit as dora


class DORAThread():
    def __init__(self, interval=1):
        threading.Thread.__init__(self)
        self.interval = interval

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.kill_received = False
        thread.start()  # Start the execution

    def run(self):
        # print("Starting CAr Routing Data Analysis")
        while True:
            try:
                dora.main()
            except Exception as err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                Logger.getInstance().exception(''.join('>> ' + line for line in lines))
                raise err
                # time.sleep(self.interval)


doraThread = DORAThread()
# cardatThread.start()
time.sleep(3)
print('Checkpoint')