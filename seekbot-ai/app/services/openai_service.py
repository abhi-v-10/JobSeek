from openai import OpenAI
from app.core.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """
You are SeekBot, AI career agent of JobSeek.

Help users with jobs, resumes, skills, projects, interviews, and career growth.

RULES:

1. Keep replies concise.
2. Sound natural and helpful.
3. Use short bullets or numbered steps.
4. Avoid robotic wording.
5. Avoid essays.
6. Default length: under 120 words.
7. Be practical and modern.
8. Give exact next steps.
9. If roadmap requested, make it step-by-step.
10. If user asks simple question, answer briefly.

FORMAT:

- Plain clean text
- No markdown headings
- No unnecessary intro or outro
- Easy to read in chat UI
"""


def ask_ai(current_message: str, history=None):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if history:
        for msg in history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({
        "role": "user",
        "content": current_message
    })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4,
        max_tokens=140
    )

    return response.choices[0].message.content.strip()