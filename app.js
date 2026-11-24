/* ══════════════════════════════════════════════════════════════
   NEUNGNOL STAY · 능놀스테이 — 예약 견적 웹앱
   · 객실 2개(3층 헤윰 / 6층 오롯) 날짜별 요금·마감 상태를
     네이버 예약 공개 GraphQL(naver-sync.py) 결과로 표시한다.
   · 실제 예약·결제는 네이버 예약으로 넘긴다(이 페이지는 견적 안내).
   ══════════════════════════════════════════════════════════════ */

/* ── i18n ── */
const RATES = { usd: 1346.13, twd: 40.45 };
let LANG = 'ko';
try { LANG = localStorage.getItem('nn_lang') || 'ko'; } catch (e) {}
function L(ko, en, zh) { return LANG === 'en' ? en : (LANG === 'zh' ? zh : ko); }
function fxText(krw) {
  if (!krw) return '';
  const usd = Math.round(krw / RATES.usd / 10) * 10, twd = Math.round(krw / RATES.twd / 10) * 10;
  const u = 'US$' + usd.toLocaleString('en-US'), t = 'NT$' + twd.toLocaleString('en-US');
  return L('≈ ' + u + ' · ' + t + ' (참고 환율 · 실제 결제는 KRW 기준)',
           '≈ ' + u + ' · ' + t + ' (reference rate; charged in KRW)',
           '≈ ' + u + ' · ' + t + '（參考匯率，實際以韓元結帳）');
}

