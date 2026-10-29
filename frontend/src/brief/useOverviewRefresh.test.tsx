import { act, cleanup, fireEvent, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { EconomyBriefResponse, OverviewRefreshState } from "../api/macrolens";
import { fetchEconomyBrief, fetchOverviewRefresh, requestOverviewRefresh } from "../api/macrolens";
import { useOverviewRefresh, useBackgroundRefresh } from "./useOverviewRefresh";

vi.mock("../api/macrolens",()=>({fetchEconomyBrief:vi.fn(),fetchOverviewRefresh:vi.fn(),requestOverviewRefresh:vi.fn()}));
const noop=()=>{};
const NOW=new Date("2026-10-26T12:00:00Z");
const stored=()=>({data_revision:"saved",automatic_refresh_supported:true,refresh:{status:"idle",results:[]}} as unknown as EconomyBriefResponse);
const completed=(extra:Partial<OverviewRefreshState>={}):OverviewRefreshState=>({status:"complete",publication_id:"saved",next_check_at:new Date(+NOW+900_000).toISOString(),results:[],...extra});
async function settle(){await act(async()=>{await Promise.resolve();await Promise.resolve();});}
beforeEach(()=>{vi.useFakeTimers();vi.setSystemTime(NOW);vi.resetAllMocks();Object.defineProperty(document,"visibilityState",{configurable:true,value:"visible"});});
afterEach(()=>{cleanup();vi.useRealTimers();});

test("entry asks once, retains saved data and honors backend cadence on rerender and focus",async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed());const onData=vi.fn();
 const {result,rerender}=renderHook(({data})=>useOverviewRefresh(data,onData),{initialProps:{data:stored()}});await settle();
 expect(result.current?.status).toBe("complete");expect(onData).not.toHaveBeenCalled();
 rerender({data:stored()});fireEvent(window,new Event("focus"));await settle();expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 vi.setSystemTime(+NOW+900_001);fireEvent(window,new Event("focus"));fireEvent(document,new Event("visibilitychange"));await settle();
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);expect(fetchEconomyBrief).not.toHaveBeenCalled();
});

test("polls only job status and switches data atomically when the new revision is ready",async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed({status:"running",publication_id:"saved"}));
 vi.mocked(fetchOverviewRefresh).mockResolvedValue(completed({publication_id:"new",status:"partial"}));
 let resolve!:(value:EconomyBriefResponse)=>void;vi.mocked(fetchEconomyBrief).mockImplementation(()=>new Promise(done=>{resolve=done;}));
 const onData=vi.fn(),{result}=renderHook(()=>useOverviewRefresh(stored(),onData));await settle();
 expect(result.current?.status).toBe("running");await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);expect(fetchOverviewRefresh).toHaveBeenCalledTimes(1);expect(onData).not.toHaveBeenCalled();expect(result.current?.status).toBe("running");
 const next={...stored(),data_revision:"new",refresh:completed({publication_id:"new",status:"partial"})};await act(async()=>resolve(next));
 expect(onData).toHaveBeenCalledTimes(1);expect(onData).toHaveBeenCalledWith(next);expect(result.current?.status).toBe("partial");
 await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});expect(fetchOverviewRefresh).toHaveBeenCalledTimes(1);
});

test("network failures back off and hidden tabs do not start provider checks",async()=>{
 vi.mocked(requestOverviewRefresh).mockRejectedValue(new Error("offline"));const onData=vi.fn(),{result}=renderHook(()=>useOverviewRefresh(stored(),onData));await settle();expect(result.current?.status).toBe("error");
 fireEvent(window,new Event("focus"));await settle();expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 vi.setSystemTime(+NOW+901_000);Object.defineProperty(document,"visibilityState",{configurable:true,value:"hidden"});fireEvent(document,new Event("visibilitychange"));await settle();expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 Object.defineProperty(document,"visibilityState",{configurable:true,value:"visible"});fireEvent(document,new Event("visibilitychange"));await settle();expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
});

