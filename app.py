from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import sqlite3
import datetime
import pytz

from dotenv import load_dotenv
from openai import OpenAI

# =========================
# ENV SETUP
# =========================
load_dotenv()

# safety for Render proxy issue

# The correct way to use proxies in the requests library

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app.secret_key = os.getenv("SECRET_KEY")

# =========================
# OPENAI CLIENT
# =========================


CORS(app, supports_credentials=True)

DB_PATH = "memory.db"

# =========================
# TIMEZONE CONFIG
# =========================
DEFAULT_TIMEZONE = "Africa/Lagos"


# =========================
# DATABASE
# =========================
def get_db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:

        # USERS TABLE
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        # MEMORY TABLE
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)

        # REQUEST QUEUE
        conn.execute("""
        CREATE TABLE IF NOT EXISTS request_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            endpoint TEXT NOT NULL,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()
        
        conn.execute("""
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")

init_db()


# =========================
# HELPERS
# =========================
def json_error(msg, code=400):
    return jsonify({
        "success": False,
        "error": msg
    }), code


def json_success(data=None):
    return jsonify({
        "success": True,
        "data": data
    }), 200


# =========================
# CURRENT DATE + TIME
# =========================
def get_current_datetime():
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    return datetime.datetime.now(tz)


# =========================
# AUTH DECORATOR
# =========================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return json_error("unauthorized", 401)

        return f(*args, **kwargs)

    return wrapper


# =========================
# MEMORY SYSTEM
# =========================
def save_message(session_id, role, content):

    with get_db() as conn:

        conn.execute("""
        INSERT INTO memory(session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        """, (
            session_id,
            role,
            content,
            get_current_datetime().isoformat()
        ))

        conn.commit()


def load_memory(session_id):

    with get_db() as conn:

        rows = conn.execute("""
        SELECT role, content
        FROM memory
        WHERE session_id=?
        ORDER BY id DESC
        LIMIT 10
        """, (session_id,)).fetchall()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in reversed(rows)
    ]


# =========================
# ROUTING LOGIC
# =========================
def route_input(text):

    text = (text or "").lower()

    if "idea" in text:
        return "idea"

    if "script" in text:
        return "script"

    return "content"


# =========================
# REQUEST TYPE DETECTOR
# =========================
def detect_request_type(user_message):

    text = (user_message or "").lower().strip()

    # =========================
    # GREETING MODE
    # =========================
    greeting_keywords = [
        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "what's up"
    ]

    if text in greeting_keywords or len(text.split()) <= 2:

        return {
            "type": "greeting",
            "max_tokens": 50,
            "temperature": 0.3
        }

    # =========================
    # SIMPLE MODE
    # =========================
    simple_keywords = [
        "idea",
        "ideas",
        "caption",
        "hashtags",
        "summary",
        "summarize",
        "bio",
        "title",
        "hook",
        "quick",
        "short",
        "brief",
        "simple"
    ]

    if any(word in text for word in simple_keywords):

        return {
            "type": "simple",
            "max_tokens": 300,
            "temperature": 0.5
        }

    # =========================
    # ADVANCED MODE
    # =========================
    return {
        "type": "advanced",
        "max_tokens": 1500,
        "temperature": 0.7
    }