const DICT = { en: {}, zh: {} };
DICT.en = {
  '예약':'Book','객실':'Rooms','사진':'Photos','후기':'Reviews','위치·이용안내':'Location & info','위치':'Location',
  '예약하기':'Book now','바로 예약하기':'Book now','요금 확인':'Check rate',
  '체크인':'Check-in','체크아웃':'Check-out','인원':'Guests','날짜 선택':'Select date',
  '성인 8명 (기준)':'8 adults (base)',
  '기준 8인 · 최대 12인':'Base 8 · max 12','같은 건물, 다른 층':'Same building, different floors',
  '광안리 바다 앞 60평, ':'60 pyeong by the Gwangalli sea, ',
  '3층 헤윰 · 6층 오롯 — 같은 건물, 각 60평대 독채 오션뷰 풀빌라. 비치뷰 자쿠지·키즈룸·100인치 빔 프로젝터.':
    'Heyum on the 3rd floor and Orot on the 6th — two private 60-pyeong ocean-view pool villas in one building. Beach-view jacuzzi, kids’ room, 100-inch projection screen.',
  '8인 기준 · 최대 12인':'Base 8 · max 12 guests','침실 3 · 퀸베드 5':'3 bedrooms · 5 queen beds',
  '객실을 고르면 날짜별 요금이 바로 계산됩니다':'Pick a room and see night-by-night rates',
  '네이버 예약 달력과 동기화 중…':'Syncing with the Naver Booking calendar…',
  '입실 15:00 · 퇴실 11:00 · 60평대':'In 15:00 · Out 11:00 · 60 pyeong','입실 16:00 · 퇴실 12:00 · 60평대':'In 16:00 · Out 12:00 · 60 pyeong',
  '입실 15:00 · 퇴실 11:00':'In 15:00 · Out 11:00','입실 16:00 · 퇴실 12:00':'In 16:00 · Out 12:00',
  '예약 가능':'Available','선택':'Selected','예약 마감':'Booked out','숫자 아래는 1박 요금':'Rate under each date is per night',
  '숙박':'Stay','예약 견적':'Your quote','예상 합계':'Estimated total','1박 요금':'Nightly rate',
  '달력에서 체크인·체크아웃 날짜를 선택해 주세요.':'Choose your check-in and check-out dates on the calendar.',
  '네이버 톡톡':'Naver TalkTalk','전화 걸기':'Call','인스타그램':'Instagram',
  '예약과 결제는 선택한 객실의 네이버 예약 화면에서 진행됩니다. 이 견적은 참고 금액이며, 최종 금액·할인·쿠폰은 네이버 예약 화면에서 확정됩니다.':
    'Booking and payment happen on Naver Booking for the room you chose. This quote is for reference; the final amount, discounts and coupons are settled on the Naver Booking screen.',
  '* 요금·마감 상태는 네이버 예약 달력에서 실시간으로 읽어옵니다. 마감된 날짜도 체크아웃일로는 선택할 수 있습니다.':
    '* Rates and closures are read live from the Naver Booking calendar. A closed date can still be your check-out day.',
  '같은 건물, 두 개의 60평 독채':'One building, two 60-pyeong private houses',
  '3층 헤윰과 6층 오롯은 같은 건물의 서로 다른 층에 있는 별개의 독채입니다. 두 객실 모두 광안리 바다가 통창으로 들어옵니다.':
    'Heyum (3F) and Orot (6F) are separate private houses on different floors of the same building. Both look straight out over the Gwangalli sea.',
  '실제 숙소 사진':'Photos of the house','사진 25장 모두 보기':'See all 25 photos',
  '거실 · 자쿠지 · 침실 3 · 욕실 2 · 키즈룸 · 주방 · 도면까지 공간과 객실별로 골라 보세요.':
    'Living room, jacuzzi, three bedrooms, two bathrooms, kids’ room, kitchen and floor plans — browse by space or by room.',
  '광안리에서 가장 넓은 60평':'The widest 60 pyeong in Gwangalli',
  '광안리 해변 도보 1분':'A minute’s walk from Gwangalli beach',
  '통창으로 광안대교와 바다가 바로 보입니다. 해바라기광장·민락회센터·민락어패류주차장이 도보 1분 거리입니다.':
    'The Gwangandaegyo bridge and the sea fill the windows. Haebaragi Plaza, Millak market and the Millak parking building are a minute away on foot.',
  '비치뷰 자쿠지':'Beach-view jacuzzi',
  '거실 창가에 놓인 자쿠지에서 광안대교 노을과 밤바다를 그대로. 온수 이용에 별도 요금은 없습니다.':
    'The jacuzzi by the living-room window opens onto the bridge at sunset and the sea at night. Hot water is included.',
  '키즈룸 무료 대여':'Kids’ room, free',
  '정글짐·트램폴린·흔들그네·미끄럼틀과 32인치 좌식 게임기. 유아동이 있는 예약에서 무료로 열어 드립니다.':
    'Climbing frame, trampoline, swing and slide plus a 32-inch floor console — opened free for bookings with young children.',
  '100인치 빔 프로젝터':'100-inch projection screen',
  '거실 100인치 빔 프로젝터와 50인치 TV. 유튜브·넷플릭스를 그대로 즐길 수 있습니다.':
    'A 100-inch projector and a 50-inch TV in the living room — YouTube and Netflix ready.',
  '60평대 독채 · 최대 12인':'A 60-pyeong house for up to 12',
  '기준 8인·최대 12인. 침실 3(퀸베드 5)·욕실 2·화장대 3개로 단체·가족 여행에 맞습니다.':
    'Base 8, up to 12. Three bedrooms with five queen beds, two bathrooms and three vanities — built for families and groups.',
  '★ 5.0 · 리뷰 125':'★ 5.0 · 125 reviews',
  '네이버 방문자 리뷰 64건 + 블로그·카페 리뷰 61건. 대표 한 줄 “세심한 배려로 완성된 룸 컨디션”.':
    '64 Naver visitor reviews plus 61 blog and cafe reviews. Their headline: “a room finished with thoughtful care”.',
  '작위적인 화려함보다,':'Rather than staged glamour,','기본에 충실한 따뜻한 공간':'a warm space true to the basics',
  '부산 수영구 민락수변로 13, 3층과 6층에 자리한 ':'Two private ocean-view pool villas of about 60 pyeong each, on the 3rd and 6th floors of 13 Millaksubyeon-ro, Suyeong-gu, Busan. ',
  '각 60평대 독채 오션뷰 풀빌라':'',
  '입니다. 현관을 지나면 광안리 바다가 통창으로 들어오는 거실과 비치뷰 자쿠지, 침실 세 개가 이어집니다. 아이가 있다면 정글짐·트램폴린·미끄럼틀이 있는 키즈룸을 무료로 열어 드리고, 유아식기·하이체어·젖병소독기·아기침대 안전가드도 요청하시면 준비해 드립니다.':
    'Inside, a living room opens to the Gwangalli sea through full-width windows, with the jacuzzi and three bedrooms beyond. For families we open the kids’ room free of charge and prepare children’s tableware, a high chair, a bottle steriliser and bed rails on request.',
  '유형':'Type','주소':'Address','인원':'Guests','침실':'Bedrooms','욕실':'Bathrooms','입·퇴실':'Check-in / out','주차':'Parking','위생':'Hygiene',
  '독채 · 60평대 · 오션뷰 풀빌라':'Private house · 60 pyeong · ocean-view pool villa',
  '부산광역시 수영구 민락수변로 13, 3층(헤윰)·6층(오롯)':'13 Millaksubyeon-ro, Suyeong-gu, Busan — 3F (Heyum) · 6F (Orot)',
  '기준 8인 / 최대 12인 (초과 1인당 30,000원 · 24개월 미만 무료)':'Base 8 / max 12 (₩30,000 per extra guest · under 24 months free)',
  '침실 3 — 퀸사이즈 베드 총 5개':'3 bedrooms — five queen beds',
  '욕실 2 · 화장대 3 · 헤어드라이기 3':'2 bathrooms · 3 vanities · 3 hairdryers',
  '3층 헤윰 15:00 / 11:00 · 6층 오롯 16:00 / 12:00 (얼리 체크인·레이트 체크아웃 불가)':'Heyum 3F 15:00 / 11:00 · Orot 6F 16:00 / 12:00 (no early check-in or late check-out)',
  '무료 1대 (도보 1분 민락회센터·민락어패류주차장) — 차종·차번 사전 등록, 주차 불가 차종 있음':'One car free (Millak market / seafood parking, 1 min on foot) — register car model and plate in advance; some vehicles cannot park',
  '세스코 멤버스 · 최근 통합방제 2026.11':'CESCO members · last full treatment Nov 2026',
  '비치뷰 자쿠지':'Beach-view jacuzzi','50인치 TV · 넷플릭스':'50-inch TV · Netflix','키즈룸':'Kids’ room',
  '32인치 좌식 게임기':'32-inch floor console','얼음정수기':'Ice water purifier','커피머신':'Coffee machine','전기밥솥':'Rice cooker',
  '인덕션 · 조리도구':'Induction hob & cookware','식기 · 와인잔':'Tableware & wine glasses','드럼세탁기':'Front-load washer','공기청정기':'Air purifier',
  '유아하이체어':'High chair','젖병소독기':'Bottle steriliser','아기침대 안전가드':'Bed rails','유아식기':'Children’s tableware',
  '와이파이':'Wi-Fi','무료 주차 1대':'One free parking space','금연':'No smoking','반려동물 불가':'No pets',
  '바다가 통창으로 들어오는 거실과 다이닝':'Living room and dining with the sea in the windows',
  '요금 · 할인 안내':'Rates & discounts',
  '아래 요금은 네이버 예약 달력에서 확인한 2026년 11~12월 실제 1박 요금 범위입니다. 날짜별 정확한 금액은 위 달력에서 확인하세요.':
    'The ranges below are the actual nightly rates read from the Naver Booking calendar for Nov–Dec 2026. Check the calendar above for the exact rate of a date.',
  '객실':'Room','입실 / 퇴실':'In / out','1박 요금':'Per night','예약 리뷰':'Booking reviews','기준 인원':'Base guests','인원 추가':'Extra guests',
  '연박 할인':'Long-stay discount','네이버 쿠폰':'Naver coupon','8인 (최대 12인)':'8 guests (max 12)',
  '1인당 30,000원 · 24개월 미만 영유아 무료':'₩30,000 per guest · under 24 months free',
  '2박 이상 예약 시 추가 1박당 50,000원 할인':'₩50,000 off each extra night from the second night',
  '네이버 예약 10,000원 할인 쿠폰 (예약 화면에서 다운로드)':'₩10,000 Naver Booking coupon (download on the booking screen)',
  '* 숙박하지 않는 방문객도 1인당 30,000원이 발생합니다. 얼리 체크인·레이트 체크아웃은 운영하지 않습니다. Npay 최대 5% 적립과 Npay 카드 이벤트가 진행 중입니다(네이버 예약 기준).':
    '* Visitors who do not stay are also charged ₩30,000 each. No early check-in or late check-out. Npay earns up to 5% and an Npay card promotion is running (per Naver Booking).',
  '무료 대여 · 요청 물품':'Free rentals & on request','무료':'Free','아기 하이체어':'High chair','유팡 젖병소독기':'Yufang bottle steriliser',
  '유아 샴푸':'Children’s shampoo','아기침대 안전가드 (2SET)':'Bed rails (2 sets)','유아동 배게':'Children’s pillows','유아식기':'Children’s tableware',
  '키즈룸은 상시 개방이 아니라 유아동이 있는 예약에서 옵션을 선택하실 때 열어 드립니다. 필요 물품은 예약 시 요청해 주세요.':
    'The kids’ room is not always open; it is unlocked when a booking with young children selects the option. Please ask for the items you need when you book.',
  '네이버 방문자 리뷰 ':'Naver visitor reviews ',' · 블로그·카페 리뷰 ':' · blog & cafe reviews ',' — 합계 ':' — ','건 · 평점 5.0':' in total · rated 5.0',
  '객실별 예약 리뷰 — 헤윰 28건 · 오롯 21건 · 방문자 사진·영상 155건':'Per-room booking reviews — Heyum 28 · Orot 21 · 155 visitor photos and videos',
  '네이버 플레이스 리뷰 전체 보기 ↗':'See all Naver Place reviews ↗',
  '광안리 해변 바로 앞':'Right by Gwangalli beach',
  '도보 거리':'On foot','문의':'Contact','예약':'Booking',
  '광안리해수욕장 도보 1분 · 해바라기광장 · 민락회센터 1분 · 민락어패류주차장 1분':'Gwangalli beach 1 min · Haebaragi Plaza · Millak market 1 min · seafood parking 1 min',
  '무료 1대 · 도보 1분 민락회센터·민락어패류주차장 1대 무료 — 차종·차번 사전 등록 필요, 주차 불가 차종 있음':'One car free · one free space at Millak market / seafood parking a minute away — register car model and plate in advance; some vehicles cannot park',
  '0507-1429-2309 · 네이버 톡톡 · 인스타그램 @neungnol_stay':'0507-1429-2309 · Naver TalkTalk · Instagram @neungnol_stay',
  '네이버 예약 (3층 헤윰 · 6층 오롯)':'Naver Booking (Heyum 3F · Orot 6F)',
  '구글 지도에서 크게 보기 ↗':'Open in Google Maps ↗','네이버 지도 ↗':'Naver Map ↗','길찾기 ↗':'Directions ↗',
  '이용 안내':'Good to know',
  '체크인·체크아웃 시간이 객실마다 다른가요?':'Do check-in and check-out differ by room?',
  '네. ':'Yes. ','3층 헤윰은 입실 15:00 / 퇴실 11:00':'Heyum on the 3rd floor checks in at 15:00 and out at 11:00',
  ', ':', ','6층 오롯은 입실 16:00 / 퇴실 12:00':'Orot on the 6th floor checks in at 16:00 and out at 12:00',
  '입니다. 청소와 다음 게스트를 위해 퇴실 시간은 꼭 지켜 주세요. 얼리 체크인·레이트 체크아웃은 운영하지 않습니다.':' Please keep to the check-out time for cleaning and the next guests. Early check-in and late check-out are not available.',
  '인원 추가 요금은 얼마인가요?':'What is the charge for extra guests?',
  '기준 8인, 최대 12인입니다. 기준 인원을 넘으면 1인당 30,000원이 추가되고 24개월 미만 영유아는 무료입니다. 숙박하지 않는 방문객도 1인당 30,000원이 발생하며, 예약 인원 외 무단 입실은 퇴실 조치됩니다.':
    'The base is 8 guests and the maximum 12. Each guest over 8 is ₩30,000 per night; children under 24 months are free. Visitors who do not stay are also ₩30,000 each, and unregistered guests may be asked to leave.',
  '키즈룸과 유아용품은 유료인가요?':'Are the kids’ room and baby items charged?',
  '키즈룸(정글짐·트램폴린·흔들그네·미끄럼틀·32인치 좌식게임기)은 유아동이 있는 예약에서 무료로 열어 드립니다. 아기 하이체어·유팡 젖병소독기·유아 샴푸·아기침대 안전가드(2SET)·유아동 배게·유아식기도 무료 대여이며, 예약 시 요청해 주시면 준비합니다.':
    'The kids’ room (climbing frame, trampoline, swing, slide and a 32-inch console) is opened free for bookings with young children. High chair, bottle steriliser, children’s shampoo, bed rails (2 sets), children’s pillows and tableware are free too — just ask when booking.',
  '자쿠지 온수는 추가 요금이 있나요?':'Is the jacuzzi hot water extra?',
  '없습니다. 거실 창가 자쿠지의 온수 이용은 무료이며, 별도 옵션을 선택하실 필요가 없습니다.':'No. Hot water in the living-room jacuzzi is included; there is no option to buy.',
  '주차는 어떻게 하나요?':'How does parking work?',
  '차량 1대가 무료입니다. 도보 1분 거리의 민락회센터·민락어패류주차장을 1대 무료로 이용하실 수 있고, 예약 시 차종과 차번을 미리 등록해 주셔야 합니다. 주차가 불가한 차종이 있으니 사전에 협의해 주세요.':
    'One car is free. You can also use one free space at the Millak market / seafood parking building a minute away; register the car model and plate when booking. Some vehicles cannot park, so please check in advance.',
  '반려동물과 함께 갈 수 있나요?':'Can we bring a pet?',
  '반려동물 동반은 불가합니다. 전 구역 금연이며, 흡연 적발 시 10만원 과태료와 퇴실 조치가 있습니다.':'Pets are not allowed. The whole property is non-smoking; smoking brings a ₩100,000 penalty and check-out.',
  '음식 조리나 파티는 가능한가요?':'Can we cook or hold a party?',
  '숙소에 비치된 인덕션 외의 화기는 사용할 수 없습니다. 바베큐·생선·청국장·조개류·대게처럼 냄새가 강한 음식은 객실 내에서 조리·섭취할 수 없고, 침구·소파에서의 음식 섭취도 삼가 주세요(오염 시 배상).':
    'No open flame beyond the built-in induction hob. Strong-smelling foods (barbecue, fish, fermented soybean, shellfish, crab) cannot be cooked or eaten indoors, and please avoid eating on the bedding or sofa (damage is chargeable).',
  '소음은 괜찮은가요?':'Is it noisy?',
  '건물 1층에 게임센터가, 건물 내에 노래방 업체가 입점해 있고 광안리 해변 상업지구에 자리합니다. 소음에 민감하신 분은 참고해 주세요.':
    'There is a game centre on the ground floor, a karaoke business in the building, and the beach commercial district right outside. Light sleepers should note this.',
  '취소·환불 규정은 어떻게 되나요?':'What is the cancellation policy?',
  '취소·환불은 예약하신 채널(네이버 예약)의 규정이 적용됩니다. 구체적인 규정표는 네이버 예약 결제 단계에서 확인하실 수 있으며, 궁금한 점은 네이버 톡톡이나 0507-1429-2309로 문의해 주세요.':
    'Cancellations follow the policy of the channel you booked on (Naver Booking). The full table appears at the payment step; for anything else, message us on Naver TalkTalk or call 0507-1429-2309.',
  '예약·안내':'Book & info','3층 헤윰 네이버 예약':'Naver Booking · Heyum 3F','6층 오롯 네이버 예약':'Naver Booking · Orot 6F',
  '이 페이지는 능놀스테이 소개와 요금 견적 안내를 위한 페이지입니다. 실제 예약·결제는 네이버 예약에서 진행되며, 표시 요금은 네이버 예약 달력 기준으로 자동 동기화됩니다.':
    'This page introduces Neungnol Stay and its rates. Booking and payment happen on Naver Booking; the rates shown sync from the Naver Booking calendar.',
  '네이버 예약 동기화 중…':'Syncing with Naver Booking…','사진 © 능놀스테이 · 네이버 플레이스 / 네이버 예약':'Photos © Neungnol Stay · Naver Place / Naver Booking',
  '숙소 사진':'Photos of the house','네이버 예약으로 이동':'Continue to Naver Booking','예약 안내':'How to book',
  '이 객실 예약하기':'Book this room','사진 보기':'See photos','객실 안내':'Room details',
  '입실':'Check-in','퇴실':'Check-out','객실 리뷰':'Room reviews','도면':'Floor plan','도면 보기':'See the floor plan',
  '전체':'All','3층 헤윰':'Heyum · 3F','6층 오롯':'Orot · 6F','자쿠지·오션뷰':'Jacuzzi & ocean','침실':'Bedrooms','도면':'Plans',
  '거실':'Living room','주방·다이닝':'Kitchen & dining','욕실':'Bathroom','어메니티':'Amenities',
  '예약하기':'Book now','예약 가능한 날짜가 없습니다':'No dates open'
};
DICT.zh = {
  '예약':'預訂','객실':'客房','사진':'照片','後記':'評價','후기':'評價','위치·이용안내':'位置與使用說明','위치':'位置',
  '예약하기':'立即預訂','바로 예약하기':'立即預訂','요금 확인':'查詢房價',
  '체크인':'入住','체크아웃':'退房','인원':'人數','날짜 선택':'選擇日期',
  '기준 8인 · 최대 12인':'基本 8 人 · 最多 12 人','같은 건물, 다른 층':'同一棟建築，不同樓層',
  '광안리 바다 앞 60평, ':'廣安里海前的 60 坪，',
  '3층 헤윰 · 6층 오롯 — 같은 건물, 각 60평대 독채 오션뷰 풀빌라. 비치뷰 자쿠지·키즈룸·100인치 빔 프로젝터.':
    '三樓 헤윰 與六樓 오롯 —— 同一棟建築中兩間各約 60 坪的獨立海景泳池別墅。海景按摩浴缸、兒童房、100 吋投影螢幕。',
  '8인 기준 · 최대 12인':'基本 8 人 · 最多 12 人','침실 3 · 퀸베드 5':'3 間臥室 · 5 張加大雙人床',
  '객실을 고르면 날짜별 요금이 바로 계산됩니다':'選擇客房，立即計算每晚房價',
  '네이버 예약 달력과 동기화 중…':'正在與 Naver 預訂日曆同步…',
  '입실 15:00 · 퇴실 11:00 · 60평대':'入住 15:00 · 退房 11:00 · 60 坪','입실 16:00 · 퇴실 12:00 · 60평대':'入住 16:00 · 退房 12:00 · 60 坪',
  '입실 15:00 · 퇴실 11:00':'入住 15:00 · 退房 11:00','입실 16:00 · 퇴실 12:00':'入住 16:00 · 退房 12:00',
  '예약 가능':'可預訂','선택':'已選擇','예약 마감':'已滿','숫자 아래는 1박 요금':'日期下方為每晚房價',
  '숙박':'住宿','예약 견적':'預訂報價','예상 합계':'預估總額','1박 요금':'每晚房價',
  '달력에서 체크인·체크아웃 날짜를 선택해 주세요.':'請在日曆上選擇入住與退房日期。',
  '네이버 톡톡':'Naver TalkTalk','전화 걸기':'撥打電話','인스타그램':'Instagram',
  '예약과 결제는 선택한 객실의 네이버 예약 화면에서 진행됩니다. 이 견적은 참고 금액이며, 최종 금액·할인·쿠폰은 네이버 예약 화면에서 확정됩니다.':
    '預訂與付款於所選客房的 Naver 預訂頁面進行。此報價僅供參考，最終金額、折扣與優惠券以 Naver 預訂頁面為準。',
  '* 요금·마감 상태는 네이버 예약 달력에서 실시간으로 읽어옵니다. 마감된 날짜도 체크아웃일로는 선택할 수 있습니다.':
    '* 房價與滿房狀態即時讀取 Naver 預訂日曆。已滿的日期仍可選為退房日。',
  '같은 건물, 두 개의 60평 독채':'同一棟建築，兩間 60 坪獨立別墅',
  '3층 헤윰과 6층 오롯은 같은 건물의 서로 다른 층에 있는 별개의 독채입니다. 두 객실 모두 광안리 바다가 통창으로 들어옵니다.':
    '三樓 헤윰 與六樓 오롯 是同一棟建築不同樓層的獨立別墅，兩間客房都能透過整面落地窗看見廣安里海。',
  '실제 숙소 사진':'實際住宿照片','사진 25장 모두 보기':'查看全部 25 張照片',
  '거실 · 자쿠지 · 침실 3 · 욕실 2 · 키즈룸 · 주방 · 도면까지 공간과 객실별로 골라 보세요.':
    '客廳、按摩浴缸、3 間臥室、2 間衛浴、兒童房、廚房與平面圖，依空間或客房瀏覽。',
  '광안리에서 가장 넓은 60평':'廣安里最寬敞的 60 坪',
  '광안리 해변 도보 1분':'步行 1 分鐘到廣安里海水浴場',
  '통창으로 광안대교와 바다가 바로 보입니다. 해바라기광장·민락회센터·민락어패류주차장이 도보 1분 거리입니다.':
    '整面落地窗正對廣安大橋與海。向日葵廣場、民樂市場與民樂海鮮停車場皆步行 1 分鐘。',
  '비치뷰 자쿠지':'海景按摩浴缸',
  '거실 창가에 놓인 자쿠지에서 광안대교 노을과 밤바다를 그대로. 온수 이용에 별도 요금은 없습니다.':
    '客廳窗邊的按摩浴缸正對廣安大橋的夕陽與夜海，熱水不加價。',
  '키즈룸 무료 대여':'兒童房免費提供',
  '정글짐·트램폴린·흔들그네·미끄럼틀과 32인치 좌식 게임기. 유아동이 있는 예약에서 무료로 열어 드립니다.':
    '攀爬架、彈跳床、鞦韆、溜滑梯與 32 吋遊戲機，有幼童的預訂可免費使用。',
  '100인치 빔 프로젝터':'100 吋投影螢幕',
  '거실 100인치 빔 프로젝터와 50인치 TV. 유튜브·넷플릭스를 그대로 즐길 수 있습니다.':'客廳備有 100 吋投影機與 50 吋電視，可看 YouTube 與 Netflix。',
  '60평대 독채 · 최대 12인':'60 坪獨立別墅 · 最多 12 人',
  '기준 8인·최대 12인. 침실 3(퀸베드 5)·욕실 2·화장대 3개로 단체·가족 여행에 맞습니다.':'基本 8 人、最多 12 人。3 間臥室（5 張加大雙人床）、2 間衛浴、3 個化妝台，適合家族與團體旅行。',
  '★ 5.0 · 리뷰 125':'★ 5.0 · 125 則評價',
  '네이버 방문자 리뷰 64건 + 블로그·카페 리뷰 61건. 대표 한 줄 “세심한 배려로 완성된 룸 컨디션”.':'Naver 訪客評價 64 則 + 部落格與 Cafe 評價 61 則。代表評語：「以細心體貼完成的房間狀態」。',
  '작위적인 화려함보다,':'與其刻意華麗，','기본에 충실한 따뜻한 공간':'更願成為忠於基本的溫暖空間',
  '유형':'類型','주소':'地址','인원':'人數','침실':'臥室','욕실':'衛浴','입·퇴실':'入住 / 退房','주차':'停車','위생':'衛生',
  '독채 · 60평대 · 오션뷰 풀빌라':'獨立別墅 · 60 坪 · 海景泳池別墅',
  '부산광역시 수영구 민락수변로 13, 3층(헤윰)·6층(오롯)':'釜山廣域市水營區民樂水邊路 13，3 樓（헤윰）· 6 樓（오롯）',
  '기준 8인 / 최대 12인 (초과 1인당 30,000원 · 24개월 미만 무료)':'基本 8 人 / 最多 12 人（超出每人 ₩30,000 · 未滿 24 個月免費）',
  '침실 3 — 퀸사이즈 베드 총 5개':'3 間臥室 —— 加大雙人床共 5 張',
  '욕실 2 · 화장대 3 · 헤어드라이기 3':'2 間衛浴 · 3 個化妝台 · 3 台吹風機',
  '3층 헤윰 15:00 / 11:00 · 6층 오롯 16:00 / 12:00 (얼리 체크인·레이트 체크아웃 불가)':'헤윰 3F 15:00 / 11:00 · 오롯 6F 16:00 / 12:00（不提供提早入住與延後退房）',
  '무료 1대 (도보 1분 민락회센터·민락어패류주차장) — 차종·차번 사전 등록, 주차 불가 차종 있음':'免費 1 台（步行 1 分鐘民樂市場／海鮮停車場）——需事先登記車型與車號，部分車型無法停車',
  '세스코 멤버스 · 최근 통합방제 2026.11':'CESCO 會員 · 最近全面防治 2026.11',
  '화장대':'化妝台','50인치 TV · 넷플릭스':'50 吋電視 · Netflix','키즈룸':'兒童房',
  '32인치 좌식 게임기':'32 吋遊戲機','얼음정수기':'冰水淨水器','커피머신':'咖啡機','전기밥솥':'電子鍋',
  '인덕션 · 조리도구':'電磁爐與廚具','식기 · 와인잔':'餐具與酒杯','드럼세탁기':'滾筒洗衣機','공기청정기':'空氣清淨機',
  '유아하이체어':'兒童高腳椅','젖병소독기':'奶瓶消毒器','아기침대 안전가드':'嬰兒床護欄','유아식기':'兒童餐具',
  '와이파이':'Wi-Fi','무료 주차 1대':'免費停車 1 台','금연':'禁菸','반려동물 불가':'不可攜帶寵物',
  '바다가 통창으로 들어오는 거실과 다이닝':'海景映入整面落地窗的客廳與餐桌',
  '요금 · 할인 안내':'房價與優惠',
  '아래 요금은 네이버 예약 달력에서 확인한 2026년 11~12월 실제 1박 요금 범위입니다. 날짜별 정확한 금액은 위 달력에서 확인하세요.':
    '以下為自 Naver 預訂日曆讀取的 2026 年 11～12 月實際每晚房價範圍。各日期正確金額請見上方日曆。',
  '객실':'客房','입실 / 퇴실':'入住 / 退房','1박 요금':'每晚房價','예약 리뷰':'預訂評價','기준 인원':'基本人數','인원 추가':'加人',
  '연박 할인':'連住優惠','네이버 쿠폰':'Naver 優惠券','8인 (최대 12인)':'8 人（最多 12 人）',
  '1인당 30,000원 · 24개월 미만 영유아 무료':'每人 ₩30,000 · 未滿 24 個月免費',
  '2박 이상 예약 시 추가 1박당 50,000원 할인':'預訂 2 晚以上，第 2 晚起每晚折 ₩50,000',
  '네이버 예약 10,000원 할인 쿠폰 (예약 화면에서 다운로드)':'Naver 預訂 ₩10,000 折價券（於預訂頁面下載）',
  '* 숙박하지 않는 방문객도 1인당 30,000원이 발생합니다. 얼리 체크인·레이트 체크아웃은 운영하지 않습니다. Npay 최대 5% 적립과 Npay 카드 이벤트가 진행 중입니다(네이버 예약 기준).':
    '* 未入住的訪客亦每人加收 ₩30,000。不提供提早入住與延後退房。Npay 最高 5% 回饋與 Npay 卡活動進行中（依 Naver 預訂）。',
  '무료 대여 · 요청 물품':'免費提供與代訂物品','무료':'免費','아기 하이체어':'兒童高腳椅','유팡 젖병소독기':'유팡 奶瓶消毒器',
  '유아 샴푸':'幼兒洗髮精','아기침대 안전가드 (2SET)':'嬰兒床護欄（2 組）','유아동 배게':'幼童枕頭','유아식기':'兒童餐具',
  '키즈룸은 상시 개방이 아니라 유아동이 있는 예약에서 옵션을 선택하실 때 열어 드립니다. 필요 물품은 예약 시 요청해 주세요.':
    '兒童房並非常時開放，有幼童的預訂選擇該選項時才會開啟。需要物品請於預訂時告知。',
  '네이버 플레이스 리뷰 전체 보기 ↗':'查看 Naver Place 全部評價 ↗',
  '광안리 해변 바로 앞':'就在廣安里海灘前',
  '도보 거리':'步行距離','문의':'洽詢','예약':'預訂',
  '광안리해수욕장 도보 1분 · 해바라기광장 · 민락회센터 1분 · 민락어패류주차장 1분':'廣安里海水浴場步行 1 分鐘 · 向日葵廣場 · 民樂市場 1 分鐘 · 海鮮停車場 1 分鐘',
  '무료 1대 · 도보 1분 민락회센터·민락어패류주차장 1대 무료 — 차종·차번 사전 등록 필요, 주차 불가 차종 있음':'免費 1 台 · 步行 1 分鐘民樂市場／海鮮停車場 1 台免費 —— 需事先登記車型與車號，部分車型無法停車',
  '0507-1429-2309 · 네이버 톡톡 · 인스타그램 @neungnol_stay':'0507-1429-2309 · Naver TalkTalk · Instagram @neungnol_stay',
  '네이버 예약 (3층 헤윰 · 6층 오롯)':'Naver 預訂（헤윰 3F · 오롯 6F）',
  '구글 지도에서 크게 보기 ↗':'在 Google 地圖開啟 ↗','네이버 지도 ↗':'Naver 地圖 ↗','길찾기 ↗':'路線指引 ↗',
  '이용 안내':'使用說明',
  '예약·안내':'預訂與洽詢','3층 헤윰 네이버 예약':'Naver 預訂 · 헤윰 3F','6층 오롯 네이버 예약':'Naver 預訂 · 오롯 6F',
  '이 페이지는 능놀스테이 소개와 요금 견적 안내를 위한 페이지입니다. 실제 예약·결제는 네이버 예약에서 진행되며, 표시 요금은 네이버 예약 달력 기준으로 자동 동기화됩니다.':
    '本頁介紹 Neungnol Stay 與房價。實際預訂與付款於 Naver 預訂進行，顯示房價依 Naver 預訂日曆自動同步。',
  '네이버 예약 동기화 중…':'正在同步 Naver 預訂…','사진 © 능놀스테이 · 네이버 플레이스 / 네이버 예약':'照片 © Neungnol Stay · Naver Place / Naver Booking',
  '숙소 사진':'住宿照片','네이버 예약으로 이동':'前往 Naver 預訂','예약 안내':'預訂說明',
  '이 객실 예약하기':'預訂此客房','사진 보기':'查看照片','객실 안내':'客房資訊',
  '입실':'入住','퇴실':'退房','객실 리뷰':'客房評價','도면':'平面圖','도면 보기':'查看平面圖',
  '전체':'全部','3층 헤윰':'헤윰 · 3F','6층 오롯':'오롯 · 6F','자쿠지·오션뷰':'按摩浴缸與海景','침실':'臥室','도면':'平面圖',
  '거실':'客廳','주방·다이닝':'廚房與餐桌','욕실':'衛浴','어메니티':'備品'
};