test("coalesces simultaneous focus events while a request is pending and aborts on unmount",async()=>{
 let signal:AbortSignal|undefined;vi.mocked(requestOverviewRefresh).mockImplementation(s=>{signal=s;return new Promise(()=>{});});
 const onData=vi.fn(),{unmount}=renderHook(()=>useOverviewRefresh(stored(),onData));fireEvent(window,new Event("focus"));fireEvent(document,new Event("visibilitychange"));await settle();expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 unmount();expect(signal?.aborted).toBe(true);
});

test("legacy API without refresh capability makes no refresh requests",async()=>{
 renderHook(()=>useOverviewRefresh({...stored(),automatic_refresh_supported:undefined},vi.fn()));await settle();expect(requestOverviewRefresh).not.toHaveBeenCalled();
});

test.each(['complete','partial','idle','error'] as const)('a continuously visible tab retries %s at the backend deadline without focus',async status=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed({status}));
 renderHook(()=>useOverviewRefresh(stored(),noop));await settle();
 await act(async()=>{await vi.advanceTimersByTimeAsync(899_999);});
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 await act(async()=>{await vi.advanceTimersByTimeAsync(1);});
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
 expect(fetchEconomyBrief).not.toHaveBeenCalled();
});

test('entry before a known cooldown does not POST until permitted',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed());
 renderHook(()=>useOverviewRefresh({...stored(),refresh:completed()},noop));await settle();
 expect(requestOverviewRefresh).not.toHaveBeenCalled();
 await act(async()=>{await vi.advanceTimersByTimeAsync(900_000);});
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
});

test('hidden deadline is suspended and repeated visibility/focus events coalesce with its overdue POST',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed());
 const onData=vi.fn();renderHook(()=>useOverviewRefresh(stored(),onData));await settle();
 Object.defineProperty(document,'visibilityState',{value:'hidden'});fireEvent(document,new Event('visibilitychange'));
 await act(async()=>{await vi.advanceTimersByTimeAsync(1_000_000);});
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 let resolve!:(v:OverviewRefreshState)=>void;
 vi.mocked(requestOverviewRefresh).mockImplementation(()=>new Promise(done=>{resolve=done;}));
 Object.defineProperty(document,'visibilityState',{value:'visible'});
 for(let n=0;n<4;n++){fireEvent(document,new Event('visibilitychange'));fireEvent(window,new Event('focus'));}
 await settle();expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
 await act(async()=>resolve(completed({next_check_at:new Date(Date.now()+900_000).toISOString()})));
 await act(async()=>{await vi.advanceTimersByTimeAsync(899_999);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
});

test('timer and focus at the same deadline never start concurrent POSTs',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValueOnce(completed());
 let resolve!:(v:OverviewRefreshState)=>void;
 vi.mocked(requestOverviewRefresh).mockImplementationOnce(()=>new Promise(done=>{resolve=done;}));
 renderHook(()=>useOverviewRefresh(stored(),noop));await settle();
 await act(async()=>{await vi.advanceTimersByTimeAsync(900_000);fireEvent(window,new Event('focus'));fireEvent(document,new Event('visibilitychange'));});
 expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
 await act(async()=>resolve(completed()));
});

test('running only polls status, pauses while hidden and resumes without a duplicate POST',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed({status:'running'}));
 vi.mocked(fetchOverviewRefresh).mockResolvedValue(completed({status:'running'}));
 renderHook(()=>useOverviewRefresh(stored(),noop));await settle();
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});expect(fetchOverviewRefresh).toHaveBeenCalledTimes(1);
 Object.defineProperty(document,'visibilityState',{value:'hidden'});fireEvent(document,new Event('visibilitychange'));
 await act(async()=>{await vi.advanceTimersByTimeAsync(8000);});expect(fetchOverviewRefresh).toHaveBeenCalledTimes(1);
 vi.mocked(fetchOverviewRefresh).mockResolvedValue(completed({status:'partial'}));
 Object.defineProperty(document,'visibilityState',{value:'visible'});fireEvent(document,new Event('visibilitychange'));await settle();
 expect(fetchOverviewRefresh).toHaveBeenCalledTimes(2);expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
});

