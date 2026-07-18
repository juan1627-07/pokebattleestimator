import time
import requests
from datetime import datetime

URL = "https://pokebattleestimator.onrender.com/"

while True:
    try:
        r = requests.get(URL, timeout=30)

        print(
            datetime.now(),
            "Ping:",
            r.status_code
        )

    except Exception as e:
        print(
            datetime.now(),
            "Failed:",
            e
        )

    time.sleep(600)  # 10 minutes