const ORIG = new WeakMap();
function applyStatic() {
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (w.nextNode()) {
    const n = w.currentNode, p = n.parentElement;
    if (!p || !n.nodeValue.trim()) continue;
    if (p.closest('script,style,[data-dyn]')) continue;
    nodes.push(n);
  }
  nodes.forEach(n => {
    if (!ORIG.has(n)) ORIG.set(n, n.nodeValue);
    const ko = ORIG.get(n);
    if (LANG === 'ko') { n.nodeValue = ko; return; }
    const key = ko.trim().replace(/\s+/g, ' ');
    const tr = (DICT[LANG] || {})[key];
    if (tr) {
      const lead = ko.match(/^\s*/)[0], trail = ko.match(/\s*$/)[0];
      n.nodeValue = lead + tr + trail;
    } else n.nodeValue = ko;
  });
  document.documentElement.lang = LANG === 'zh' ? 'zh-Hant' : LANG;
  document.title = LANG === 'en'
    ? 'NEUNGNOL STAY · Ocean-view pool villa in Gwangalli, Busan'
    : LANG === 'zh' ? 'NEUNGNOL STAY · 釜山廣安里海景泳池別墅'
    : 'NEUNGNOL STAY · 능놀스테이 | 부산 광안리 오션뷰 풀빌라 3층 헤윰 · 6층 오롯';
  document.querySelectorAll('.lang-sw button').forEach(b => b.classList.toggle('on', b.dataset.lang === LANG));
}
function setLang(l) {
  LANG = l;
  try { localStorage.setItem('nn_lang', l); } catch (e) {}
  applyStatic();
  setRoom(ST.room);
  renderGallery(); renderReviews(); paintStamp();
  document.querySelectorAll('.modal.show').forEach(m => closeModal(m.id));
}

