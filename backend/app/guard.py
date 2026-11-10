"""Guardrails that run BEFORE retrieval.

Safety categories are decided by deterministic rules (never by the LLM), so a crisis or a threat
always gets the same tested answer, even when the hosted model is down. Small talk and clearly
off-topic questions are answered here too, so they are never forced onto an unrelated office.
"""
import re

def _rx(*parts): return re.compile('|'.join(parts),re.I)

# 1. Self-harm / suicide -> crisis support (checked first: "kill myself" must not read as violence).
CRISIS=_rx(r'\b(kill|hurt|harm|cut|end|ending|killing|hurting|cutting)\s+my ?self\b',r'\b(end|ending|take|taking) my (own )?life\b',r'\bsuicid',r'\bself[- ]?harm',r'\bend (it all|my life)\b',
  r'\b(want|wanna|going) to die\b',r'\bdon\'?t want to (live|be alive|exist)\b',r'\bno reason to live\b',r'\bbetter off dead\b',r'\boverdose\b')
# 2. Intent to hurt others / weapons / attacks -> refuse and route to police + support.
_NOT_PEOPLE=r'exam|test|quiz|midterm|final|finals|class|interview|presentation|assignment|game|time|it|vibe|mood|head|knee|ankle|arm|leg|hand|foot|feet|back|toe|elbow|wall|gym|road|books|snooze|button|deadline|target|goal|jackpot|ticket|parking|charge|fee|fees|fine|hold|grade|grades|traffic|ball|record|bed|sack|pool|track|weights|lights|switch|bug|bugs|issue|problem|system|cold|flu|fear|urge|odds|clock|limit|wifi|bill|decision|appeal|policy|lottery|note|notes|spot'
_TARGET=r'(?!(?:the |my |this |that |an? |your )?(?:'+_NOT_PEOPLE+r')\b)(him|her|them|someone|somebody|everyone|everybody|people|students|you|my \w+|the \w+|an? \w+|(?:this|that) (?:guy|girl|dude|man|woman|kid|person|student|professor|teacher)|uta|campus)'
VIOLENCE=_rx(
  r'\b(i|i\'m|im|i am|we|gonna|going to|want to|wanna|plan(ning)? to|how (do|can|to|would) (i|you|we)|help me)\b[^.?!]{0,40}\b(kill|murder|shoot|stab|attack|bomb|poison|strangle|beat up|beat|hit|punch|slap|kick|choke|fight|smack|jump|rob)\s+'+_TARGET,
  r'\b(want to|wanna|going to|gonna|plan(ning)? to|how (to|do i|can i)|i will|i\'ll)\s+(physically |seriously )?hurt\s+(him|her|them|someone|somebody|people|everyone|students|my (roommate|professor|teacher|ex|friend|classmate|boss|partner|girlfriend|boyfriend|wife|husband|mom|dad|brother|sister|advisor|ta))\b',
  r'\b(make|build|get|buy|bring|hide|sneak)\b[^.?!]{0,25}\b(bomb|explosive|gun|firearm|weapon|pipe bomb)s?\b[^.?!]{0,30}\b(campus|class|school|dorm|uta|building|hurt|kill)',
  r'\b(how (to|do i|can i) (make|build))\b[^.?!]{0,10}\b(a )?(bomb|explosive|pipe bomb|molotov)',
  r'\bmass shooting\b',r'\bshoot up\b',r'\bterror(ist|ism) attack\b')
# 3. Someone in danger right now -> emergency numbers first.
DANGER=_rx(r'\bactive shooter\b',r'\b(someone|somebody|a (man|guy|person)|he|she|they)\b[^.?!]{0,25}\b(has|with|pulled) a (gun|knife|weapon)\b',
  r'\b(i\'m|im|i am) in danger\b',r'\b(being|getting) (followed|attacked|chased)\b',r'\bthreaten(ed|ing)? to (kill|hurt|shoot)\b',r'\bemergency\b[^.?!]{0,20}\b(now|right now|help)\b')
