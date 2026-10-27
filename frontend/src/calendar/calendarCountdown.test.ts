import {afterEach,expect,test} from 'vitest';
import {setLanguage} from '../i18n/language';
import {countdownText,countdownDelay} from './calendarAgenda';
const now=new Date('2026-10-27T12:00:00Z');
afterEach(()=>setLanguage('en'));
test.each([
 [169*60+27,'In 7 days','Za 7 dni'],[48*60,'In 2 days','Za 2 dni'],[24*60,'In 1 day','Za 1 dzień'],
 [135,'In 2 hours 15 minutes','Za 2 godz. 15 min'],[61,'In 1 hour 1 minute','Za 1 godz. 1 min'],
 [27,'In 27 minutes','Za 27 min'],[1,'In 1 minute','Za 1 min'],[.5,'In less than a minute','Za mniej niż minutę'],
])('remaining %s minutes has natural EN/PL wording',(minutes,en,pl)=>{
 for(const [language,expected] of [['en',en],['pl',pl]] as const){setLanguage(language);expect(countdownText(now.getTime()+minutes*60000,now)).toBe(expected);}
});
test('uses full days and minutes without rounding across thresholds',()=>{
 expect(countdownText(now.getTime()+86400000-1,now)).toBe('In 23 hours 59 minutes');
 expect(countdownText(now.getTime()+3600000-1,now)).toBe('In 59 minutes');
 expect(countdownText(now.getTime()+60000-1,now)).toBe('In less than a minute');
 expect(countdownText(now.getTime(),now)).toBeNull();expect(countdownText(Infinity,now)).toBeNull();
});
test('updates only when the displayed precision or next release changes',()=>{
 expect(countdownDelay(now.getTime()+(169*60+27)*60000,now)).toBe((60+27)*60000+1);
 expect(countdownDelay(now.getTime()+135*60000+15000,now)).toBe(15001);
 expect(countdownDelay(now.getTime()+30000,now)).toBe(30000);
 expect(countdownDelay(Infinity,now)).toBeNull();
});
