import { useEffect, useRef, useState } from "react";
import { fetchEconomyBrief, fetchOverviewRefresh, requestOverviewRefresh, type EconomyBriefResponse, type OverviewRefreshState } from "../api/macrolens";

// One cancellable timer, driven by backend cadence. Status polling observes
// an existing job; the backend owns provider cadence and locking.
type Refreshable={automatic_refresh_supported?:boolean;data_revision?:string;refresh?:OverviewRefreshState};
type Operations<T>={request:(signal:AbortSignal)=>Promise<OverviewRefreshState>;load:(signal:AbortSignal)=>Promise<T>};
const overviewOperations={request:requestOverviewRefresh,load:fetchEconomyBrief};
export function useOverviewRefresh(data:EconomyBriefResponse|undefined,onData:(data:EconomyBriefResponse)=>void) {
 return useBackgroundRefresh(data,onData,overviewOperations);
}
export function useBackgroundRefresh<T extends Refreshable>(data:T|undefined,onData:(data:T)=>void,operations:Operations<T>) {
  const [refresh,setRefresh]=useState<OverviewRefreshState>();
  const current=useRef(data);current.current=data;
  const enabled=data?.automatic_refresh_supported===true;
  useEffect(()=>{
    if(!enabled)return;
    let alive=true,inFlight=false,timer:ReturnType<typeof setTimeout>|undefined;
    const fallbackDelay=15*60_000;
    const parsedNext=(value?:string|null)=>value?Date.parse(value):NaN;
    let state=current.current?.refresh;
    let nextCheck=parsedNext(state?.next_check_at);
    if(!Number.isFinite(nextCheck))nextCheck=0;
    let deadline=Date.now()+fallbackDelay,nextPoll=0;
    let loadedRevision=current.current?.data_revision;
    const controller=new AbortController();
    const clearTimer=()=>{if(timer!==undefined)clearTimeout(timer);timer=undefined;};
    const schedule=()=>{
      clearTimer();
      if(!alive||inFlight||document.visibilityState==='hidden')return;
      const delay=Math.max(0,(state?.status==='running'?nextPoll:nextCheck)-Date.now());
      timer=setTimeout(()=>void check(),Math.min(delay,2_147_483_647));
    };
    const accept=(response:OverviewRefreshState)=>{
      if(!["idle","running","complete","partial","error"].includes(response.status))throw new Error("Invalid check status.");
      state=response;nextPoll=Date.now()+2000;nextCheck=parsedNext(response.next_check_at);
      // A stale/malformed terminal deadline must not spin in a POST loop.
      if(!Number.isFinite(nextCheck)||nextCheck<=Date.now())nextCheck=Date.now()+fallbackDelay;
    };
    const fail=()=>{
      nextCheck=Date.now()+fallbackDelay;
      state={status:"error",next_check_at:new Date(nextCheck).toISOString(),results:[{resource:"overview",status:"error",error_code:"check_unavailable"}]};
      if(alive)setRefresh(state);
    };
    const check=async()=>{
      if(!alive||inFlight||document.visibilityState==="hidden")return;
      if(state?.status!=="running"&&Date.now()<nextCheck){schedule();return;}
      if(state?.status==='running'&&Date.now()<nextPoll){schedule();return;}
      clearTimer();
      inFlight=true;
      try{
        if(state?.status!=="running")deadline=Date.now()+fallbackDelay;
        if(Date.now()>deadline&&state?.status==="running")throw new Error("Check timed out.");
        const response=state?.status==="running"?await fetchOverviewRefresh(controller.signal):await operations.request(controller.signal);
        if(!alive)return;
        accept(response);
        if(response.status==="running"){
          setRefresh(response);
        }else if(response.publication_id&&response.publication_id!==loadedRevision){
          setRefresh({...response,status:"running"});
          const updated=await operations.load(controller.signal);
          if(alive){accept(updated.refresh??response);loadedRevision=updated.data_revision;onData(updated);setRefresh(updated.refresh??response);}
        }else setRefresh(response);
      }catch{if(alive&&!controller.signal.aborted)fail();}
      finally{inFlight=false;schedule();}
    };
    const returned=()=>{
      clearTimer();
      if(document.visibilityState==="hidden")return;
      void check();
    };
    setRefresh(state);
    void check();
    window.addEventListener("focus",returned);document.addEventListener("visibilitychange",returned);
    return()=>{alive=false;controller.abort();clearTimer();window.removeEventListener("focus",returned);document.removeEventListener("visibilitychange",returned);};
  },[enabled,onData,operations]);
  return refresh;
}