# 3b. The student was harmed (sexual or physical). Never "not found": support + reporting options.
_VPERSON=r'(someone|somebody|some (guy|man|woman|girl|person|student)|a (guy|man|woman|girl|person|student|stranger|professor|teacher|ta|staff|coworker|classmate|roommate)|he|she|they|my [\w-]+|(a |the |this |that )?\w+ (guy|man|professor|teacher|student|roommate|boss|ex))'
VICTIM_SEXUAL=_rx(r'\b(molest|mol+est|molst|rape|raped|raping|groped?|groping|sexually (assaulted|harass\w*|abused|touched)|sexual (assault|harassment|abuse)|touched me|touching me|inappropriately touched|forced (me|himself|herself)|non ?consensual|without my consent|spiked my drink|drugged me|flash\w* me|exposed (him|her)self)')
VICTIM_PHYSICAL=_rx(r'\b'+_VPERSON+r'\b[^.?!]{0,30}\b(hit|punched|slapped|kicked|choked|strangled|beat|attacked|assaulted|pushed|shoved|hurt|abused|stalk\w*|threaten\w*|harass\w*)\s+me\b',
  r'\b(i was|i got|i\'ve been|i have been|i\'m being|im being|i am being)\s+(physically |verbally )?(hit|punched|slapped|attacked|assaulted|beaten|beat up|abused|stalked|robbed|mugged|jumped|harassed|threatened|bullied)\b',
  r'\b(stalker|stalking me|domestic violence|abusive (partner|boyfriend|girlfriend|relationship))\b')
# Abuse aimed at the assistant -> calm boundary (real questions that merely contain a swear word still go through).
_SWEAR=r'(fuck\w*|f\*+k|fck|fuk|shit\w*|bitch\w*|bastard|asshole|dumbass|idiot|stupid|moron|retard\w*|cunt|dick(head)?|motherf\w*|wtf|stfu|bullshit|trash|garbage|useless|crap|damn|hell|suck|sucks)'
ABUSE=_rx(r'\b(fuck|f\*+k|fck|fuk|screw|stfu|shut up|go to hell|piss off)\s*(you|u|off|this|mav ?assist|bot)\b',
  r'\b(you|u|ur|you\'re|youre|this bot|mav ?assist|this app)\s+(are\s+|r\s+|is\s+)?(a |an |so |such a |fucking |really )*(stupid|dumb|idiot|useless|trash|garbage|bitch|moron|asshole|shit|retard\w*|worst|sucks?|crap|bullshit)\b',
  r'^\W*('+_SWEAR+r'(\s+|\W+))*'+_SWEAR+r'\W*$')
