from datetime import datetime

from utils.database import db


def logger(level, **record):
    print(record['message'])
    record.update({
        "datetime": datetime.now(),
        "level": level
    })
    db.logs.insert_one(record)