test.each([undefined,'invalid','2026-10-26T11:00:00Z'])('invalid or elapsed terminal next_check_at %s cannot spin',async next_check_at=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed({next_check_at}));
 renderHook(()=>useOverviewRefresh(stored(),noop));await settle();
 await act(async()=>{await vi.advanceTimersByTimeAsync(899_999);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 await act(async()=>{await vi.advanceTimersByTimeAsync(1);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
});

test('a longer backend error backoff is honored and network errors also schedule a bounded retry',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValueOnce(completed({status:'error',next_check_at:new Date(+NOW+1_800_000).toISOString()})).mockRejectedValueOnce(new Error('offline')).mockResolvedValue(completed());
 renderHook(()=>useOverviewRefresh(stored(),noop));await settle();
 await act(async()=>{await vi.advanceTimersByTimeAsync(1_799_999);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 await act(async()=>{await vi.advanceTimersByTimeAsync(1);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
 await act(async()=>{await vi.advanceTimersByTimeAsync(900_000);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(3);
});

test('unmount cancels the scheduled retry',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed());
 const {unmount}=renderHook(()=>useOverviewRefresh(stored(),noop));await settle();unmount();
 await act(async()=>{await vi.advanceTimersByTimeAsync(2_000_000);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
});

test('a stale range load is aborted and cannot replace the new range',async()=>{
 let resolve!:(value:EconomyBriefResponse)=>void,oldSignal:AbortSignal|undefined;
 const oldOps={request:vi.fn(async()=>completed({publication_id:'new-old-range'})),load:vi.fn((s:AbortSignal)=>{oldSignal=s;return new Promise<EconomyBriefResponse>(done=>{resolve=done;});})};
 const newOps={request:vi.fn(async()=>completed()),load:vi.fn(async()=>stored())};
 const onData=vi.fn();
 const {rerender}=renderHook(({ops})=>useBackgroundRefresh(stored(),onData,ops),{initialProps:{ops:oldOps}});
 await settle();rerender({ops:newOps});await settle();expect(oldSignal?.aborted).toBe(true);
 await act(async()=>resolve({...stored(),data_revision:'new-old-range'}));
 expect(onData).not.toHaveBeenCalled();expect(newOps.request).toHaveBeenCalledTimes(1);
});

test('focus bursts cannot accelerate status polling of an already-running job',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed({status:'running'}));
 vi.mocked(fetchOverviewRefresh).mockResolvedValue(completed({status:'running'}));
 renderHook(()=>useOverviewRefresh(stored(),noop));await settle();
 for(let n=0;n<4;n++){fireEvent(window,new Event('focus'));await settle();}
 expect(fetchOverviewRefresh).not.toHaveBeenCalled();
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});
 expect(fetchOverviewRefresh).toHaveBeenCalledTimes(1);
 for(let n=0;n<4;n++){fireEvent(window,new Event('focus'));await settle();}
 expect(fetchOverviewRefresh).toHaveBeenCalledTimes(1);
});

test('the reloaded payload can extend cooldown and its deadline replaces the older status response',async()=>{
 vi.mocked(requestOverviewRefresh).mockResolvedValue(completed({publication_id:'new'}));
 vi.mocked(fetchEconomyBrief).mockResolvedValue({...stored(),data_revision:'new',refresh:completed({publication_id:'new',next_check_at:new Date(+NOW+1_800_000).toISOString()})});
 const onData=vi.fn();renderHook(()=>useOverviewRefresh(stored(),onData));await settle();
 expect(onData).toHaveBeenCalledTimes(1);
 await act(async()=>{await vi.advanceTimersByTimeAsync(900_000);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(1);
 await act(async()=>{await vi.advanceTimersByTimeAsync(900_000);});expect(requestOverviewRefresh).toHaveBeenCalledTimes(2);
 expect(fetchEconomyBrief).toHaveBeenCalledTimes(1);
});