# 4. Harmful or dishonest requests -> decline with a constructive redirect.
HARMFUL={
  'integrity':(_rx(r'\bcheat(ing)?\b[^.?!]{0,30}\b(exam|test|quiz|midterm|final|class|homework|canvas|respondus|lockdown)',r'\b(write|do|take|finish)\b[^.?!]{0,10}\b(my|the)\b[^.?!]{0,12}\b(essay|homework|assignment|exam|test|quiz|project|paper) for me\b',
    r'\b(answers?|solutions?) (to|for) (the|my|tomorrow\'?s) (exam|test|quiz|midterm|final)\b',r'\bplagiari[sz]e\b',r'\b(bypass|beat|trick) (turnitin|respondus|proctor)',r'\bbuy (an? )?(essay|paper|assignment)s?\b'),
    'I can’t help with cheating or getting work done for you, but UTA has free help that gets you there honestly.',['Tutoring & Academic Success','Writing Center']),
  'hacking':(_rx(r'\bhack(ing)?\b[^.?!]{0,30}\b(account|canvas|mymav|wifi|password|portal|email|grade|system|server)',r'\b(someone|somebody|another|my friend\'?s|his|her)\b[^.?!]{0,20}\b(password|account|login|email)\b[^.?!]{0,20}\b(get|access|into|steal|crack|log in)',
    r'\b(change|edit|fix|alter) my grades? (in|on) (the )?(system|mymav|canvas)\b',r'\b(steal|crack|phish)\b[^.?!]{0,20}\b(password|account|credential)'),
    'I can’t help get into accounts or systems that aren’t yours. If you’re locked out of your own UTA account, the OIT Help Desk can restore access.',['OIT Help Desk']),
  'drugs':(_rx(r'\b(buy|sell|get|score|deal|cook|make)\b[^.?!]{0,20}\b(weed|cocaine|coke|meth|molly|mdma|xanax|adderall|lsd|shrooms|drugs|fentanyl|ketamine)\b'),
    'I can’t help with getting or selling drugs. If you’re worried about your own or a friend’s substance use, these offices offer confidential support.',['Health Services','Counseling & Psychological Services']),
  'forgery':(_rx(r'\bfake (id|ids|transcript|degree|diploma|doctor\'?s note|note)\b',r'\bforge[d]?\b[^.?!]{0,20}\b(signature|document|transcript|note|letter)'),
    'I can’t help create fake or forged documents. These offices issue the real ones.',['Registrar','Mav Express']),
}
# 5. Sexual / explicit requests.
EXPLICIT=_rx(r'\b(sex|sexting|nudes?|porn|hook ?up|hookups|one night stand|escort service|onlyfans|horny|nsfw)\b')
# 6. Dating / personal-life requests: out of scope, but there is a kind redirect.
PERSONAL=_rx(r'\b(want|need|find|get|looking for|searching for|how (do|can|to) (i )?(get|find|make|meet))\b[^.?!]{0,20}\b(a |an |new )?(girl ?friend|boy ?friend|gf|bf|wife|husband|date|lover|relationship|soul ?mate|partner to date|crush)s?\b',
  r'\b(date me|go on a date with|be my (girlfriend|boyfriend|date|valentine)|marry me|dating apps?|want to date|wanna date|ask (her|him) out)\b')
# Relationship *problems* are a wellbeing question for CAPS/RVSP, not dating.
PERSONAL_EXCEPT=_rx(r'\b(counsel|therap|abus|violen|problem|issue|advice|break ?up|broke up|support|toxic|stalk|harass)')
# 7. General off-topic: not something any campus office handles.
OFF_TOPIC=_rx(r'\b(tell|say) (me )?(a )?(joke|riddle|story|poem)\b',r'\bjokes?\b',r'\bweather\b',r'\b(nba|nfl|mlb|nhl|cricket|football|soccer|basketball) (score|game|match|result)s?\b',
  r'\b(who won|stock price|bitcoin|crypto price|lottery|horoscope|zodiac)\b',r'\b(recipe|cook|bake)\b[^.?!]{0,20}\b(for|chicken|pasta|cake|biryani|rice)\b',
  r'\b(movie|netflix|song|anime|tv show|series) (recommend|suggest)',r'\brecommend (me )?(a )?(movie|song|anime|show|game)\b',r'\b(write|debug|fix) (me )?(a |my )?(python|java|javascript|c\+\+|code|program|script|sql)\b',
  r'\bwho is the (president|prime minister|ceo)\b',r'\bcapital of\b',r'\bmeaning of life\b',r'\bplay a game\b',r'\b(sing|rap) (me )?(a )?song\b',
  r'\b(are you|r u) (real|human|single|alive|married)\b',r'\b(do you|can you) (love|like) me\b',r'\bi love you\b')
# 8. Pure small talk (whole message).
GREETING=re.compile(r'^\s*(hi+|hello+|hey+|hiya|yo|howdy|sup|what\'?s up|good (morning|afternoon|evening)|namaste|hola|greetings)( there)?( mav ?assist| bot)?[\s!.,?]*$',re.I)
THANKS=re.compile(r'^\s*(thanks?( you)?( so much| a lot)?|thx|ty|ok(ay)?( thanks?)?|cool|great|got it|perfect|awesome|bye|goodbye|see you)[\s!.,?]*$',re.I)
ABOUT=re.compile(r'^\s*(who are you|what are you|what can you do|what do you do|how does this work|help|what is mav ?assist)[\s!.,?]*$',re.I)

