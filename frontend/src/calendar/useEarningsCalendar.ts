import {useEffect,useState} from 'react';
import {fetchEarnings,type CalendarItemsResponse} from './earningsTypes';

export function useEarningsCalendar(startDate:string,endDate:string,enabled=true){
 const [data,setData]=useState<CalendarItemsResponse>(),[error,setError]=useState(false),[warning,setWarning]=useState(false),[retry,setRetry]=useState(0);
 useEffect(()=>{
  let active=true,inFlight=false;const abort=new AbortController();setData(undefined);setError(false);setWarning(false);
  if(!enabled)return()=>{active=false;abort.abort();};
  const refresh=async(initial=false)=>{
   if(inFlight||(!initial&&document.visibilityState==='hidden'))return;
   inFlight=true;
   try{const value=await fetchEarnings(startDate,endDate,[],abort.signal);if(active){setData(value);setError(false);setWarning(false);}}
   catch{if(active){if(initial)setError(true);else setWarning(true);}}
   finally{inFlight=false;}
  };
  void refresh(true);
  const timer=window.setInterval(()=>{void refresh();},60000);
  const visible=()=>{if(document.visibilityState!=='hidden')void refresh();};
  document.addEventListener('visibilitychange',visible);
  return()=>{active=false;abort.abort();window.clearInterval(timer);document.removeEventListener('visibilitychange',visible);};
 },[startDate,endDate,enabled,retry]);
 return {data,error,warning,retry:()=>setRetry(v=>v+1)};
}
export type EarningsCalendarState=ReturnType<typeof useEarningsCalendar>;
