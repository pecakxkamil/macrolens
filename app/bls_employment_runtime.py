"""Subscribe to the existing Earnings clock; no browser dependency or new timer."""
import json
import threading
from datetime import datetime,timezone
from app.database.connection import get_independent_connection
from app.ingestion import bls_employment as source

BUSY=threading.Lock()
STATE=dict(registered=False,status='awaiting_authorization',last_result=None)


def tick(token_path,directory,cancelled=lambda:False):
    if cancelled() or not token_path.exists() or not BUSY.acquire(False):return
    def work():
        try:
            if cancelled():return
            token=json.loads(token_path.read_text(encoding='utf-8'))
            if token.get('version') not in (3,4,5):return
            result=source.run(get_independent_connection,token,directory)
            STATE.update(status=result['status'],last_result=result)
        except Exception as error:STATE.update(status='stopped',last_result=dict(error_type=type(error).__name__))
        finally:BUSY.release()
    from app.analytics.overview_refresh import coordinator
    try:coordinator.launch(work)
    except BaseException:BUSY.release();raise