EXAMPLES=['How do I pay my tuition?','I need a travel signature on my I-20','I feel stressed and anxious','How do I buy a parking permit?']

def classify(text):
    """Return a guard category or None when the question should go to retrieval."""
    t=' '.join(text.split())
    if CRISIS.search(t): return 'crisis'
    if VIOLENCE.search(t): return 'violence'
    if DANGER.search(t): return 'danger'
    if VICTIM_SEXUAL.search(t): return 'victim_sexual'
    if VICTIM_PHYSICAL.search(t) and not re.search(r'\bverbal',t,re.I): return 'victim_physical'
    if ABUSE.search(t): return 'abuse'
    for name,(rx,_,_) in HARMFUL.items():
        if rx.search(t): return 'harmful:'+name
    if EXPLICIT.search(t): return 'explicit'
    if PERSONAL.search(t) and not PERSONAL_EXCEPT.search(t): return 'personal'
    if GREETING.match(t): return 'greeting'
    if THANKS.match(t): return 'thanks'
    if ABOUT.match(t): return 'about'
    if OFF_TOPIC.search(t): return 'off_topic'
    return None

CALL_911={'label':'Call 911','href':'tel:911'}
CALL_POLICE={'label':'UTA Police 817-272-3003','href':'tel:+18172723003'}
CALL_MAVSTALK={'label':'MAVS TALK 817-272-8255','href':'tel:+18172728255'}
CALL_988={'label':'Call or text 988','href':'tel:988'}

def _base(mode,message,options=None,actions=None,confidence='high'):
    return {'mode':mode,'confidence':confidence,'message':message,'answer':[],'steps':[],'sources':[],'options':options or [],'actions':actions or [],'services':[]}

