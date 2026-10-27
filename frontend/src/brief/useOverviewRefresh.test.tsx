import { act, cleanup, fireEvent, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { EconomyBriefResponse, OverviewRefreshState } from "../api/macrolens";
import { fetchEconomyBrief, fetchOverviewRefresh, requestOverviewRefresh } from "../api/macrolens";
import { useOverviewRefresh } from "./useOverviewRefresh";

vi.mock("../api/macrolens",()=>({fetchEconomyBrief:vi.fn(),fetchOverviewRefresh:vi.fn(),requestOverviewRefresh:vi.fn()}));
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
