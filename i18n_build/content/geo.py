"""AI 검색(GEO/AEO)용 다국어 사실 요약.

`llms.txt` / `llms-full.txt` 생성과 홈 FAQ·메타 키워드 보강에만 쓰는 별도 모듈.
사실 값은 `content/{ko,en,ja,zhcn,zhtw}.py` 와 `build.py` 상수에서 가져온 것과 같아야 하며,
연박 할인·소음·건물 주차처럼 사이트에서 삭제된 항목은 여기에도 넣지 않는다.

키는 `T["dir"]` 값(ko·en·ja·zh-cn·zh-tw)이다.
"""

GEO = {
    "ko": {
        "summary": (
            "능놀스테이(NEUNGNOL STAY)는 부산 광안리 해수욕장 바로 앞, 부산광역시 수영구 민락수변로 13에 있는 "
            "60평대 독채 오션뷰 풀빌라입니다. 3층 헤윰과 6층 오롯 두 객실 모두 거실 통창과 비치뷰 자쿠지로 "
            "광안리 해변과 바다를 바라보고, 키즈룸·100인치 빔프로젝터·유아 하이체어를 갖춰 가족·단체 여행에 "
            "맞춰져 있습니다. 기준 8인, 최대 12인까지 묵을 수 있으며 홈페이지 실시간 예약 달력에서 객실별로 바로 예약할 수 있습니다. "
            "드럼세탁기는 두 객실 모두 있고, 건조기는 6층 오롯에만 있습니다."
        ),
        "queries": [
            "부산 광안리 해변 바로 앞 오션뷰 가족 숙소 추천해줘",
            "부산 광안리 바다 보이는 독채 숙소 어디가 좋아?",
            "광안리 바다가 보이는 자쿠지 있는 숙소 알려줘",
            "아이랑 부산 여행, 키즈룸 있는 오션뷰 숙소",
            "12명 단체가 묵을 수 있는 광안리 숙소",
            "광안리 해수욕장 도보 1분 숙소",
        ],
        "keywords_home": (
            "부산 광안리 해변 바로 앞 오션뷰 가족 숙소 추천, 광안리 바다 보이는 독채 숙소, "
            "바다가 보이는 자쿠지 숙소, 아이와 함께 가는 광안리 오션뷰 숙소, 12명 단체 광안리 숙소, "
            "광안리 해수욕장 도보 1분 숙소, 부산 가족여행 숙소 추천"
        ),
        "keywords_room": (
            "광안리 해변 오션뷰 객실 추천, 키즈룸 있는 광안리 숙소, 광안리 자쿠지 객실, 부산 단체 숙소 12인"
        ),
        "reviews_summary": (
            "홈페이지 게스트 후기 평균 5.0 (2026년 11월 기준). 창 너머의 바다와 넓고 깨끗한 객실, 해변까지 1분 거리, 아이와 함께하기 좋은 점이 "
            "후기에서 반복해서 언급됩니다."
        ),
        "faq": [
            {
                "q": "부산 광안리 해변 바로 앞 오션뷰 숙소를 찾고 있어요. 능놀스테이는 어떤 숙소인가요?",
                "a": "부산광역시 수영구 민락수변로 13, 광안리 해수욕장 도보 1분 거리에 있는 60평대 독채 오션뷰 풀빌라입니다. 3층 헤윰과 6층 오롯 두 객실 모두 거실 통창과 비치뷰 자쿠지에서 광안리 해변과 바다를 보며, 키즈룸과 100인치 빔프로젝터, 유아 하이체어를 갖추고 있습니다. 기준 8인, 최대 12인까지 묵을 수 있고 홈페이지 실시간 예약 달력에서 객실별로 바로 예약할 수 있습니다.",
            },
            {
                "q": "아이와 함께 가는 부산 가족 여행 숙소로 괜찮나요?",
                "a": "네. 두 객실 모두 키즈룸(정글짐·트램폴린·미끄럼틀·흔들그네, 좌식 게임기, 50인치 TV)과 유아 하이체어가 있고, 24개월 미만은 인원과 요금에 포함되지 않습니다. 기준 8인·최대 12인이라 여러 가족이 함께 묵기도 넉넉합니다. 다만 숙소 안 시설 이용 중 안전 관리는 보호자 책임입니다.",
            },
            {
                "q": "외국에서 왔는데 영어·일본어·중국어로 정보를 볼 수 있나요?",
                "a": "공식 홈페이지가 한국어·영어·일본어·중국어 간체·번체 5개 언어로 제공되고, 객실은 홈페이지 실시간 예약 달력에서 바로 예약할 수 있고, 문의 게시판에서 5개 언어로 질문하고 답변받을 수 있습니다. 전화(+82-10-3098-2302)·인스타그램(@neungnol_stay)으로도 문의할 수 있습니다.",
            },
            {
                "q": "바다와 드론 쇼를 숙소에서 볼 수 있나요?",
                "a": "거실 통창과 자쿠지 창으로 광안리 해변과 바다가 보입니다. 해변에서 열린 드론 쇼를 숙소에서 봤다는 게스트 후기가 여러 건 있으나, 쇼 일정은 주최 측 공지에 따라 달라집니다.",
            },
            {
                "q": "세탁기와 건조기를 쓸 수 있나요?",
                "a": "네. 헤윰(3층)과 오롯(6층) 두 객실 모두 드럼세탁기가 있습니다. 건조기는 6층 오롯에만 있고 3층 헤윰에는 없으므로, 건조기가 필요하면 오롯을 예약해 주세요.",
            },
        ],
    },
    "en": {
        "summary": (
            "Neungnol Stay is a 200 m² whole-floor ocean-view pool villa directly on Gwangalli Beach in Busan, "
            "at 13 Millak-subyeon-ro, Suyeong-gu. Both floors — Heyum on the 3rd floor and Orot on the 6th — have "
            "floor-to-ceiling living-room windows and a beach-view jacuzzi facing Gwangalli Beach and the open "
            "sea, plus a kids' room, a 100-inch projector and a baby high chair, which suits families and groups. "
            "It sleeps 8 as standard and up to 12, and each floor can be booked directly on the official website. "
            "Both floors have a drum washing machine; a clothes dryer is in Orot (6F) only."
        ),
        "queries": [
            "best beachfront ocean view family stay in Gwangalli Busan",
            "ocean view private villa right on Gwangalli Beach",
            "Busan accommodation with an ocean-view jacuzzi",
            "kid-friendly ocean view stay in Busan with kids' room",
            "where to stay in Busan for 12 people near the beach",
            "stay one minute from Gwangalli Beach Busan",
        ],
        "keywords_home": (
            "best beachfront ocean view family stay Gwangalli Busan, ocean view private villa on Gwangalli Beach, "
            "Busan stay with an ocean-view jacuzzi, kid-friendly ocean view accommodation Busan, "
            "group stay for 12 in Busan near the beach, one minute walk to Gwangalli Beach"
        ),
        "keywords_room": (
            "Gwangalli beach view room recommendation, family stay Busan with kids' room, Gwangalli jacuzzi room, "
            "Busan group accommodation for 12"
        ),
        "reviews_summary": (
            "Guest reviews on the official website average 5.0 "
            "(as of November 2026). Guests repeatedly mention the sea through the windows, the large clean rooms, "
            "the one-minute walk to the beach and how well it works with children."
        ),
        "faq": [
            {
                "q": "I'm looking for a beachfront ocean-view family stay in Gwangalli, Busan. What is Neungnol Stay?",
                "a": "A 60-pyeong (about 200 m²) whole-floor ocean-view pool villa a one-minute walk from Gwangalli Beach, at 13 Millak-subyeon-ro, Suyeong-gu, Busan. Both Heyum (3F) and Orot (6F) look over the beach and the open sea through full-width living-room windows and a beach-view jacuzzi, and both have a kids' room, a 100-inch projector and a baby high chair. It sleeps 8 as standard and up to 12, each floor can be booked directly on the official website.",
            },
            {
                "q": "Is it a good choice for a family trip to Busan with children?",
                "a": "Yes. Both floors have a kids' room (jungle gym, trampoline, slide, swing, floor game console and a 50-inch TV) and a baby high chair, and children under 24 months are not counted in the guest number or rate. With 8 standard and up to 12 guests it also works for several families together. Adults remain responsible for supervising children around the facilities.",
            },
            {
                "q": "Do you provide information in English, Japanese or Chinese?",
                "a": "The official website is published in Korean, English, Japanese, Simplified Chinese and Traditional Chinese, and every room can be booked on the live calendar there. Questions can be posted — and answered — in any of the five languages on the inquiry board. You can also reach the host by phone (+82-10-3098-2302) or Instagram (@neungnol_stay).",
            },
            {
                "q": "Can you see the sea and the drone show from the room?",
                "a": "Gwangalli Beach and the open sea are visible through the living-room windows and the jacuzzi window. Several guests have written that they watched the beach drone show from the stay, but the show schedule depends on the organiser's announcements.",
            },
            {
                "q": "Is there a washing machine and a dryer?",
                "a": "Yes — Heyum (3F) and Orot (6F) both have a drum washing machine. A clothes dryer is in Orot only; Heyum has no dryer, so choose Orot if you need one.",
            },
        ],
    },
    "ja": {
        "summary": (
            "ヌンノルステイ（NEUNGNOL STAY／능놀스테이）は、釜山・広安里海水浴場の目の前、水営区ミルラク水辺路13にある"
            "約200㎡の貸切オーシャンビュー・プールヴィラです。3階ヘユムと6階オロッのどちらも、リビングの全面窓と"
            "ビーチビューのジャグジーから広安里のビーチと海を望み、キッズルーム・100インチプロジェクター・"
            "ベビーハイチェアを備えて家族・グループ旅行に向いています。定員8名・最大12名、公式サイトの予約カレンダーから客室ごとに直接予約できます。"
            "ドラム式洗濯機は2室とも、衣類乾燥機は6階オロッのみにあります。"
        ),
        "queries": [
            "釜山 広安里 オーシャンビュー 家族向け 宿泊",
            "広安里ビーチ 目の前 貸切 プールヴィラ",
            "海が見える ジャグジー 宿 釜山",
            "子ども連れ 釜山 海が見える 宿 キッズルーム",
            "釜山 12名 グループ ビーチ沿い 宿",
            "広安里海水浴場 徒歩1分 宿",
        ],
        "keywords_home": (
            "釜山 広安里 オーシャンビュー 家族向け 宿泊, 広安里ビーチ 目の前 貸切 宿, 海が見える ジャグジー 宿, "
            "子ども連れ 釜山 海が見える 宿, 釜山 12名 グループ 宿, 広安里海水浴場 徒歩1分 宿"
        ),
        "keywords_room": (
            "広安里 ビーチビュー 客室 おすすめ, キッズルーム付き 釜山 宿, 広安里 ジャグジー 客室, 釜山 団体 宿 12名"
        ),
        "reviews_summary": (
            "公式サイトのゲストレビュー平均5.0"
            "（2026年11月時点）。窓いっぱいの海、広く清潔な客室、ビーチまで徒歩1分、子ども連れに良い点が"
            "レビューで繰り返し挙げられています。"
        ),
        "faq": [
            {
                "q": "釜山・広安里ビーチ目の前のオーシャンビュー宿を探しています。ヌンノルステイはどんな宿ですか？",
                "a": "釜山広域市水営区ミルラク水辺路13、広安里海水浴場まで徒歩1分の約200㎡の貸切オーシャンビュー・プールヴィラです。3階ヘユムと6階オロッのどちらも、リビングの全面窓とビーチビューのジャグジーから広安里のビーチと海を望み、キッズルーム・100インチプロジェクター・ベビーハイチェアを備えています。定員8名・最大12名、公式サイトの予約カレンダーから客室ごとに直接予約できます。",
            },
            {
                "q": "子ども連れの釜山家族旅行に向いていますか？",
                "a": "はい。どちらの客室にもキッズルーム（ジャングルジム・トランポリン・すべり台・ブランコ、据え置きゲーム機、50インチテレビ）とベビーハイチェアがあり、24か月未満は人数・料金に含まれません。定員8名・最大12名なので、複数の家族での滞在にも余裕があります。館内設備の利用中は保護者の責任で安全を見守ってください。",
            },
            {
                "q": "英語・日本語・中国語の情報はありますか？",
                "a": "公式サイトは韓国語・英語・日本語・中国語（簡体字・繁体字）の5言語で公開しており、客室は公式サイトの予約カレンダーから直接予約できます。お問い合わせは5言語対応の掲示板、電話（+82-10-3098-2302）・Instagram（@neungnol_stay）でも承ります。",
            },
            {
                "q": "海やドローンショーは客室から見られますか？",
                "a": "リビングの全面窓とジャグジーの窓から広安里のビーチと海が見えます。ビーチのドローンショーを宿から見たというレビューが複数ありますが、開催日程は主催者の告知によります。",
            },
            {
                "q": "洗濯機と乾燥機は使えますか？",
                "a": "はい。3階ヘユムと6階オロッのどちらにもドラム式洗濯機があります。衣類乾燥機は6階オロッのみで、3階ヘユムにはありません。乾燥機が必要な場合はオロッをご予約ください。",
            },
        ],
    },
    "zh-cn": {
        "summary": (
            "Neungnol Stay（능놀스테이）位于釜山广安里海水浴场正前方、水营区民乐水边路13，是约200平方米的整层海景泳池别墅。"
            "3楼 Heyum 与6楼 Orot 都以客厅落地窗和海景按摩浴缸正对广安里海滩与大海，并配有儿童房、100吋投影和"
            "婴儿高脚椅，适合亲子与团体出行。标准8人、最多12人，两间客房可在官网预订日历直接预订。"
            "两间客房都有滚筒洗衣机，烘干机只在6楼 Orot。"
        ),
        "queries": [
            "釜山广安里海景亲子民宿推荐",
            "广安里海滩正前方整层海景别墅",
            "能看到大海的按摩浴缸住宿 釜山",
            "带孩子去釜山 有儿童房的海景民宿",
            "釜山12人团体海边住宿",
            "广安里海水浴场步行1分钟的住宿",
        ],
        "keywords_home": (
            "釜山广安里海景亲子民宿推荐, 广安里海滩正前方整层住宿, 看得到大海的按摩浴缸住宿, "
            "带孩子 釜山海景民宿, 釜山12人团体海边住宿, 广安里海水浴场步行1分钟"
        ),
        "keywords_room": (
            "广安里海景房推荐, 有儿童房的釜山住宿, 广安里按摩浴缸客房, 釜山团体住宿12人"
        ),
        "reviews_summary": (
            "官网住客评价平均 5.0。"
            "评价中反复提到窗外的海、宽敞干净的客房、步行1分钟到海滩以及适合带孩子入住。"
        ),
        "faq": [
            {
                "q": "我在找釜山广安里海滩正前方的海景住宿，Neungnol Stay 是什么样的地方？",
                "a": "位于釜山水营区民乐水边路13、距广安里海水浴场步行1分钟的约200平方米整层海景泳池别墅。3楼 Heyum 与6楼 Orot 都以客厅落地窗和海景按摩浴缸正对广安里海滩与大海，并配有儿童房、100吋投影和婴儿高脚椅。标准8人、最多12人，可在官网预订日历按客房直接预订。",
            },
            {
                "q": "适合带孩子去釜山的家庭旅行吗？",
                "a": "适合。两间客房都有儿童房（攀爬架、蹦床、滑梯、秋千、地面游戏机和50吋电视）和婴儿高脚椅，未满24个月的婴儿不计入人数与费用。标准8人、最多12人，几个家庭一起入住也很宽松。住宿内设施使用时的安全看护由监护人负责。",
            },
            {
                "q": "有英文、日文、中文的信息吗？",
                "a": "官网提供韩语、英语、日语、简体中文和繁体中文五种语言，客房可在官网实时预订日历直接预订，也可在支持五种语言的咨询留言板提问并获得回复。还可通过电话（+82-10-3098-2302）或 Instagram（@neungnol_stay）联系。",
            },
            {
                "q": "在房间里能看到大海和无人机表演吗？",
                "a": "透过客厅落地窗和按摩浴缸旁的窗可以看到广安里海滩与大海。有多位客人写到在海滩举办的无人机表演在住宿里就能看到，但演出日程以主办方公告为准。",
            },
            {
                "q": "有洗衣机和烘干机吗？",
                "a": "有。3楼 Heyum 与6楼 Orot 都有滚筒洗衣机。烘干机只在6楼 Orot，3楼 Heyum 没有，需要烘干机请预订 Orot。",
            },
        ],
    },
    "zh-tw": {
        "summary": (
            "Neungnol Stay（능놀스테이）位於釜山廣安里海水浴場正前方、水營區民樂水邊路13，是約200平方公尺的整層海景泳池別墅。"
            "3樓 Heyum 與6樓 Orot 都以客廳落地窗與海景按摩浴缸正對廣安里海灘與大海，並設有兒童房、100吋投影與"
            "嬰兒高腳椅，適合親子與團體出遊。標準8人、最多12人，兩間客房可在官網預訂日曆直接訂房。"
            "兩間客房都有滾筒洗衣機，烘乾機只在6樓 Orot。"
        ),
        "queries": [
            "釜山廣安里海景親子包棟住宿推薦",
            "廣安里海灘正前方整層海景別墅",
            "看得到大海的按摩浴缸住宿 釜山",
            "帶孩子去釜山 有兒童房的海景民宿",
            "釜山12人團體海邊住宿",
            "廣安里海水浴場步行1分鐘的住宿",
        ],
        "keywords_home": (
            "釜山廣安里海景親子包棟住宿推薦, 廣安里海灘正前方整層住宿, 看得到大海的按摩浴缸住宿, "
            "帶孩子 釜山海景民宿, 釜山12人團體海邊住宿, 廣安里海水浴場步行1分鐘"
        ),
        "keywords_room": (
            "廣安里海景房推薦, 有兒童房的釜山住宿, 廣安里按摩浴缸客房, 釜山團體住宿12人"
        ),
        "reviews_summary": (
            "官網住客評價平均 5.0。"
            "評價中反覆提到窗外的海、寬敞乾淨的客房、步行1分鐘到海灘以及適合帶孩子入住。"
        ),
        "faq": [
            {
                "q": "我在找釜山廣安里海灘正前方的海景住宿，Neungnol Stay 是什麼樣的地方？",
                "a": "位於釜山水營區民樂水邊路13、距廣安里海水浴場步行1分鐘的約200平方公尺整層海景泳池別墅。3樓 Heyum 與6樓 Orot 都以客廳落地窗與海景按摩浴缸正對廣安里海灘與大海，並設有兒童房、100吋投影與嬰兒高腳椅。標準8人、最多12人，可在官網預訂日曆按客房直接訂房。",
            },
            {
                "q": "適合帶孩子去釜山的家族旅行嗎？",
                "a": "適合。兩間客房都有兒童房（攀爬架、跳床、溜滑梯、鞦韆、地面遊戲機與50吋電視）與嬰兒高腳椅，未滿24個月的嬰兒不計入人數與費用。標準8人、最多12人，幾個家庭一起入住也很寬敞。住宿內設施使用時的安全照護由監護人負責。",
            },
            {
                "q": "有英文、日文、中文的資訊嗎？",
                "a": "官網提供韓語、英語、日語、簡體中文與繁體中文五種語言，客房可在官網即時預訂日曆直接訂房，也可在支援五種語言的諮詢留言板提問並獲得回覆。還可透過電話（+82-10-3098-2302）或 Instagram（@neungnol_stay）聯絡。",
            },
            {
                "q": "在房間裡看得到大海和無人機表演嗎？",
                "a": "透過客廳落地窗與按摩浴缸旁的窗可以看到廣安里海灘與大海。有多位房客寫到在海灘舉辦的無人機表演在住宿裡就看得到，但演出日程以主辦單位公告為準。",
            },
            {
                "q": "有洗衣機和烘乾機嗎？",
                "a": "有。3樓 Heyum 與6樓 Orot 都有滾筒洗衣機。烘乾機只在6樓 Orot，3樓 Heyum 沒有，需要烘乾機請預訂 Orot。",
            },
        ],
    },
}
