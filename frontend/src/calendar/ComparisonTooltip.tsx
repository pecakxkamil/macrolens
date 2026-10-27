import {useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import type {Comparison} from './calendarComparisons';

export function ComparisonTooltip({comparison}:{comparison:Comparison}){
 const [open,setOpen]=useState(false),[position,setPosition]=useState({left:0,top:0});
 const trigger=useRef<HTMLButtonElement>(null),popup=useRef<HTMLSpanElement>(null),id=useId();
 useEffect(()=>{
  if(!open)return;
  const outside=(event:PointerEvent)=>{if(!trigger.current?.contains(event.target as Node)&&!popup.current?.contains(event.target as Node))setOpen(false);};
  document.addEventListener('pointerdown',outside);
  return()=>document.removeEventListener('pointerdown',outside);
 },[open]);
 useLayoutEffect(()=>{
  if(!open)return;
  const place=()=>{if(!trigger.current||!popup.current)return;const r=trigger.current.getBoundingClientRect(),p=popup.current.getBoundingClientRect();setPosition({left:Math.max(12,Math.min(r.left+r.width/2-p.width/2,innerWidth-p.width-12)),top:Math.max(12,r.bottom+p.height+8<innerHeight?r.bottom+6:r.top-p.height-6)});};
  place();window.addEventListener('resize',place);window.addEventListener('scroll',place,true);
  return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);};
 },[open]);
 return <span className={`agenda-comparison agenda-comparison--${comparison.tone}`} onMouseEnter={()=>setOpen(true)} onMouseLeave={()=>setOpen(false)}>
  <button ref={trigger} type="button" aria-describedby={open?id:undefined} aria-expanded={open} onFocus={()=>setOpen(true)} onBlur={()=>setOpen(false)} onClick={()=>setOpen(true)} onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();setOpen(false);}}}>{comparison.text}</button>
  {open?<span ref={popup} id={id} role="tooltip" className="agenda-comparison-tooltip" style={position}>{comparison.explanation}</span>:null}
 </span>;
}