/* ── 객실 정의 ── */
const BIZ = '839642';
const ROOM = {
  hewyum: {
    key: 'hewyum', ko: '헤윰', en: 'Heyum', zh: '헤윰',
    floor: '3층', floorEn: '3rd floor', floorZh: '3樓',
    in: '15:00', out: '11:00', item: '4848181', reviews: 28,
    priceRange: ['500,000', '1,200,000'],
    intro: ['작위적인 화려함 보다는 기본에 충실한 따뜻한 공간이고자합니다.',
            'We would rather be a warm space true to the basics than a showy one.',
            '比起刻意的華麗，我們更希望成為忠於基本的溫暖空間。'],
    photos: ['h01', 'h02', 'h06'],
    plan: 'plan-hewyum',
    highlights: [
      ['광안리 비치뷰 통창 거실', 'Full-width beach-view living room', '廣安里海景落地窗客廳'],
      ['비치뷰 자쿠지', 'Beach-view jacuzzi', '海景按摩浴缸'],
      ['키즈룸(무료)', 'Kids’ room (free)', '兒童房（免費）'],
      ['100인치 빔 프로젝터', '100-inch projection screen', '100 吋投影螢幕'],
      ['간단 조리 가능한 주방', 'Kitchen for light cooking', '可簡單料理的廚房'],
      ['드럼세탁기', 'Front-load washer', '滾筒洗衣機']
    ]
  },
  orot: {
    key: 'orot', ko: '오롯', en: 'Orot', zh: '오롯',
    floor: '6층', floorEn: '6th floor', floorZh: '6樓',
    in: '16:00', out: '12:00', item: '4881823', reviews: 21,
    priceRange: ['500,000', '1,100,000'],
    intro: ['작위적인 화려함 보다는 기본에 충실한 따뜻한 공간이고자합니다.',
            'We would rather be a warm space true to the basics than a showy one.',
            '比起刻意的華麗，我們更希望成為忠於基本的溫暖空間。'],
    photos: ['o01', 'o02', 'o10'],
    plan: 'plan-orot',
    highlights: [
      ['광안리 비치뷰 통창 거실', 'Full-width beach-view living room', '廣安里海景落地窗客廳'],
      ['비치뷰 자쿠지', 'Beach-view jacuzzi', '海景按摩浴缸'],
      ['키즈룸(무료)', 'Kids’ room (free)', '兒童房（免費）'],
      ['100인치 빔 프로젝터', '100-inch projection screen', '100 吋投影螢幕'],
      ['간단 조리 가능한 주방', 'Kitchen for light cooking', '可簡單料理的廚房'],
      ['드럼세탁기', 'Front-load washer', '滾筒洗衣機']
    ]
  }
};
const bookingUrl = k => 'https://m.booking.naver.com/booking/3/bizes/' + BIZ + '/items/' + ROOM[k].item;

