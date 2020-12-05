from datetime import datetime
from tzlocal import get_localzone
from scheduler import Scheduler

if __name__ == '__main__':
    date_now = datetime.now()
    tz = get_localzone()
    scheduler = Scheduler(date_now, tz)
    scheduler.run()
