import { tText, tLabel } from "../i18n/language";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { metricMetadata, type MetricKey, type MetricMetadata } from "../metricMetadata";

type InfoTooltipProps = { metricKey: MetricKey; label?: never; description?: never; trigger?: never; content?:never; bounded?:never; closable?:never } | { metricKey?: never; label: string; description: string; trigger?: string; content?:ReactNode; bounded?:boolean; closable?:boolean };
export function InfoTooltip(props: InfoTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const clickOnly = Boolean(props.bounded || props.closable);
  const [position,setPosition] = useState<{left:number;top:number;width:number}>();
  const root=useRef<HTMLSpanElement>(null), button=useRef<HTMLButtonElement>(null), content=useRef<HTMLSpanElement>(null);
  const tooltipId = useId();
  const metadata: MetricMetadata | undefined = props.metricKey ? metricMetadata[props.metricKey] : undefined;
  const show = () => {
    window.dispatchEvent(new CustomEvent("macrolens:tooltip-open", { detail: tooltipId }));
    setIsOpen(true);
  };
  const hide = () => setIsOpen(false);
  useEffect(() => {
    const otherOpened = (event: Event) => {
      if ((event as CustomEvent<string>).detail !== tooltipId) setIsOpen(false);
    };
    window.addEventListener("macrolens:tooltip-open", otherOpened);
    return () => window.removeEventListener("macrolens:tooltip-open", otherOpened);
  }, [tooltipId]);
  useEffect(() => {
    if (!clickOnly || !isOpen) return;
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [clickOnly, isOpen]);
  useLayoutEffect(()=>{
    if(!props.bounded||!isOpen)return;
    const place=()=>{
      if(!button.current||!content.current)return;
      const width=Math.min(420,window.innerWidth-32),rect=button.current.getBoundingClientRect();
      content.current.style.width=`${width}px`;
      const height=content.current.getBoundingClientRect().height;
      const left=Math.max(16,Math.min(rect.left+rect.width/2-width/2,window.innerWidth-width-16));
      const preferred=rect.bottom+8+height<=window.innerHeight-16?rect.bottom+8:rect.top-height-8;
      const top=Math.max(16,Math.min(preferred,window.innerHeight-height-16));
      setPosition({left,top,width});
    };
    place();window.addEventListener("resize",place);
    const scroll=(event:Event)=>{if(event.target instanceof Node&&content.current?.contains(event.target))return;place();};
    window.addEventListener("scroll",scroll,true);
    return()=>{window.removeEventListener("resize",place);window.removeEventListener("scroll",scroll,true);};
  },[props.bounded,isOpen,props.description]);
  function closeExplanation() {
    // Keep keyboard focus at the control that opened the popup.
    button.current?.focus({ preventScroll: true });
    hide();
  }
  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Escape") { if (clickOnly) closeExplanation(); else { hide(); event.currentTarget.blur(); } }
  }
  return (
    <span ref={root} className={`info-tooltip${props.bounded?" info-tooltip--bounded":""}${props.closable?" info-tooltip--closable":""}${clickOnly?" info-tooltip--click":""}${isOpen ? " info-tooltip--open" : ""}`}>
      <button ref={button} type="button" className="info-tooltip__trigger"
        aria-label={tLabel(props.label ?? `About ${metadata!.label}`)} aria-describedby={tooltipId} aria-expanded={isOpen}
        onClick={() => { if (isOpen) closeExplanation(); else show(); }}
        onKeyDown={handleKeyDown}>{props.trigger ?? "i"}</button>
      <span ref={content} id={tooltipId} role="tooltip" className="info-tooltip__content"
        onKeyDown={props.bounded || props.closable ? event=>{if(event.key==="Escape"){event.stopPropagation();closeExplanation();}}:undefined}
        style={props.bounded?{...position,position:"fixed",right:"auto"}:undefined}>
        {(props.bounded || props.closable) && isOpen ? <button type="button" className="info-tooltip__close"
          aria-label={tLabel("Close explanation")} onClick={closeExplanation}><span aria-hidden="true">×</span></button> : null}
        {props.content ?? <span>{tText(props.description ?? metadata!.description)}</span>}
        {metadata?.methodology ? <span>{tText(metadata.methodology)}</span> : null}
      </span>
    </span>
  );
}