/* ── 요금 상수 ── */
const BASE_GUESTS = 8, MAX_GUESTS = 12;
const EXTRA_PERSON_FEE = 30000;   // 기준 8인 초과 1인 · 1박
const LONGSTAY_DISCOUNT = 50000;  // 2박 이상 추가 1박당

/* ── 날짜 도우미 ── */
const pad = n => String(n).padStart(2, '0');
const ds = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
function parseDS(s) { const a = s.split('-').map(Number); return new Date(a[0], a[1] - 1, a[2]); }
function addDays(s, n) { const d = parseDS(s); d.setDate(d.getDate() + n); return ds(d); }
function fmt(n) { return n == null ? '—' : n.toLocaleString('en-US'); }
function won(n) { return n == null ? '—' : (LANG === 'ko' ? fmt(n) + '원' : '₩' + fmt(n)); }
const DOW = ['일', '월', '화', '수', '목', '금', '토'];
const DOW_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const DOW_ZH = ['日', '一', '二', '三', '四', '五', '六'];
const MON_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function pretty(s) {
  const d = parseDS(s), w = d.getDay();
  if (LANG === 'en') return DOW_EN[w] + ', ' + d.getDate() + ' ' + MON_EN[d.getMonth()];
  if (LANG === 'zh') return (d.getMonth() + 1) + '月' + d.getDate() + '日（' + DOW_ZH[w] + '）';
  return (d.getMonth() + 1) + '월 ' + d.getDate() + '일 (' + DOW[w] + ')';
}
function monthLabel(y, m) {
  if (LANG === 'en') return MON_EN[m] + ' ' + y;
  if (LANG === 'zh') return y + '年' + (m + 1) + '月';
  return y + '년 ' + (m + 1) + '월';
}
function nightsLabel(n) { return L(n + '박', n + (n === 1 ? ' night' : ' nights'), n + ' 晚'); }
function roomName(k) {
  const r = ROOM[k];
  return L(r.floor, r.floorEn, r.floorZh) + ' ' + L(r.ko, r.en, r.zh);
}

