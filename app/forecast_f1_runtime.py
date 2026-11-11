"""F1 subscribes to the existing Earnings lifecycle, with separate authorization."""
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from app.database.connection import get_independent_connection
from app import forecast_f1_refresh as refresh
from app.database import activate_forecast_f1 as activation

TOKEN=Path(os.getenv('FORECAST_F1_TOKEN',str(activation.ROOT/'data/raw/forecast-f1/activation.json')))
RAW=activation.ROOT/'data/raw/forecast-f1/documents'
from app.database import forecast_f1_authorization_v2 as authorization_v2
IMPORTED_ARTIFACTS=activation.artifacts()
IMPORTED_BACKEND_ARTIFACTS=authorization_v2.artifacts()
STATE=dict(registered=False,activated=False,status='awaiting_activation',last_result=None)
BUSY=threading.Lock()

def status():return dict(STATE,runtime_artifacts=IMPORTED_BACKEND_ARTIFACTS)

def tick(cancelled=lambda:False):
 if cancelled() or not TOKEN.exists():
  STATE.update(activated=False,status='awaiting_activation');return
 if not BUSY.acquire(False):return
 def work():
  try:
   token=json.loads(TOKEN.read_text(encoding='utf-8'))
   loaded=IMPORTED_BACKEND_ARTIFACTS if token.get('version') in (2,3) else IMPORTED_ARTIFACTS
   if token['artifacts']!=loaded:raise ValueError('Loaded F1 code changed')
   if cancelled():return
   from app.forecast_f1_bindings import publication_events
   # run() checks authorization before any publisher HTTP or financial write.
   result=refresh.run(get_independent_connection,RAW,authorization=token,events_loader=publication_events)
   STATE.update(activated=True,status=result['status'],last_result=result)
  except Exception as error:
   STATE.update(activated=False,status='stopped',last_result=dict(error_type=type(error).__name__))
   logging.getLogger(__name__).exception('Forecast F1 stopped safely')
  finally:BUSY.release()
 from app.analytics.overview_refresh import coordinator
 try:coordinator.launch(work)
 except BaseException:BUSY.release();raise

@asynccontextmanager
async def lifespan(app):
 from app.analytics.overview_refresh import coordinator
 from app.earnings_monitor_runtime import lifespan as earnings_lifespan
 stopped=threading.Event()
 remove=coordinator.register_launch_listener('app.earnings_monitor_runtime',lambda:tick(stopped.is_set))
 from app import bls_employment_runtime as bls_runtime
 remove_bls=coordinator.register_launch_listener('app.earnings_monitor_runtime',lambda:bls_runtime.tick(TOKEN,activation.ROOT/'data/raw/bls-employment',stopped.is_set))
 bls_runtime.STATE['registered']=True
 STATE['registered']=True
 try:
  async with earnings_lifespan(app):
   bls_runtime.tick(TOKEN,activation.ROOT/'data/raw/bls-employment',stopped.is_set)
   tick(stopped.is_set)  # one controlled startup check; no additional timer
   yield
 finally:
  stopped.set();remove();remove_bls();bls_runtime.STATE['registered']=False;STATE['registered']=False
