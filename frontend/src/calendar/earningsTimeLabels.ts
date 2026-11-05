import {getLanguage} from '../i18n/language';

const labels={
 after_close:{en:'After US close',pl:'Po sesji USA'},
 before_open:{en:'Before US open',pl:'Przed sesją USA'},
 during_session:{en:'During US session',pl:'W trakcie sesji USA'},
 unknown:{en:'Time not confirmed',pl:'Godzina niepotwierdzona'},
 call:{en:'Call',pl:'Konferencja'},
 warsaw:{en:'Warsaw',pl:'PL'},
} as const;
export const earningsTimeLabel=(key:keyof typeof labels)=>labels[key][getLanguage()];
