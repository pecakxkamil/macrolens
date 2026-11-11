export type ChangeDirection='positive'|'negative'|'neutral';

/** Numerical direction only; no economic or investment interpretation. */
export function changeDirection(value:number|bigint|null|undefined):ChangeDirection {
 if(value==null||(typeof value==='number'&&!Number.isFinite(value)))return 'neutral';
 return value>0?'positive':value<0?'negative':'neutral';
}
