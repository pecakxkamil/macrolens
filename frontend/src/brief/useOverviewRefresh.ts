import { useEffect, useRef, useState } from "react";
import { fetchEconomyBrief, fetchOverviewRefresh, requestOverviewRefresh, type EconomyBriefResponse, type OverviewRefreshState } from "../api/macrolens";

// One entry request and visibility/focus checks. Polling only observes an existing
// job; it never starts another ingestion. The backend owns cadence and locking.
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
    let state=current.current?.refresh,nextCheck=0,deadline=Date.now()+15*60_000;
    const controller=new AbortController();
    const fail=()=>{
      nextCheck=Date.now()+15*60_000;
      state={status:"error",next_check_at:new Date(nextCheck).toISOString(),results:[{resource:"overview",status:"error",error_code:"check_unavailable"}]};
      if(alive)setRefresh(state);
    };
    const check=async(initial=false)=>{
      if(!alive||inFlight||(!initial&&document.visibilityState==="hidden"))return;
      if(state?.status!=="running"&&!initial&&Date.now()<nextCheck)return;
      inFlight=true;
      try{
        if(Date.now()>deadline&&state?.status==="running")throw new Error("Check timed out.");
        const response=state?.status==="running"?await fetchOverviewRefresh(controller.signal):await operations.request(controller.signal);
        if(!alive)return;
        if(!["idle","running","complete","partial","error"].includes(response.status))throw new Error("Invalid check status.");
        state=response;nextCheck=response.next_check_at?Date.parse(response.next_check_at):Date.now()+15*60_000;
        if(response.status==="running"){
          setRefresh(response);timer=setTimeout(()=>void check(),2000);
        }else if(response.publication_id&&response.publication_id!==current.current?.data_revision){
          setRefresh({...response,status:"running"});
          const updated=await operations.load(controller.signal);
          if(alive){onData(updated);setRefresh(updated.refresh??response);}
        }else setRefresh(response);
      }catch{if(alive&&!controller.signal.aborted)fail();}
      finally{inFlight=false;}
    };
    const returned=()=>{
      if(document.visibilityState==="hidden")return;
      if(timer)clearTimeout(timer);
      if(state?.status!=="running")deadline=Date.now()+15*60_000;
      void check();
    };
    void check(true);
    window.addEventListener("focus",returned);document.addEventListener("visibilitychange",returned);
    return()=>{alive=false;controller.abort();if(timer)clearTimeout(timer);window.removeEventListener("focus",returned);document.removeEventListener("visibilitychange",returned);};
  },[enabled,onData,operations]);
  return refresh;
}