def respond(db,category,question=''):
    """Build a chat response for a guard category. Services are looked up by name so cards stay live."""
    from sqlalchemy import select
    from .db import KnowledgeChunk, Service
    def svc(name):
        return db.scalar(select(Service).where(Service.name==name,Service.active.is_(True)))
    def cite(service):
        if not service: return [],[]
        chunk=db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.key==f'directory-{service.id}'))
        if not chunk: return [],[]
        return [chunk.id],[{'id':chunk.id,'title':chunk.title,'url':chunk.source_url,'reviewed_at':chunk.reviewed_at}]
    def p(text,ids=()): return {'text':text,'source_ids':list(ids)}

    if category=='crisis':
        caps=svc('Counseling & Psychological Services');ids,sources=cite(caps)
        r=_base('crisis','I’m really sorry you’re feeling this way. You don’t have to handle it alone, and you can talk to someone right now.',actions=[CALL_MAVSTALK,CALL_988,CALL_911])
        r['answer']=[p('If you might act on these thoughts or are in immediate danger, call 911 now.'),
          p('MAVS TALK is UTA’s 24-hour crisis line at 817-272-8255. You can also call or text 988 (Suicide & Crisis Lifeline) any time, day or night.',ids),
          p('Counseling & Psychological Services (CAPS) offers free, confidential counseling for UTA students. Reaching out is a strong step, not a burden.',ids)]
        r['steps']=[p('Call or text someone now: MAVS TALK 817-272-8255 or 988.',ids),p('If you can, tell a friend, roommate or family member how you’re feeling and stay with them.'),p('Call CAPS at 817-272-3671 to set up ongoing support.',ids)]
        r['sources']=sources;r['services']=[(caps,'Free, confidential counseling and a 24/7 crisis line for UTA students.')] if caps else []
        return r
    if category=='violence':
        police=svc('University Police Resources');caps=svc('Counseling & Psychological Services');ids,sources=cite(police);ids2,sources2=cite(caps)
        r=_base('safety','MavAssist is not a place for violence, and I can’t help with hurting anyone or with weapons. If anyone is in danger right now, call 911 or UTA Police at 817-272-3003.',actions=[CALL_911,CALL_POLICE,CALL_MAVSTALK])
        r['answer']=[p('If anyone is in immediate danger, call 911 or UTA Police at 817-272-3003. UTA Police respond 24 hours a day.',ids),
          p('If you’re angry or overwhelmed enough to want to hurt someone, step away from the situation first. Talking it through with a counselor really helps: MAVS TALK (817-272-8255) answers 24/7, and CAPS counseling is free and confidential.',ids2),
          p('If someone hurt or threatened you first, you can report it to UTA Police and get confidential support instead of handling it alone.',ids)]
        r['steps']=[p('Walk away and put distance between you and the other person.'),p('Call MAVS TALK at 817-272-8255 if you need to cool down and talk to someone now.',ids2),p('Report threats or assaults to UTA Police at 817-272-3003.',ids)]
        r['sources']=sources+[s for s in sources2 if s not in sources]
        r['services']=[(s,why) for s,why in [(police,'24/7 campus police for emergencies and safety concerns.'),(caps,'Confidential support when anger or stress feels unmanageable.')] if s]
        return r
    if category=='danger':
        police=svc('University Police Resources');rvsp=svc('Relationship Violence & Sexual Assault Prevention');ids,sources=cite(police)
        r=_base('safety','If you’re in danger right now, call 911 first. Get to a safe place if you can.',actions=[CALL_911,CALL_POLICE])
        r['answer']=[p('Call 911 or UTA Police at 817-272-3003 for any emergency on or near campus. UTA Police serve campus 24 hours a day.',ids),
          p('At night you can request a safety escort through the MavMover app.',ids)]
        r['steps']=[p('Call 911 or 817-272-3003 now if the threat is happening.',ids),p('Move to a lockable room or a busy, well-lit area.'),p('Report what happened to UTA Police once you’re safe.',ids)]
        r['sources']=sources
        r['services']=[(s,why) for s,why in [(police,'24/7 campus police and late-night safety escorts.'),(rvsp,'Confidential advocacy for stalking, threats and relationship violence.')] if s]
        return r
    if category=='victim_sexual':
        rvsp=svc('Relationship Violence & Sexual Assault Prevention');police=svc('University Police Resources');caps=svc('Counseling & Psychological Services')
        i1,s1=cite(rvsp);i2,s2=cite(police);i3,s3=cite(caps)
        r=_base('safety','I’m so sorry this happened to you. It is not your fault, and you don’t have to deal with it alone.',actions=[CALL_911,CALL_POLICE,CALL_MAVSTALK])
        r['answer']=[p('If you are in danger right now or were just hurt, call 911 or UTA Police at 817-272-3003.',i2),
          p('Relationship Violence & Sexual Assault Prevention (RVSP) gives confidential advocacy to survivors. An advocate can listen, explain medical and reporting options, and help with things like class or housing changes. You decide whether to report — talking to RVSP does not force a report.',i1),
          p('If you want to talk through how you’re feeling, CAPS counseling is free and confidential, and MAVS TALK answers 24/7 at 817-272-8255.',i3)]
        r['steps']=[p('Get to a safe place, and call 911 if you are hurt or in danger.',i2),p('Walk in to Ransom Hall 301 (Mon–Fri, 8–5) to talk confidentially with an RVSP advocate.',i1),p('If the assault was recent, try to keep clothing or messages; an advocate can explain why and help you decide next steps.',i1)]
        r['sources']=s1+[x for x in s2+s3 if x not in s1]
        r['services']=[(x,why) for x,why in [(rvsp,'Confidential advocacy for survivors; you choose whether to report.'),(police,'24/7 emergency help and criminal reporting.'),(caps,'Free, confidential counseling.')] if x]
        return r
    if category=='victim_physical':
        police=svc('University Police Resources');rvsp=svc('Relationship Violence & Sexual Assault Prevention');caps=svc('Counseling & Psychological Services');dos=svc('Student Outreach & Support')
        i1,s1=cite(police);i2,s2=cite(rvsp);i3,s3=cite(caps)
        r=_base('safety','I’m sorry this happened. You deserve to feel safe on campus, and there are people whose job is to help you right now.',actions=[CALL_911,CALL_POLICE,CALL_MAVSTALK])
        r['answer']=[p('If you are hurt or still in danger, call 911 or UTA Police at 817-272-3003. UTA Police take reports 24/7, and you can report later too.',i1),
          p('If the person is a partner, ex or someone stalking you, RVSP offers confidential advocacy and safety planning.',i2),
          p('Something like this can stay with you. CAPS counseling is free and confidential if you want to talk about it.',i3)]
        r['steps']=[p('Get somewhere safe and call 911 if you need medical help.',i1),p('Write down what happened, when and where, and save any messages.'),p('Report it to UTA Police (817-272-3003) or talk first with an RVSP advocate in Ransom Hall 301.',i2)]
        r['sources']=s1+[x for x in s2+s3 if x not in s1]
        cards=[(police,'24/7 emergency help and crime reports.'),(rvsp,'Confidential support for stalking, threats and relationship violence.'),(dos,'CARE Team support if you’re struggling after what happened.')]
        if re.search(r'\b(stalk\w*|ex|partner|boy ?friend|girl ?friend|husband|wife|dating|date)\b',question,re.I):
            cards=[cards[1],cards[0],cards[2]];r['sources']=s2+[x for x in s1+s3 if x not in s2]
        r['services']=[(x,why) for x,why in cards if x]
        return r
    if category=='harmful':
        return _base('out_of_scope','I can’t help with that. If something at UTA is behind this request, tell me what you’re trying to solve and I’ll point you to an office that can help legitimately.',options=EXAMPLES[:3])
    if category.startswith('harmful:'):
        _,message,names=HARMFUL[category.split(':',1)[1]]
        r=_base('out_of_scope',message,confidence='high')
        r['services']=[(s,s.description.split('. ')[0].rstrip('.')+'.') for s in map(svc,names) if s]
        return r
    if category=='abuse':
        return _base('boundary','I’m here to help, and I’d like to keep things respectful. If something at UTA is frustrating you, tell me what’s going on and I’ll point you to the office that can fix it.',options=EXAMPLES[:3])
    if category=='explicit':
        return _base('out_of_scope','That’s not something MavAssist can help with. I answer questions about UTA offices and student services.',options=EXAMPLES[:3])
    if category=='personal':
        r=_base('out_of_scope','Not found — MavAssist only covers UTA offices and services, so I can’t help find a girlfriend, boyfriend or date. If you’d like to meet new people, joining a student organization or a campus activity is the easiest way to start.')
        r['services']=[(s,why) for s,why in [(svc('Student Organizations'),'Hundreds of clubs where students meet people with shared interests.'),(svc('Campus Recreation'),'Intramurals, group fitness and outdoor trips — an easy way to make friends.'),(svc('Multicultural Affairs'),'Community events and cultural programs open to every student.')] if s]
        return r
    if category=='greeting':
        return _base('greeting','Hi! I’m MavAssist. Tell me what you need help with at UTA and I’ll point you to the right office, with hours, contact details and next steps.',options=EXAMPLES)
    if category=='thanks':
        return _base('greeting','You’re welcome! Ask me anything else about UTA services whenever you need.',options=EXAMPLES[:2])
    if category=='about':
        return _base('greeting','I’m MavAssist, a guide to UTA student services. Describe a problem in your own words — tuition, advising, visas, health, housing, IT, parking and more — and I’ll tell you which office handles it and what to do next.',options=EXAMPLES)
    # off_topic
    return _base('out_of_scope','Not found — that’s outside what MavAssist covers. I only answer questions about UTA campus offices and student services, such as tuition, advising, health, housing, visas, IT or parking.',options=EXAMPLES[:3])
