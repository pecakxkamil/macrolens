"""One API lifecycle wake-up, dispatching through the existing coordinator.

No extra scheduler package/process and no Calendar GET side effects. With no
approved runtime token this loop performs only a filesystem existence check.
"""
import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from app import earnings_monitor as monitor

logger = logging.getLogger(__name__)
STATE = dict(loop_running=False, activated=False, status='awaiting_activation',last_tick=None,last_result=None)


def status():
    return dict(STATE,runtime_artifacts=monitor.IMPORTED_ARTIFACTS)


@asynccontextmanager
async def lifespan(app):
    stopped = threading.Event()
    busy = threading.Event()
    STATE['loop_running'] = True
    async def wakeup():
        while not stopped.is_set():
            STATE['last_tick'] = monitor.utc_now().isoformat()
            if not monitor.TOKEN.exists():
                STATE.update(activated=False,status='awaiting_activation')
            elif not busy.is_set():
                from app.analytics.overview_refresh import coordinator
                busy.set()
                def work():
                    try:
                        result=monitor.run(cancelled=stopped.is_set)
                        STATE.update(activated=result['status'] in ('completed','busy'),status=result['status'],last_result=result)
                    except Exception as error:
                        STATE.update(activated=False,status='activation_or_worker_error',last_result={'error_type':type(error).__name__})
                        logger.exception('Earnings monitor stopped safely')
                    finally:
                        busy.clear()
                coordinator.launch(work)
            await asyncio.sleep(30)
    task=asyncio.create_task(wakeup(),name='macrolens-task-wakeup')
    logger.info('Earnings task wake-up started; imports require separately approved activation')
    try:
        yield
    finally:
        stopped.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        STATE['loop_running']=False
