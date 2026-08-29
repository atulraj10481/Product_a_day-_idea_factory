import os, sys, json, sqlite3, time, requests
from ddgs import DDGS
from dotenv import load_dotenv

# Reconfigure stdout/stderr for full UTF-8 Unicode support on Windows
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# ─── Multi-Provider LLM Engine ───────────────────────────────────────────────

PROVIDERS = []

# Provider 1: OpenRouter (Primary - nvidia/nemotron-3-ultra-550b-a55b:free)
if os.getenv("OPENROUTER_API_KEY"):
    PROVIDERS.append("openrouter")

# Provider 2: Groq (Fallback - openai/gpt-oss-120b)
if os.getenv("GROQ_API_KEY"):
    PROVIDERS.append("groq")

# Provider 3: Gemini (Secondary Fallback)
if os.getenv("GEMINI_API_KEY"):
    PROVIDERS.append("gemini")

if not PROVIDERS:
    print("[ERROR] No API keys found! Add at least one to .env:")
    print("   OPENROUTER_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY")
    exit(1)

print(f"[LLM] Active Providers: {', '.join(PROVIDERS)}")

# Initialize clients lazily
_clients = {}

def get_gemini_client():
    if "gemini" not in _clients:
        from google import genai
        _clients["gemini"] = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _clients["gemini"]

def get_groq_client():
    if "groq" not in _clients:
        from groq import Groq
        _clients["groq"] = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _clients["groq"]

# ─── Database ────────────────────────────────────────────────────────────────

def init_db():
    if not os.path.exists('data'): os.mkdir('data')
    conn = sqlite3.connect('data/factory.db')
    conn.execute("CREATE TABLE IF NOT EXISTS cache (company TEXT PRIMARY KEY, context TEXT)")
    conn.execute("""CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY, company TEXT, role TEXT, idea_name TEXT,
        problem TEXT, mermaid_code TEXT, stack TEXT, priority TEXT,
        company_profile TEXT, job_summary TEXT, mvp_score TEXT,
        source TEXT, scraped_at TEXT, job_link TEXT, job_description TEXT,
        decision TEXT DEFAULT 'UNREVIEWED', remark TEXT DEFAULT '')""")
    return conn

# ─── Research Cache ──────────────────────────────────────────────────────────

def get_cached_research(conn, company):
    res = conn.execute("SELECT context FROM cache WHERE company=?", (company,)).fetchone()
    if res: return res[0]
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(f"{company} software products services", max_results=2)]
            context = " ".join(results)
            conn.execute("INSERT INTO cache VALUES (?, ?)", (company, context))
            conn.commit()
            return context
    except:
        return "No additional context found."

# ─── LLM Calls ───────────────────────────────────────────────────────────────

def call_openrouter(prompt):
    api_key = os.getenv("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Product a Day Idea Factory"
    }
    payload = {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"]
    elif "error" in data:
        raise RuntimeError(f"OpenRouter API Error: {data['error']}")
    else:
        raise RuntimeError(f"Unexpected OpenRouter response format: {data}")

def call_groq(prompt):
    client = get_groq_client()
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-120b",
        temperature=0.7
    )
    return response.choices[0].message.content

def call_gemini(prompt):
    client = get_gemini_client()
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt
    )
    return response.text

PROVIDER_FUNCS = {
    "openrouter": call_openrouter,
    "groq": call_groq,
    "gemini": call_gemini
}

# ─── JSON Parsing Helper ────────────────────────────────────────────────────

def parse_json_response(raw_text):
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1]
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0]
    cleaned = cleaned.strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end+1]

    return json.loads(cleaned)

# ─── Idea Generation with Fallback ──────────────────────────────────────────

def generate_idea(job, context):
    known_stack = os.getenv('KNOWN_STACK', 'Node.js, Python')
    prompt = f"""
    Analyze this hiring need for {job['company']}.
    Context: {context}
    Role: {job['title']}
    JD: {job.get('description', 'Not available')}

    Task:
    1. Identify the internal pain point this role addresses.
    2. Suggest a UNIQUE standalone Workflow Product.
    3. Determine if it's 'Zero-to-One' or 'Incremental'.
    4. Provide Mermaid.js graph TD code.
    5. Suggest a stack using {known_stack} + 1 best-fit tool.
    6. Summarize the Company Profile (Name, Products/Services, Customers' pain points and vision).
    7. Provide a concise Summary of the Job Description.
    8. Provide an MVP Score (e.g., 85/100) and justify it based on technical feasibility, time-to-market, market size, and competitive advantage.

    Output JSON (ONLY JSON, no markdown fences):
    {{
      "idea_name": "...",
      "problem": "...",
      "mermaid": "graph TD; ...",
      "priority": "Zero-to-One",
      "stack": "...",
      "company_profile": "...",
      "job_summary": "...",
      "mvp_score": "..."
    }}
    """

    # Always try openrouter first, fallback to groq/gemini on failure
    for provider in PROVIDERS:
        try:
            print(f"   [{provider}] Generating idea...")
            raw_text = PROVIDER_FUNCS[provider](prompt)
            result = parse_json_response(raw_text)
            if result and isinstance(result, dict) and "idea_name" in result:
                return result
            else:
                print(f"   [WARN] [{provider}] Invalid JSON output structure. Trying next provider...")
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate" in err_str.lower() or "502" in err_str or "503" in err_str:
                print(f"   [WARN] [{provider}] Temporary provider issue/rate limit: {err_str[:80]}... Falling back...")
            else:
                print(f"   [ERROR] [{provider}] Error: {err_str[:80]}")
    return None

# ─── Main Pipeline ───────────────────────────────────────────────────────────

def main():
    conn = init_db()
    if not os.path.exists('data/raw_jobs.json'):
        print("[ERROR] No jobs found. Run scrapers first.")
        return

    with open('data/raw_jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    total = len(jobs)
    processed = 0
    skipped = 0

    print(f"\nTotal jobs to process: {total}")
    print(f"{'='*60}\n")

    for i, job in enumerate(jobs):
        # Skip if already processed
        existing = conn.execute("SELECT 1 FROM ideas WHERE company=? AND role=?", (job['company'], job['title'])).fetchone()
        if existing:
            skipped += 1
            continue

        print(f"[{i+1}/{total}] Processing {job['company']} - {job['title']}...")
        context = get_cached_research(conn, job['company'])
        idea = generate_idea(job, context)
        if idea:
            conn.execute("""INSERT INTO ideas (company, role, idea_name, problem, mermaid_code, stack, priority,
                         company_profile, job_summary, mvp_score, source, scraped_at, job_link, job_description)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (job['company'], job['title'], idea.get('idea_name'), idea.get('problem'),
                          idea.get('mermaid'), idea.get('stack'), idea.get('priority'),
                          idea.get('company_profile'), idea.get('job_summary'), idea.get('mvp_score'),
                          job.get('source', 'unknown'), job.get('scraped_at', ''),
                          job.get('link', ''), job.get('description', '')))
            conn.commit()
            processed += 1
            print(f"   [OK] Saved Idea: {idea.get('idea_name', 'Unknown')}")
        else:
            print(f"   [FAIL] Could not generate idea for {job['company']}")
        
        # Polite delay between requests
        time.sleep(1)

    conn.close()
    print(f"\n{'='*60}")
    print(f"Done! Processed: {processed} | Skipped: {skipped} | Failed: {total - processed - skipped}")

if __name__ == "__main__":
    main()