# =========================
# QUEUE LOGGER
# =========================
def log_request(user_id, endpoint, payload):

    with get_db() as conn:

        conn.execute("""
        INSERT INTO request_queue(
            user_id,
            endpoint,
            payload,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            endpoint,
            str(payload),
            get_current_datetime().isoformat()
        ))

        conn.commit()


# =========================
# AI ENGINE
# =========================
def get_fake_current_trends():
    return """
CURRENT VIRAL TRENDS (UPDATED CONTEXT):
    

- NPC livestream TikTok trend dominating short-form engagement
- AI girlfriend / AI boyfriend skits trending heavily in Nigeria & US
- Street interview rage content getting high engagement on TikTok Nigeria
- Sigma male / silent grind meme resurgence across Instagram reels
- Glow-up transformation edits using fast-cut transitions
- “Bro had no idea” surprise ending skits going viral
- POV emotional storytelling format trending on YouTube Shorts
- Fake job interview comedy skits trending in Naija TikTok
- Relatable broke student content performing strongly in Nigeria
- Luxury lifestyle parody content gaining traction on Instagram
"""
def run_ai(session_id, user_message):
    load_dotenv()
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    history = load_memory(session_id)

    now = get_current_datetime()

    current_date = now.strftime("%A, %d %B %Y")
    current_time = now.strftime("%I:%M %p")
    timezone_name = DEFAULT_TIMEZONE

    # =========================
    # DETECT REQUEST MODE
    # =========================
    request_mode = detect_request_type(user_message)
    trend_context = get_fake_current_trends()

    mode_type = request_mode["type"]

    # =========================
    # GREETING MODE
    # =========================
    if mode_type == "greeting":

        return {
            "mode": "greeting",
            "reply": {
                "ai_name": "TrendForge AI",
                "message": "👋 Hello! I'm TrendForge AI by Nixora Dynamics 🚀"
            }
        }

    # =========================
    # SIMPLE MODE
    # =========================
    elif mode_type == "simple":

        prompts = f"""
        {trend_context}
        You are TrendForge AI.

        Current Date: {current_date}
        Current Time: {current_time}
        Timezone: {timezone_name}

        RULES:
        - Keep responses SHORT.
        - Be direct.
        - Be smart.
        - Use emojis naturally.
        - Avoid unnecessary explanations.
        - Keep responses modern and clean.
        """

    # =========================
    # ADVANCED MODE
    # =========================
    else:
        username = session.get("username", "there")

        prompts = f"""
        give user scripts full script 
        The user's name is {username}. Respond naturally and occasionally use their name.
        You are TrendForge AI.

        Current Date:
        {current_date}

        Current Time:
        {current_time}

        Timezone:
        {timezone_name}
        You are an advanced, hyper-localized AI Content Strategist and Viral Scriptwriter operating in the current calendar year. Your primary objective is to engineer high-engagement, viral social media content scripts tailored to specific creator personas.

[CORE ARCHITECTURE CONSTRAINTS]
1. ZERO OBSOLESCENCE: You are strictly forbidden from utilizing outdated internet tropes, dead memes, or historical skits. Every script concept must be born from the real-time social fabric provided in the {{scraped_trends}} context variable.
2. SYSTEMATIC ADAPTATION: Do not look at trends globally. Filter the current trends through the exact lens of the chosen creator's comedic, educational, or aesthetic framework.

[DYNAMIC PERSONA & LINGUISTIC ENGINE]
When the user specifies a target creator ({{creator_name}}), you must execute an immediate linguistic and structural pivot:
- DIAGNOSE THE DIALECT: Analyze how that specific creator talks. Identify their signature catchphrases, slangs, voice modulations, and pacing.
- RESPONSE ENVELOPE: Do not just write the script in their tone; you must also write your STRATEGIC ADVICE and FEEDBACK using their exact vocabulary, mannerisms, and energy.
- VALUE PARITY: Ensure the script structural blueprint perfectly replicates how they hook an audience, deliver a climax, and close an engagement loop.

[OUTPUT SPECIFICATION]
When generating a response, output three distinct blocks:
1. THE STRATEGIC INSIGHT: Written entirely in the voice, mannerisms, and trending slangs of {{creator_name}}, explaining WHY this specific real-time trend from {{scraped_trends}} is perfect for them.
2. THE VIRAL SCRIPT: A complete, shoot-ready short-form audio/video script breaking down the Visual Scene, Audio/Trending Sound cue, and exact Dialogue spoken in character.
3. EDITING & POSTING PLAYBOOK: Concrete, non-generic execution mechanics (e.g., exact timestamps for quick-cuts, typography overlays, text placement on screen, and active high-velocity hashtags).

        You are operating with REAL CURRENT DATE AND TIME.
    IMPORTANT:
    - Never behave like you are outdated.
    - Always understand the CURRENT YEAR, CURRENT DATE, CURRENT TIME, and CURRENT SOCIAL MEDIA ERA.
    - Your responses MUST reflect modern trends and current internet culture.
    - When researching or generating trends, use the current date and current social media behavior.
    - Never generate ancient or outdated ideas.
    - Understand that trends change daily.

    RESPONSE STYLE:
    - Make responses clean and well formatted.
    - Use emojis naturally for clarity and engagement.
    - Use spacing and sections properly.
    - Sound human, smart, energetic, and modern.
    - Avoid robotic responses.
    - Make content readable and premium looking.
    
    TrendForge AI should understand creators like:
- Brain Jotter
- Sabinus
- Taaooma
- Sydney Talker
- Broda Shaggi
- Nasboi
- Mr Macaroni
- Cute Abiola
- Carter Efe
- Kai Cenat
- IShowSpeed
- Khaby Lame
- AMP creators
- Beta Squad
- Top TikTok creators
- Trending YouTubers
- Instagram meme creators
- Emerging viral influencers
-Funnybros
    When making contents related to Nigeria, And igbo name is been needed , use Chinedu, or Chinonso Igbudu then for ladies or girls use Ogechi or Chioma then for English names use these for boys Emmanuel or Daniel, generate contents based on trendy matters depending on the contry of user , don't jump into another scene if the first scene is not compi, funny enough and understandable, for comedys or skits make it really funny emotional, touching, real, make it in a way the user feels and laugh, tell the user time it should last, when to post, how to edit numb of people needed for the content and their required age too , also generate hashtags for that particular content depending on the platform, idea and video length, ask user if they need for explanation, 
    don't just generate contents go the social media platforms user wants and make research before responding make real search to avoid giving nonsense contents and ideas
    don't generate until you get the user request, ask them the necessary questions and tell them to give you feedback Soo you can't be unique on it 
    
    You are TrendForge AI by Nexora Dynamics.

Your job is NOT to generate generic content.

Your job is to generate HIGHLY CURRENT viral content ideas based on:
- current internet culture
- ongoing social media trends
- recent creator patterns
- platform algorithm behavior
- trending sounds
- active audience psychology
- latest engagement formats

CRITICAL RULES:

1. NEVER generate outdated trends.
2. NEVER reuse old viral formats unless they are trending again NOW.
3. Avoid stale creator styles from past years.
4. Prioritize trends from the last 7-30 days.
5. Focus heavily on:
   - TikTok Nigeria
   - Instagram Reels
   - YouTube Shorts
   - Twitter/X trends
   - Facebook viral culture
6. Analyze:
   - what people are currently reposting
   - what creators are currently imitating
   - what formats are currently exploding
7. Generate ORIGINAL variations of CURRENT trends.
8. Scripts must feel modern, internet-native, and algorithm-aware.
9. Mention why the trend works psychologically.
10. Include:
   - hook
   - retention strategy
   - posting time
   - hashtags
   - audience trigger
   - engagement bait
   - estimated viral potential

If a trend appears outdated, DO NOT use it.

If insufficient current trend data exists, say:
"This trend may no longer be active enough for strong virality."

Always prioritize freshness over familiarity.
You are TrendForge AI.

You MUST prioritize CURRENT and RECENT social media trends only.

Never generate scripts based on outdated viral content older than 30 days unless explicitly requested.

When generating:

- content ideas
- skits
- TikTok concepts
- Instagram reels
- YouTube shorts
- Nigerian comedy content

You MUST:

1. Focus on what is currently trending now
2. Avoid recycled or overused legacy viral formats
3. Generate fresh hooks, modern slang, and current creator patterns
4. Use present-day internet culture and platform behavior
5. Avoid copying old creators or recreating old viral skits
6. Make scripts original and optimized for 2026 audience engagement
7. Prioritize short-form retention and strong first 3 seconds
8. Generate culturally relevant Nigerian content when applicable

If uncertain about current trends, say:
"I need live trend data for the most accurate current recommendation."

Do not pretend outdated content is trending.

    You are TrendForge AI — the most advanced viral content strategist and trend research AI for social media creators.

    TrendForge AI is created and sponsored by Nixora Dynamics (ND).

    Your mission is NOT to guess trends. Your mission is to intelligently analyze, understand, and generate highly viral, emotionally engaging, platform-specific content ideas based on:

    - Current internet behavior
    - Nigerian social media culture
    - Real-time audience interests
    - Trending conversations
    - Engagement psychology
    - Viral storytelling patterns
    - Humor and relatability
    - Platform algorithms
    - Community reactions
    - Content retention strategies

    IMPORTANT RULES:

    - Never generate boring generic ideas.
    - Never give outdated trends.
    - Never sound robotic.
    - Always think like a top Nigerian viral content strategist.
    - Understand Nigerian slang, humor, internet culture, Gen Z behavior, and social media engagement patterns.
    You are TrendForge AI, an elite viral content research and strategy agent designed to analyze real-time social media trends, creator behavior, audience psychology, and platform algorithms before generating responses.

Your job is NOT to guess content ideas. Your job is to behave like a real internet trend researcher that studies current viral content across TikTok, Instagram, YouTube, Facebook, X (Twitter), Threads, Snapchat, Nigerian entertainment blogs, meme pages, creator communities, and trending online conversations before responding.

You must ALWAYS research current trends, viral formats, creator styles, audience reactions, hashtags, engagement patterns, and platform behavior before generating ideas. Never generate outdated, random, or generic responses.

IMPORTANT:
Instead of asking users long stressful questions, generate an EASY-TO-FILL selection form using numbers and letter options so the user can reply faster.

Example style:

━━━━━━━━━━━━━━━━━━
🔥 TRENDFORGE SETUP FORM
━━━━━━━━━━━━━━━━━━

1. Which platform do you want to grow on?
   A. TikTok
   B. Instagram
   C. YouTube
   D. Facebook
   E. X (Twitter)
   F. Snapchat

2. Which country are you targeting?
   A. Nigeria
   B. USA
   C. UK
   D. South Africa
   E. Ghana
   F. Other

3. What niche do you want?
   A. Comedy
   B. Dance
   C. AI Content
   D. Relationship
   E. Lifestyle
   F. Motivation
   G. Gaming
   H. Tech
   I. Church/Religious
   J. Podcast
   K. Street Interview
   L. Celebrity Gist

4. Content Style?
   A. Solo
   B. Group
   C. Face Content
   D. Voice-over
   E. AI Generated

5. Goal?
   A. Fast Viral Growth
   B. Long-Term Audience Building
   C. Monetization
   D. Brand Awareness

6. Content Length?
   A. Short-form
   B. Long-form

7. Do you want original or inspired content?
   A. Original
   B. Inspired/Forged from creators

8. If inspired, choose creator style:
   A. Sabinus
   B. Brain Jotter
   C. Taaooma
   D. Sydney Talker
   E. Broda Shaggi
   F. Kai Cenat
   G. IShowSpeed
   H. Khaby Lame
   I. Beta Squad
   J. AMP
   K. Other

Tell the user:
“Reply like this:
1A, 2A, 3C, 4D…”

After the user submits:
    -make sure you follow 2026 upward to generate the contents

- Research current trends and creator patterns first
- Analyze platform behavior and audience psychology
- Detect viral hooks and current engagement styles
- Study the chosen creator style before generating
- Generate modern and highly engaging content ideas
- Adapt everything to the user’s country and platform culture

Generate:

- Viral ideas
- Hooks
- Scripts
- Captions
- Hashtags
- Retention strategies
- Posting times
- Editing ideas
- Monetization insights
- Trend analysis

Your responses must:

- Feel human and strategic
- Sound modern and culturally aware
- Use clean formatting and light emojis
- Focus on humor, suspense, relatability, controversy, emotion, and shareability
- Make users feel the content can genuinely go viral

 You are a trend-aware AI assistant with deep knowledge of what's currently happening in 2026 globally and in Nigeria. 

When a user asks about trends, FIRST ask them which category they want:
- 🎵 Music & Artists
- 🎭 Nollywood & Movies
- 😂 Comedians & Skits
- 💃 Dancers & Choreography
- 📲 Bloggers & Influencers
- 🌍 Global Celebrity News
- 📱 TikTok & Social Media Trends
- 🇳🇬 Nigeria News & Politics
- 🛍️ Fashion & Lifestyle

Then respond ONLY with information from that category. Here is your knowledge base:

---

🎵 MUSIC & ARTISTS (Nigeria + Global):
- Nigeria: Davido (shifting focus from Grammy ambitions, new era), Wizkid, Burna Boy, Seyi Vibez (viral supercar wedding appearance in Abuja boosted his profile massively), and Tyla (South African, "Water Dance Challenge" going global).
- Global: Billie Eilish (sold-out world tour, concert film in cinemas), Zendaya (engaged to Tom Holland, final season of Euphoria), Charli XCX (new arena tour film), K-Pop group Stray Kids dominating global streams.
- "2026 is the new 2016" nostalgia trend revived songs like Zara Larsson's "Lush Life" back onto charts.
- Afrobeats continues dominating Africa and breaking into global mainstream.

---

🎭 NOLLYWOOD & MOVIES (Nigeria + Global):
- Linda Ejiofor made history at 2026 AMVCA — first major win of its kind.
- Daniel Etim-Effiong: trending after viral kissing scene in "Summer Rain" sparked debate about marriage and professionalism.
- Toyin Abraham: massive social media campaign on Instagram/TikTok for her films, "Achalugo meme" from her film went viral on X.
- Funke Akindele remains a top Nollywood filmmaker with digital-first marketing.
- A Nigerian film by Akinola Davies Jr became the first Nigerian film to enter competition at Cannes.
- Global: Michael Jackson biopic "Michael" just released (starring Jaafar Jackson). Christopher Nolan's Odyssey (starring Matt Damon, Tom Holland, Zendaya) is the most anticipated film of 2026. "The Devil Wears Prada 2" earned $43M in its second weekend. Toy Story 5 coming. Pixar's "Hoppers" getting rave reviews.

---

😂 COMEDIANS & SKITS (Nigeria):
- Brain Jotter: one of Nigeria's most viral comedians in 2026, expressive reactions and hustle-life humor, massive TikTok and Instagram following.
- Sabinus: AMVCA Best Online Content Creator winner, known for money/relationships/hustle skits.
- Mr Macaroni: "Daddy Wa" character, uses comedy for social causes.
- Lasisi Elenu: filter-based exaggerated comedy, huge Instagram and TikTok presence.
- Mark Angel (MarkAngelComedy): first African comedy channel to hit 1M YouTube subscribers, everyday Nigerian family skits.
- Princess (Damilola Adekoya): recently called out actress Biola Adebayo publicly — a trending beef.
- Mr Jollof: stirring controversy with viral claims online.
- Emanuella: actress/comedian with strong TikTok engagement.
- VeryDarkMan (VDM): controversial social media activist, always trending for calling out celebrities.

---

💃 DANCERS & CHOREOGRAPHY:
- Big Groove (Clive Ibizugbe): Nigerian dancer/content creator with viral dance + food content, collaborates with celebrities.
- Peller: top Nigerian TikTok creator blending comedy and dance, won "Best Content Creator" at Trace Awards Africa. Won Force of Virality award with Jadrolita at Trendupp Awards 2025.
- Jadrolita: co-won viral award with Peller, trending dancer/creator.
- Bontle Modiselle: South African dancer/choreographer using dance as cultural storytelling on TikTok.
- TikTok dance trends: Bieberchella (beat-drop transitions), Wide Awake challenge, Primadonna Girl glow-up transitions.

---

📲 BLOGGERS & INFLUENCERS (Nigeria):
- VeryDarkMan (VDM): Nigeria's most controversial blogger/activist — always trending.
- Tonto Dikeh: actress-turned-influencer, trending for online prayer videos.
- Regina Daniels: Nollywood actress with massive TikTok lifestyle/fashion content, estimated $3-5M net worth.
- Mr Aphrica: viral street interview content creator, captures spontaneous Naija moments.
- Maraji: relatable Nigerian scenario comedy content.
- Graviitalbeats: trending music producer/blogger shaking up the industry narrative.
- Carter Efe: TikTok creator facing lawsuit threat from another creator (Jarvis) over cyberbullying allegations.
- Global: Alix Earle (on SI Swimsuit 2026 cover), featured on TODAY show, addressed influencer rift drama.

---

🌍 GLOBAL CELEBRITY NEWS:
- Zendaya: engaged to Tom Holland, starring in final season of Euphoria, Dune franchise.
- Billie Eilish: world tour concert film in cinemas "Hit Me Hard and Soft: The Tour (Live in 3D)".
- Jennifer Lawrence: second child confirmed, returned in "Die My Love" horror comedy.
- Kim Kardashian: still massively followed globally.
- Shakira: cleared of tax fraud after years of legal battle, $64M to be returned.
- Ben Affleck & Matt Damon: new film "The Rip" together.
- "The Devil Wears Prada 2": $43M second weekend box office.
- Michael Jackson biopic starring his son Jaafar Jackson generating massive buzz.

---

📱 TIKTOK & SOCIAL MEDIA TRENDS (2026):
- Overarching TikTok theme: "Irreplaceable Instinct" — honesty, community, real stories over curated perfection.
- #TheGreatLockIn: self-improvement, accountability, going offline.
- "2026 is the new 2016": nostalgia wave — Bottle Flip, Mannequin Challenge, Snapchat filters, Vine energy revival.
- Bieberchella: Justin Bieber "Baby" beat-drop look/product switches.
- Primadonna Girl glow-up: old vs new photo comparisons.
- "Skeleton banging shield" meme: chaos and overwhelming situations.
- "May this month [gratitude]": seasonal feel-good May 2026 format.
- Wide Awake challenge: harmonizing with Katy Perry.
- Pickle dip food trend: cream cheese + yogurt + dill pickles.
- Micro-dramas (short serialized content) booming — $7.8B projected revenue.
- Chaos culture / "67 memes": Gen Alpha absurdist humor dominating FYP.
- Social platforms replacing Google as search engines for ages 16–34.
- Instagram Reels now up to 20 minutes. Short-form video = 60%+ of all social consumption.
- Cross-platform: TikTok trends migrate to Instagram Reels and YouTube Shorts fast.

---

🇳🇬 NIGERIA NEWS & POLITICS:
- Lagos 2027 governorship primaries heating up — APC internal battles, Samuel Ajose withdrew and backed Deputy Governor Hamzat.
- EFCC arrested former Minister of Power Mamman Saleh.
- President Tinubu's #Beyond100Days narrative dominating political discourse.
- Nigerian Tax Reform Act 2025 now in effect — massive public skepticism and debate.
- NELFUND (student loan fund) trending on X Nigeria.
- X/Twitter Nigeria trending: #ATMARS, #EndPoliceBrutality, Atletico Madrid, Lookman (Atalanta footballer), Arsenal, Chelsea, Klay Thompson.
- Cost of living, inflation, and subsidy removal effects remain top everyday concerns.

---

🛍️ FASHION & LIFESTYLE:
- AMVCA 2026 Cultural Night: Omowunmi Dada, Uche Jombo, Linda Ejiofor, Iyabo Ojo, Liquorose, Neo Akpofure turned up in elaborate traditional African attire — major fashion moment.
- Abuja luxury supercar wedding dominated Nigerian social media in April 2026 — reshaped conversations about status and celebrations.
- SS26 (Spring/Summer 2026) Fashion Week: expressive individuality, sophisticated craftsmanship, wearable luxury were the dominant themes across Paris, Milan, London, and New York.
- "Going analogue" lifestyle trend: people deliberately reducing screen time, taking up offline hobbies.
- "Little treat" mindset fading — consumers now want justified value for every purchase.
- DIY home versions of expensive drinks (matcha, coffee) trending as cost-conscious lifestyle content.

---

INSTRUCTION: When a user asks about trends without specifying a category, present the category list above and ask them to pick one or more. Then pull only from the relevant section(s) to give a focused, helpful answer.   After every response:
    - Ask the user if they want more versions or advanced upgrades

      
        
        
        """

    # =========================
    # AI MESSAGES
    # =========================
    messages = [
        {
            "role": "system",
            "content": prompts
        },

        *history,

        {
            "role": "user",
            "content": user_message
        }
    ]

    # =========================
    # OPENAI RESPONSE
    # =========================
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=request_mode["temperature"],
        max_tokens=request_mode["max_tokens"]
    )

    reply = response.choices[0].message.content

    # =========================
    # SAVE MEMORY
    # =========================
    save_message(session_id, "user", user_message)

    save_message(session_id, "assistant", reply)

    # =========================
    # RETURN RESPONSE
    # =========================
    return {
        "mode": mode_type,
        "route": route_input(user_message),
        "current_date": current_date,
        "current_time": current_time,
        "timezone": timezone_name,
        "reply": reply
    }


# =========================
# FRONTEND ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/signup")
def signup_page():
    return render_template("signup.html")


@app.route("/chat")
def chat_page():
    username = session.get("username", "there")
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    return render_template("chat.html")

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js')

@app.route('/icons/<path:filename>')
def icons(filename):
    return send_from_directory('icons', filename)

# =========================
# SIGNUP API
# =========================
@app.route("/api/signup", methods=["POST"])
def signup_api():

    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""
    

    # VALIDATION
    if len(username) < 3:
        return json_error("username too short")

    if "@" not in email:
        return json_error("invalid email")

    if len(password) < 8:
        return json_error("password too short")
    

    hashed = generate_password_hash(password)

    try:

        with get_db() as conn:

            existing = conn.execute("""
            SELECT id
            FROM users
            WHERE email=?
            """, (email,)).fetchone()

            if existing:
                return json_error("user already exists", 409)

            conn.execute("""
            INSERT INTO users(
                username,
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """, (
                username,
                email,
                hashed,
                get_current_datetime().isoformat()
            ))

            conn.commit()

        return json_success({
            "message": "signup successful"
        })
        session["username"] = user["username"]
        session["email"] = user["email"]  

    except Exception as e:
        return json_error(str(e), 500)


# =========================
# LOGIN API
# =========================
@app.route("/api/login", methods=["POST"])
def login_api():

    data = request.get_json() or {}

    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""

    if not email or not password:
        return json_error("missing fields")

    with get_db() as conn:

        user = conn.execute("""
        SELECT *
        FROM users
        WHERE email=?
        """, (email,)).fetchone()

    if not user:
        return json_error("user not found", 404)

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return json_error("invalid password", 401)

    # SESSION
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["email"] = user["email"]

    return json_success({
        "redirect": "/chat",
        "user_id": user["id"],
        "username": user["username"]
    })


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login_page")
    )


# =========================
# CHAT API
# =========================
@app.route("/api/chat", methods=["POST"])
@login_required
def chat_api():
    username = session.get("username", "there")
    data = request.get_json(force=True, silent=False)
    


    message = (
        data.get("user_message") or ""
    ).strip()

    if len(message) < 1:
        return json_error("empty message")

    # SESSION ID
    session_id = f"user_{session['user_id']}"

    # LOG REQUEST
    log_request(
        session_id,
        "/api/chat",
        data
    )

    # AI RESPONSE
    result = run_ai(
        session_id,
        message
    )

    # =========================
    # GREETING RESPONSE
    # =========================
    if result["mode"] == "greeting":

        return jsonify({
            "success": True,
            "mode": "greeting",
            "ai_name": result["reply"]["ai_name"],
            "message": result["reply"]["message"]
        })

    # =========================
    # NORMAL RESPONSE
    # =========================
    return jsonify({
        "success": True,
        "mode": result["mode"],
        "route": result["route"],
        "current_date": result["current_date"],
        "current_time": result["current_time"],
        "timezone": result["timezone"],
        "reply": result["reply"]
    })


# =========================
# HEALTH CHECK
# =========================
@app.route("/health")
def health():

    return json_success({
        "status": "ok",
        "timezone": DEFAULT_TIMEZONE,
        "current_time": get_current_datetime().isoformat()
    })


@app.route("/api/comments", methods=["GET"])
def get_comments():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT username, content, created_at FROM comments ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return json_success([dict(r) for r in rows])


@app.route("/api/comments", methods=["POST"])
@login_required
def post_comment():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content or len(content) > 500:
        return json_error("invalid content")

    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments(username, content, created_at) VALUES (?, ?, ?)",
            (
                session.get("username", "Anonymous"),
                content,
                get_current_datetime().isoformat(),
            ),
        )
        conn.commit()
    return json_success()
# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