/* ── 네이버 데이터 ── */
const NAVER = { hewyum: {}, orot: {} };
let OPEN_UNTIL = { hewyum: null, orot: null };
const SYNC = { ok: false, at: null, updatedAt: null, err: null, changed: 0 };
(function seed() {
  const raw = window.NAVER_DATA || {};
  Object.keys(NAVER).forEach(k => {
    const r = (raw.rooms || {})[k];
    if (!r || !r.days) return;
    Object.keys(r.days).forEach(d => {
      const v = r.days[d];
      if (Array.isArray(v)) NAVER[k][d] = [v[0] == null ? null : Number(v[0]), String(v[1] || '')];
    });
    OPEN_UNTIL[k] = r.openUntil || null;
  });
  SYNC.at = raw.updatedAt ? new Date(raw.updatedAt) : null;
  SYNC.updatedAt = raw.updatedAt || null;
  SYNC.ok = Object.keys(NAVER.hewyum).length > 0;
})();
function applySync(json) {
  if (!json || !json.rooms) throw new Error('bad json');
  let changed = 0;
  Object.keys(NAVER).forEach(k => {
    const r = json.rooms[k]; if (!r || !r.days) return;
    Object.keys(r.days).forEach(d => {
      const v = r.days[d]; if (!Array.isArray(v)) return;
      const price = v[0] == null ? null : Number(v[0]);
      const st = String(v[1] || '');
      if (['open', 'closed', 'sold', 'blocked', 'unopened', 'past'].indexOf(st) < 0) return;
      const cur = NAVER[k][d];
      if (cur && cur[0] === price && cur[1] === st) return;
      NAVER[k][d] = [price, st]; changed++;
    });
    if (r.openUntil) OPEN_UNTIL[k] = String(r.openUntil);
  });
  SYNC.ok = true; SYNC.at = new Date(); SYNC.updatedAt = json.updatedAt || null; SYNC.changed = changed;
  return changed;
}
async function loadSync(silent) {
  try {
    const res = await fetch('./naver-sync.json?t=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const json = await res.json();
    const n = applySync(json);
    paintStamp(); renderCals(); renderQuote(); renderBar();
    if (!silent) console.log('[naver] synced, changed ' + n);
  } catch (e) {
    SYNC.err = String((e && e.message) || e);
    paintStamp();
    console.warn('[naver] live sync failed, using bundled data:', SYNC.err);
  }
}

/* ── 상태 ── */
const todayKST = () => { const d = new Date(Date.now() + 9 * 3600 * 1000); return d.toISOString().slice(0, 10); };
const TODAY = todayKST();
const ST = {
  room: 'hewyum',
  y: Number(TODAY.slice(0, 4)), m: Number(TODAY.slice(5, 7)) - 1,
  in: null, out: null,
  adults: 8, children: 0, infants: 0
};

/* ── 가용성 ── */
function stateOf(date, room) {
  room = room || ST.room;
  if (date < TODAY) return 'past';
  const v = NAVER[room][date];
  if (v) return v[1];
  const until = OPEN_UNTIL[room];
  if (until && date > until) return 'unopened';
  return 'unopened';
}
function priceOf(date, room) {
  room = room || ST.room;
  const v = NAVER[room][date];
  if (v && v[0]) return v[0];
  return rulePrice(date);
}
function rulePrice(date) {
  const d = parseDS(date), dow = d.getDay(), m = d.getMonth() + 1;
  const peak = (m === 1 || m === 7 || m === 8);
  if (dow >= 1 && dow <= 4) return 500000;
  if (dow === 5) return 600000;
  if (dow === 6) return peak ? 1200000 : 1100000;
  return peak ? 700000 : 600000;
}
const isOpen = (date, room) => stateOf(date, room) === 'open';
function stateLabel(s) {
  const M = {
    open: L('예약 가능', 'Available', '可預訂'),
    closed: L('예약 마감', 'Not on sale', '已滿'),
    sold: L('예약 마감', 'Booked out', '已滿'),
    past: L('지난 날짜', 'Past date', '已過日期'),
    blocked: L('차단됨', 'Blocked', '已關閉'),
    unopened: L('판매 미오픈', 'Not yet on sale', '尚未開賣')
  };
  return M[s] || s;
}

/* ── 견적 ── */
function nights() { if (!ST.in || !ST.out) return 0; return Math.round((parseDS(ST.out) - parseDS(ST.in)) / 86400000); }
function overGuests() { return Math.max(0, ST.adults + ST.children - BASE_GUESTS); }
function quote() {
  const n = nights(); if (n <= 0) return null;
  const nightly = []; let sum = 0, blockedIn = null;
  for (let i = 0; i < n; i++) {
    const d = addDays(ST.in, i);
    if (stateOf(d) !== 'open') blockedIn = blockedIn || d;
    const p = priceOf(d);
    nightly.push({ d, p }); sum += p;
  }
  const extra = overGuests() * EXTRA_PERSON_FEE * n;
  const longStay = n >= 2 ? (n - 1) * LONGSTAY_DISCOUNT : 0;
  const total = sum - longStay + extra;
  return { n, nightly, sum, extra, longStay, total, blockedIn };
}

/* ── 달력 ── */
function renderCals() {
  const box = [document.getElementById('cal1'), document.getElementById('cal2')];
  for (let k = 0; k < 2; k++) {
    let y = ST.y, m = ST.m + k;
    if (m > 11) { m -= 12; y += 1; }
    box[k].innerHTML = monthHTML(y, m);
  }
  document.getElementById('calTitle').textContent = monthLabel(ST.y, ST.m);
}
function monthHTML(y, m) {
  const first = new Date(y, m, 1), start = first.getDay();
  const last = new Date(y, m + 1, 0).getDate();
  const dows = LANG === 'en' ? DOW_EN : (LANG === 'zh' ? DOW_ZH : DOW);
  let h = '<div class="dow">' + dows.map(d => '<span>' + d + '</span>').join('') + '</div><div class="grid">';
  for (let i = 0; i < start; i++) h += '<span></span>';
  for (let d = 1; d <= last; d++) {
    const date = y + '-' + pad(m + 1) + '-' + pad(d);
    const st = stateOf(date);
    const asOut = !!(ST.in && !ST.out && date > ST.in && st !== 'past');
    const cls = ['d', st === 'open' ? 'open' : 'off'];
    if (date === ST.in || date === ST.out) cls.push(date === ST.in ? 'start' : 'end');
    else if (ST.in && ST.out && date > ST.in && date < ST.out) cls.push('inrange');
    if (date === TODAY) cls.push('today');
    const price = priceOf(date);
    const priceTxt = (st === 'open') ? calPriceShort(price) : '';
    const dis = (st === 'open' || asOut) ? '' : ' disabled';
    const title = pretty(date) + ' · ' + (asOut && st !== 'open' ? L('체크아웃일로 선택 가능', 'Can be your check-out day', '可選為退房日') : stateLabel(st)) + (st === 'open' ? ' · ' + won(price) : '');
    h += '<button class="' + cls.join(' ') + '"' + dis + ' onclick="pickDate(\'' + date + '\')" title="' + title + '" aria-label="' + title + '">'
      + '<span class="n">' + d + '</span>' + (priceTxt ? '<span class="p">' + priceTxt + '</span>' : '') + '</button>';
  }
  return h + '</div>';
}
function shiftMonth(d) {
  ST.m += d;
  if (ST.m > 11) { ST.m = 0; ST.y++; }
  if (ST.m < 0) { ST.m = 11; ST.y--; }
  renderCals();
}
function pickDate(date) {
  const st = stateOf(date);
  if (!ST.in || (ST.in && ST.out)) {
    if (st !== 'open') return;
    ST.in = date; ST.out = null;
  } else if (date > ST.in) {
    ST.out = date;                 // 마감일도 체크아웃일로는 허용
  } else {
    if (st !== 'open') return;
    ST.in = date; ST.out = null;
  }
  renderCals(); renderQuote(); syncSearch(); renderBar();
}
function calPriceShort(n) {
  if (n == null) return '';
  if (LANG === 'ko') return (n / 10000) + '만';
  if (LANG === 'zh') return Math.round(n / 10000) + '萬';
  return Math.round(n / 1000) + 'k';
}

/* ── 견적 카드 ── */
function renderQuote() {
  const body = document.getElementById('qBody'), badge = document.getElementById('qBadge');
  const totalEl = document.getElementById('qTotal'), btn = document.getElementById('qBtn');
  const fxEl = document.getElementById('qFx');
  if (!body) return;
  const q = quote();
  document.getElementById('selIn').textContent = ST.in ? pretty(ST.in) : '—';
  document.getElementById('selOut').textContent = ST.out ? pretty(ST.out) : '—';
  document.getElementById('selNights').textContent = q ? nightsLabel(q.n) : '—';

  if (!q) {
    badge.textContent = ST.in ? L('체크아웃 선택', 'Choose check-out', '選擇退房日') : L('날짜 선택', 'Select dates', '選擇日期');
    body.innerHTML = '<p style="font-size:13px;color:var(--muted);margin:4px 0 8px">'
      + (ST.in ? pretty(ST.in) + L(' 체크인 — 체크아웃 날짜를 선택해 주세요.', ' check-in — now choose your check-out date.', ' 入住——請選擇退房日期。')
               : L('달력에서 체크인·체크아웃 날짜를 선택해 주세요.', 'Choose your check-in and check-out dates on the calendar.', '請在日曆上選擇入住與退房日期。'))
      + '</p><div class="qline"><span>' + L('1박 요금', 'Nightly rate', '每晚房價') + '</span><b>' + won(priceOf(ST.in || TODAY)) + '~</b></div>';
    totalEl.textContent = '—'; fxEl.textContent = ''; btn.disabled = true;
    btn.textContent = L('예약하기', 'Book now', '立即預訂');
    return;
  }
  let rows = '';
  q.nightly.forEach(x => {
    rows += '<div class="qline"><span>' + pretty(x.d) + '</span><b>' + won(x.p) + '</b></div>';
  });
  rows += '<div class="qline sub"><span>' + L('숙박 요금 합계', 'Room total', '住宿小計') + ' (' + nightsLabel(q.n) + ')</span><b>' + won(q.sum) + '</b></div>';
  if (q.longStay > 0) rows += '<div class="qline disc"><span>' + L('연박 할인 (2박 이상 1박당 −5만)', 'Long-stay discount (₩50,000 off each extra night)', '連住優惠（第 2 晚起每晚折 ₩50,000）') + '</span><b>−' + won(q.longStay) + '</b></div>';
  if (q.extra > 0) rows += '<div class="qline"><span>' + L('인원 추가 ', 'Extra guests ', '加人 ') + overGuests() + L('명 × ' + q.n + '박', ' × ' + q.n + ' nights', ' 名 × ' + q.n + ' 晚') + '</span><b>' + won(q.extra) + '</b></div>';
  rows += '<div class="qline"><span>' + L('입실 / 퇴실', 'Check-in / out', '入住 / 退房') + '</span><b>' + roomName(ST.room) + ' · ' + ROOM[ST.room].in + ' / ' + ROOM[ST.room].out + '</b></div>';
  body.innerHTML = rows;
  badge.textContent = nightsLabel(q.n);
  totalEl.textContent = won(q.total);
  fxEl.textContent = fxText(q.total);
  if (q.blockedIn) {
    body.insertAdjacentHTML('afterbegin', '<div class="demo-note" style="margin:0 0 10px">'
      + L('선택한 기간에 예약 마감된 날짜(', 'Your stay includes an unavailable date (', '您選擇的期間包含已滿的日期（')
      + pretty(q.blockedIn) + L(')가 있습니다. 다시 선택해 주세요.', '). Please choose again.', '），請重新選擇。') + '</div>');
    btn.disabled = true; btn.textContent = L('날짜를 다시 선택하세요', 'Choose dates again', '請重新選擇日期');
  } else {
    btn.disabled = false; btn.textContent = L('예약하기', 'Book now', '立即預訂') + ' · ' + won(q.total);
  }
}
function stepGuest(k, d) {
  ST[k] = Math.max(0, ST[k] + d);
  if (k === 'adults') ST.adults = Math.max(1, Math.min(MAX_GUESTS, ST.adults));
  if (k === 'children') { ST.children = Math.min(4, ST.children); if (ST.adults + ST.children > MAX_GUESTS) ST.children = MAX_GUESTS - ST.adults; }
  if (k === 'infants') ST.infants = Math.min(6, ST.infants);
  if (ST.adults + ST.children > MAX_GUESTS) {
    ST.children = MAX_GUESTS - ST.adults;
    toast(L('최대 12인까지 예약 가능합니다', 'Up to 12 guests', '最多可入住 12 人'));
  }
  paintGuests(); renderQuote(); syncSearch(); renderBar();
}
function paintGuests() {
  const a = document.getElementById('gAdults'), c = document.getElementById('gChildren'), i = document.getElementById('gInfants');
  if (a) a.textContent = ST.adults;
  if (c) c.textContent = ST.children;
  if (i) i.textContent = ST.infants;
}

/* ── 객실 전환 ── */
function setRoom(k) {
  if (!ROOM[k]) return;
  const prev = ST.room;
  ST.room = k;
  document.querySelectorAll('.room-tabs .rt').forEach(b => b.classList.toggle('on', b.dataset.room === k));
  const sel = document.getElementById('sbRoom'); if (sel) sel.value = k;
  const hero = document.getElementById('heroCheck');
  if (hero) hero.textContent = roomName(k) + ' ' + ROOM[k].in + ' / ' + ROOM[k].out;
  renderCals(); renderQuote(); renderRoomPanel(); syncSearch(); renderBar();
  if (prev !== k && ST.in && stateOf(ST.in, k) !== 'open') {
    toast(roomName(k) + L('에는 선택한 체크인 날짜가 예약 마감입니다. 다른 날짜를 골라 주세요.',
      ': the check-in date you chose is booked out for this room. Please pick another date.',
      '：所選入住日期在此客房已滿，請選擇其他日期。'));
  }
}
function renderRoomPanel() {
  const box = document.getElementById('roomPanel'); if (!box) return;
  const r = ROOM[ST.room];
  const nm = L(r.ko, r.en, r.zh), fl = L(r.floor, r.floorEn, r.floorZh);
  box.innerHTML =
    '<div class="rp-top">' +
      '<div class="rp-photos">' + r.photos.map((id, i) => {
        const cap = photoCap(id);
        return '<button onclick="openLightbox(\'' + ST.room + '\')" aria-label="' + cap + '"><img src="assets/' + id + '.webp" alt="' + cap + '" loading="lazy"></button>';
      }).join('') + '</div>' +
      '<div class="rp-info">' +
        '<div class="rp-floor">' + fl + ' · ' + L('60평대 독채', 'a private 60-pyeong house', '60 坪獨立別墅') + '</div>' +
        '<h3>' + nm + ' · ' + (LANG === 'ko' ? r.en : r.ko) + '</h3>' +
        '<p class="quote-line">“' + r.intro[LANG === 'en' ? 1 : (LANG === 'zh' ? 2 : 0)] + '”</p>' +
        '<ul class="rp-spec">' +
          '<li><span>' + L('입실 / 퇴실', 'Check-in / out', '入住 / 退房') + '</span><b>' + r.in + ' / ' + r.out + '</b></li>' +
          '<li><span>' + L('인원', 'Guests', '人數') + '</span><b>' + L('기준 8인 · 최대 12인', 'Base 8 · max 12', '基本 8 人 · 最多 12 人') + '</b></li>' +
          '<li><span>' + L('침실', 'Bedrooms', '臥室') + '</span><b>' + L('침실 3 · 퀸베드 5', '3 bedrooms · 5 queen beds', '3 間臥室 · 5 張加大雙人床') + '</b></li>' +
          '<li><span>' + L('욕실', 'Bathrooms', '衛浴') + '</span><b>' + L('욕실 2 · 화장대 3', '2 bathrooms · 3 vanities', '2 間衛浴 · 3 個化妝台') + '</b></li>' +
          '<li><span>' + L('1박 요금', 'Per night', '每晚房價') + '</span><b>' + r.priceRange[0] + '~' + r.priceRange[1] + L('원', ' KRW', ' 韓元') + '</b></li>' +
          '<li><span>' + L('객실 리뷰', 'Room reviews', '客房評價') + '</span><b>' + r.reviews + L('건', '', ' 則') + '</b></li>' +
        '</ul>' +
        '<div class="rp-high">' + r.highlights.map(h => '<span>' + h[LANG === 'en' ? 1 : (LANG === 'zh' ? 2 : 0)] + '</span>').join('') + '</div>' +
        '<div class="rp-actions">' +
          '<button class="btn gold" onclick="startBooking()">' + L('이 객실 예약하기', 'Book this room', '預訂此客房') + '</button>' +
          '<a class="btn ghost" href="' + bookingUrl(ST.room) + '" target="_blank" rel="noopener">' + L('네이버 예약', 'Naver Booking', 'Naver 預訂') + '</a>' +
          '<button class="btn ghost" onclick="openLightbox(\'' + ST.room + '\')">' + L('사진 보기', 'See photos', '查看照片') + '</button>' +
        '</div>' +
      '</div>' +
    '</div>';
}

/* ── 사진 ── */
const PHOTOS = (window.PHOTOS || []).map(p => ({ s: p.f.replace('.webp', ''), file: p.f, room: p.room, space: p.space, cap: p.cap }));
function photoCap(id) {
  const p = PHOTOS.find(x => x.s === id);
  if (!p) return id;
  return p.cap[LANG === 'en' ? 1 : (LANG === 'zh' ? 2 : 0)];
}
function catsList() {
  return [
    ['all', L('전체', 'All', '全部')],
    ['hewyum', L('3층 헤윰', 'Heyum 3F', '헤윰 3F')],
    ['orot', L('6층 오롯', 'Orot 6F', '오롯 6F')],
    ['jacuzzi', L('자쿠지·오션뷰', 'Jacuzzi & ocean', '按摩浴缸與海景')],
    ['kids', L('키즈룸', 'Kids’ room', '兒童房')],
    ['bed', L('침실', 'Bedrooms', '臥室')],
    ['plan', L('도면', 'Plans', '平面圖')]
  ];
}
function inCat(p, cat) {
  if (cat === 'all') return true;
  if (cat === 'hewyum' || cat === 'orot') return p.room === cat;
  return p.space === cat;
}
function renderGallery() {
  const mosaic = ['o01', 'h02', 'h06', 'o10', 'o02'];
  const box = document.getElementById('galMosaic'); if (!box) return;
  box.innerHTML = mosaic.map((id, i) => {
    const p = PHOTOS.find(x => x.s === id) || PHOTOS[i];
    const more = i === 4 ? '<span class="more">+' + Math.max(0, PHOTOS.length - 4) + '</span>' : '';
    return '<button onclick="openLightbox(\'all\')" aria-label="' + photoCap(id) + '"><img src="assets/' + id + '.webp" alt="' + photoCap(id) + '" loading="lazy"><span class="lab">' + photoCap(id) + '</span>' + more + '</button>';
  }).join('');
  const cnt = document.getElementById('galCount'); if (cnt) cnt.textContent = PHOTOS.length;
}
let lbCat = 'all', viewerList = [], viewerIdx = 0;
function openLightbox(cat) {
  lbCat = cat || 'all';
  document.getElementById('lbChips').innerHTML = catsList().map(([k, v]) =>
    '<button class="chip' + (k === lbCat ? ' on' : '') + '" onclick="openLightbox(\'' + k + '\')">' + v + '</button>').join('');
  viewerList = PHOTOS.filter(p => inCat(p, lbCat));
  document.getElementById('lbCount').textContent = '· ' + viewerList.length + L('장', ' photos', ' 張');
  document.getElementById('lbGrid').innerHTML = viewerList.map((p, i) =>
    '<button onclick="openViewer(' + i + ')"><img src="assets/' + p.file + '" alt="' + photoCap(p.s) + '" loading="lazy"><span class="t">' + photoCap(p.s) + '</span></button>').join('');
  openModal('lbModal');
}
function openViewer(i) {
  viewerIdx = i; const p = viewerList[i];
  document.getElementById('viewerImg').src = 'assets/' + p.file;
  document.getElementById('viewerCap').textContent = photoCap(p.s) + '  (' + (i + 1) + '/' + viewerList.length + ')';
  const v = document.getElementById('viewer');
  if (!v.classList.contains('show')) { v.classList.add('show'); tgPush('viewer'); }
}
function viewerStep(d) { viewerIdx = (viewerIdx + d + viewerList.length) % viewerList.length; openViewer(viewerIdx); }
function closeViewer() {
  const v = document.getElementById('viewer');
  if (!v.classList.contains('show')) return;
  v.classList.remove('show');
  const i = TG_LAYERS.lastIndexOf('viewer'); if (i >= 0) TG_LAYERS.splice(i, 1);
  tgSync();
}

/* ── 리뷰 ── */
const BLOG_REVIEWS = [
  { t: ['부산 광안리 풀빌라 능놀스테이:혜윰, 대형 자쿠지에 파노라마 오션뷰까지', 'Gwangalli pool villa Neungnol Stay Heyum — a big jacuzzi and a panoramic ocean view', '釜山廣安里泳池別墅 능놀스테이 헤윰——大型按摩浴缸與全景海景'],
    who: '나를 위해 사는 포미의 하루일기', room: '헤윰', url: 'https://m.blog.naver.com/syungtic/224324359831' },
  { t: ['[부산 광안리] 능놀스테이 풀빌라 펜션 | 아이 동반 숙박 후기', 'Gwangalli Neungnol Stay pool villa — staying with a child', '［釜山廣安里］능놀스테이 泳池別墅｜帶孩子入住後記'],
    who: '소소로그의 리뷰노트', room: '헤윰', url: '' },
  { t: ['부산 광안리 능놀스테이 헤윰, 불꽃놀이 보기 좋은 곳!', 'Neungnol Stay Heyum in Gwangalli — a great spot for the fireworks', '釜山廣安里 능놀스테이 헤윰——看煙火的好地方！'],
    who: '하춍의 일상 :)', room: '헤윰', url: 'https://m.blog.naver.com/ssun-s2/224099237916' }
];
function renderReviews() {
  const grid = document.getElementById('revGrid'); if (!grid) return;
  const li = LANG === 'en' ? 1 : (LANG === 'zh' ? 2 : 0);
  grid.innerHTML = BLOG_REVIEWS.map(r =>
    '<div class="rev"><div class="st">★ 5.0</div>'
    + '<h5>' + r.t[li] + '</h5>'
    + '<p>' + L('능놀스테이 ' + r.room + ' 객실을 직접 다녀온 블로거의 후기입니다.', 'A blog review by a guest who stayed in ' + r.room + '.', '入住 ' + r.room + ' 客房的部落客後記。') + '</p>'
    + '<div class="who"><span>' + r.who + '</span>'
    + (r.url ? '<a class="more" href="' + r.url + '" target="_blank" rel="noopener">' + L('후기 읽기 ↗', 'Read ↗', '閱讀 ↗') + '</a>' : '<span>' + L('네이버 블로그', 'Naver Blog', 'Naver 部落格') + '</span>')
    + '</div></div>').join('');
  const note = document.getElementById('revNote');
  if (note) note.textContent = L('방문자 리뷰 64건 + 블로그·카페 리뷰 61건(네이버 플레이스 표기 125건). 위 카드는 네이버 블로그에 공개된 실제 후기 제목이며, 전체 후기는 네이버 플레이스에서 확인하실 수 있습니다.',
    '64 visitor reviews plus 61 blog and cafe reviews (125 shown on Naver Place). The cards above are real public blog reviews; see all of them on Naver Place.',
    '訪客評價 64 則 + 部落格與 Cafe 評價 61 則（Naver Place 顯示 125 則）。上方卡片為 Naver 部落格公開的實際後記標題，完整評價請見 Naver Place。');
}

/* ── 검색바 · 하단 바 ── */
function syncSearch() {
  const si = document.getElementById('sbIn'), so = document.getElementById('sbOut');
  if (!si) return;
  si.value = ST.in || ''; so.value = ST.out || '';
  so.min = ST.in ? addDays(ST.in, 1) : TODAY;
  si.min = TODAY;
  document.getElementById('sbInHint').textContent = ST.in ? pretty(ST.in) : L('날짜 선택', 'Select date', '選擇日期');
  document.getElementById('sbOutHint').textContent = ST.out ? pretty(ST.out) : L('날짜 선택', 'Select date', '選擇日期');
  const g = ST.adults + ST.children;
  const q = quote();
  document.getElementById('sbSum').textContent = L('총 ' + g + '명', g + ' guests', '共 ' + g + ' 人')
    + (ST.infants ? L(' + 유아 ' + ST.infants, ' + ' + ST.infants + ' infant(s)', ' + 嬰兒 ' + ST.infants) : '');
  const roomSel = document.getElementById('sbRoom'); if (roomSel) roomSel.value = ST.room;
}
function sbChanged() {
  const i = document.getElementById('sbIn').value, o = document.getElementById('sbOut').value;
  if (i) ST.in = i;
  ST.out = o || null;
  if (ST.out && ST.out <= ST.in) ST.out = null;
  const g = parseInt(document.getElementById('sbGuests').value, 10);
  if (g) { ST.adults = g; ST.children = 0; paintGuests(); }
  renderCals(); renderQuote(); syncSearch(); renderBar();
}
function goBook() {
  if (!ST.in) pickEarliest();
  document.getElementById('booking').scrollIntoView({ behavior: 'smooth' });
  renderCals(); renderQuote(); syncSearch(); renderBar();
}
function quickPickOptions(max) {
  const out = [], lim = max || 6;
  for (let i = 0; i < 200 && out.length < lim; i++) {
    const d = addDays(TODAY, i);
    if (stateOf(d) !== 'open') continue;
    out.push({ in: d, out: addDays(d, 1), price: priceOf(d) });
  }
  return out;
}
function pickEarliest() {
  const o = quickPickOptions(1);
  if (!o.length) return false;
  ST.in = o[0].in; ST.out = o[0].out;
  return true;
}
function lowestOpenPrice() {
  const o = quickPickOptions(1);
  if (o.length) return o[0].price;
  let m = null;
  Object.keys(NAVER[ST.room]).forEach(k => {
    const v = NAVER[ST.room][k];
    if (v[1] === 'open' && v[0] && (m == null || v[0] < m)) m = v[0];
  });
  return m || 500000;
}
function renderBar() {
  const price = document.getElementById('bbPrice'); if (!price) return;
  const per = document.getElementById('bbPer'), sub = document.getElementById('bbSub'), btn = document.getElementById('bbBtn');
  const q = quote();
  if (q) {
    price.textContent = won(q.total);
    per.textContent = L('총 예상액', 'estimated total', '預估總額');
    sub.textContent = roomName(ST.room) + ' · ' + pretty(ST.in) + ' → ' + pretty(ST.out) + ' · ' + nightsLabel(q.n);
    btn.textContent = L('예약하기', 'Book now', '立即預訂');
  } else {
    const o = quickPickOptions(1);
    price.textContent = won(lowestOpenPrice()) + L('~', '~', '~');
    per.textContent = L('/ 1박', '/ night', '/ 晚');
    sub.textContent = roomName(ST.room) + ' · ' + (ST.in
      ? pretty(ST.in) + L(' 체크인 · 체크아웃 날짜를 고르세요', ' check-in · choose your check-out', ' 入住 · 請選退房日')
      : (o.length ? L('가장 빠른 체크인 ', 'Next check-in ', '最快可入住 ') + pretty(o[0].in)
                  : L('예약 가능한 날짜 문의', 'Please ask about dates', '請洽詢可預訂日期')));
    btn.textContent = L('바로 예약하기', 'Book now', '立即預訂');
  }
}
function barBooking() {
  if (!quote()) {
    if (!pickEarliest()) {
      document.getElementById('booking').scrollIntoView({ behavior: 'smooth' });
      toast(L('지금 바로 예약 가능한 날짜가 없습니다. 네이버 톡톡이나 0507-1429-2309로 문의해 주세요.',
              'No dates are open right now — please message us on Naver TalkTalk or call 0507-1429-2309.',
              '目前沒有可預訂的日期，請以 Naver TalkTalk 或 0507-1429-2309 洽詢。'));
      return;
    }
    renderCals(); renderQuote(); syncSearch(); renderBar();
  }
  startBooking();
}

/* ── 예약 안내 모달 ── */
function startBooking() {
  if (!ST.in) pickEarliest();
  if (ST.in && !ST.out && stateOf(ST.in) === 'open') ST.out = addDays(ST.in, 1);
  const q = quote();
  if (!q) { toast(L('체크아웃 날짜를 선택해 주세요', 'Please choose a check-out date', '請選擇退房日期')); return; }
  if (q.blockedIn) { toast(L('선택한 기간에 예약 마감된 날짜가 있습니다. 다른 날짜를 선택해 주세요.', 'Your stay includes an unavailable date — please pick another.', '所選期間包含已滿的日期，請重新選擇。')); return; }
  const r = ROOM[ST.room];
  const nm = roomName(ST.room);
  document.getElementById('bkTitle').textContent = L('예약 안내', 'How to book', '預訂說明');
  document.getElementById('bkPane').innerHTML =
      '<div class="bk-total"><span>' + L('예상 합계', 'Estimated total', '預估總額') + '</span><b>' + won(q.total) + '</b></div>'
    + '<div class="sum">'
    +   '<div class="row"><span>' + L('객실', 'Room', '客房') + '</span><b>' + nm + '</b></div>'
    +   '<div class="row"><span>' + L('체크인', 'Check-in', '入住') + '</span><b>' + pretty(ST.in) + ' ' + r.in + '</b></div>'
    +   '<div class="row"><span>' + L('체크아웃', 'Check-out', '退房') + '</span><b>' + pretty(ST.out) + ' ' + r.out + '</b></div>'
    +   '<div class="row"><span>' + L('숙박', 'Stay', '住宿') + '</span><b>' + nightsLabel(q.n) + '</b></div>'
    +   '<div class="row"><span>' + L('인원', 'Guests', '人數') + '</span><b>' + L('성인 ' + ST.adults + ' · 아동 ' + ST.children + ' · 유아 ' + ST.infants,
            'A ' + ST.adults + ' · C ' + ST.children + ' · I ' + ST.infants,
            '成人 ' + ST.adults + ' · 兒童 ' + ST.children + ' · 嬰兒 ' + ST.infants) + '</b></div>'
    +   '<div class="row"><span>' + L('숙박 요금', 'Room total', '住宿小計') + '</span><b>' + won(q.sum) + '</b></div>'
    +   (q.longStay ? '<div class="row" style="color:var(--ok)"><span>' + L('연박 할인', 'Long-stay discount', '連住優惠') + '</span><b>−' + won(q.longStay) + '</b></div>' : '')
    +   (q.extra ? '<div class="row"><span>' + L('인원 추가 (기준 8인 초과)', 'Extra guests (over 8)', '加人（超出 8 人）') + '</span><b>' + won(q.extra) + '</b></div>' : '')
    + '</div>'
    + '<p class="bk-room">' + L('* 입실 ' + r.in + ' / 퇴실 ' + r.out + ' · 24개월 미만 영유아는 인원 산정에서 제외됩니다.',
        '* Check-in ' + r.in + ' / check-out ' + r.out + ' · infants under 24 months are not counted.',
        '* 入住 ' + r.in + ' / 退房 ' + r.out + ' · 未滿 24 個月嬰兒不計入人數。') + '</p>'
    + '<div class="bk-links">'
    +   '<a class="naver" href="' + bookingUrl(ST.room) + '" target="_blank" rel="noopener">' + L('네이버 예약에서 이 객실 보기 ↗', 'Open this room on Naver Booking ↗', '在 Naver 預訂查看此客房 ↗') + '</a>'
    +   '<a class="alt" href="https://talk.naver.com/w4hhwm" target="_blank" rel="noopener">' + L('네이버 톡톡으로 문의', 'Message us on Naver TalkTalk', '以 Naver TalkTalk 洽詢') + '</a>'
    +   '<a class="alt" href="tel:050714292309">' + L('전화 0507-1429-2309', 'Call 0507-1429-2309', '電話 0507-1429-2309') + '</a>'
    +   '<a class="alt" href="https://www.instagram.com/neungnol_stay" target="_blank" rel="noopener">' + L('인스타그램 @neungnol_stay', 'Instagram @neungnol_stay', 'Instagram @neungnol_stay') + '</a>'
    + '</div>'
    + '<p class="qnote" style="margin-top:12px">' + L('날짜·인원·요금은 네이버 예약 화면에서 다시 확인해 주세요. 최종 금액과 할인·쿠폰 적용은 네이버 예약에서 확정되며, 이 페이지에서는 결제가 이루어지지 않습니다.',
        'Please confirm dates, guests and the rate on the Naver Booking screen. The final amount and any discount or coupon are settled there; no payment happens on this page.',
        '請在 Naver 預訂頁面再次確認日期、人數與房價。最終金額與折扣、優惠券以 Naver 預訂為準，本頁不進行付款。') + '</p>';
  openModal('bookModal');
}

/* ── 네이버 동기화 표시 ── */
function paintStamp() {
  const el = document.getElementById('naverStamp');
  const st = document.getElementById('naverState');
  const t = SYNC.at;
  let hhmm = '';
  if (t && !isNaN(t.getTime())) {
    const k = new Date(t.getTime() + 9 * 3600 * 1000);
    hhmm = pad(k.getUTCHours()) + ':' + pad(k.getUTCMinutes());
  }
  const ok = SYNC.ok && !SYNC.err;
  if (el) {
    el.textContent = ok
      ? L('네이버 예약 달력과 동기화됨 — ' + hhmm + ' 기준 (예약된 날짜는 자동으로 닫힙니다)',
          'Synced with the Naver Booking calendar — as of ' + hhmm + ' (booked dates close automatically)',
          '與 Naver 預訂日曆同步 — ' + hhmm + ' 基準（已預訂的日期會自動關閉）')
      : L('네이버 달력 실시간 동기화가 지금은 막혀 있습니다. 아래 마감 상태는 마지막으로 확인한 값이니 예약 전 네이버 예약에서 한 번 더 확인해 주세요.',
          'Live Naver sync is unavailable right now. The closures below are the last values read — please double-check on Naver Booking before you book.',
          '目前無法即時同步 Naver 日曆。下方滿房狀態為上次讀取的值，預訂前請再於 Naver 預訂確認。');
    el.style.color = ok ? '' : '#A34A00';
  }
  if (st) {
    st.textContent = ok
      ? L('네이버 예약 동기화 · ' + hhmm, 'Naver sync · ' + hhmm, 'Naver 同步 · ' + hhmm)
      : L('네이버 예약 동기화 대기', 'Naver sync pending', '等待 Naver 同步');
  }
}

/* ── 모달 · 히스토리 ── */
const TG_LAYERS = [];
let TG_PENDING = 0, TG_TIMER = null;
function tgDepth() { const s = history.state; return (s && typeof s.tg === 'number') ? s.tg : 0; }
function tgPush(name) { TG_LAYERS.push(name); try { history.pushState({ tg: TG_LAYERS.length }, ''); } catch (e) {} }
function tgSync() { if (TG_TIMER) return; TG_TIMER = setTimeout(function () { TG_TIMER = null; tgSyncNow(); }, 0); }
function tgSyncNow() {
  const diff = (tgDepth() - TG_PENDING) - TG_LAYERS.length;
  if (diff > 0) { TG_PENDING += diff; try { history.go(-diff); } catch (e) { TG_PENDING -= diff; } }
}
function tgHideDom(name) {
  if (name === 'viewer') { document.getElementById('viewer').classList.remove('show'); return; }
  const el = document.getElementById(name); if (!el) return;
  el.classList.remove('show');
  if (!document.querySelector('.modal.show')) document.body.style.overflow = '';
}
function tgCloseTop() { const name = TG_LAYERS.pop(); if (name) tgHideDom(name); }
window.addEventListener('popstate', function () {
  TG_PENDING = 0;
  const depth = tgDepth();
  let guard = 0;
  while (TG_LAYERS.length > depth && guard++ < 12) tgCloseTop();
  if (!document.querySelector('.modal.show')) document.body.style.overflow = '';
});
function openModal(id) {
  const el = document.getElementById(id); if (!el) return;
  if (!el.classList.contains('show')) { el.classList.add('show'); tgPush(id); }
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  const el = document.getElementById(id); if (!el) return;
  if (!el.classList.contains('show')) return;
  tgHideDom(id);
  const i = TG_LAYERS.lastIndexOf(id); if (i >= 0) TG_LAYERS.splice(i, 1);
  tgSync();
}
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window.__tt);
  window.__tt = setTimeout(() => { t.classList.remove('show'); }, 2200);
}

/* ── init ── */
function init() {
  applyStatic();
  paintGuests();
  setRoom('hewyum');
  renderGallery(); renderReviews(); paintStamp();
  startSyncLoop();
  if (tgDepth() > 0) { try { history.replaceState({ tg: 0 }, ''); } catch (e) {} }
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeViewer(); document.querySelectorAll('.modal.show').forEach(m => closeModal(m.id)); }
    if (document.getElementById('viewer').classList.contains('show')) {
      if (e.key === 'ArrowRight') viewerStep(1);
      if (e.key === 'ArrowLeft') viewerStep(-1);
    }
  });
}
function startSyncLoop() {
  loadSync(true);
  setInterval(() => loadSync(true), 15 * 60 * 1000);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && (!SYNC.at || Date.now() - SYNC.at.getTime() > 5 * 60 * 1000)) loadSync(true);
  });
}
init();
