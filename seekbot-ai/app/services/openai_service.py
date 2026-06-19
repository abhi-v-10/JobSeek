# from openai import OpenAI
# from app.core.config import OPENAI_API_KEY
from app.core.openai_client import generate_chat_completion

# client = OpenAI(api_key=OPENAI_API_KEY)
# client = InferenceClient(provider="hf-inference", api_key=HF_TOKEN)


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


def ask_ai(current_message: str, history=None, file_context: str = None, image_base64: str = None):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if history:
        for msg in history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    user_content = []
    if current_message:
        user_content.append({"type": "text", "text": current_message})
    
    if file_context:
        user_content.append({"type": "text", "text": f"\n\n[DOCUMENT CONTEXT]:\n{file_context}"})
    
    if image_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

    messages.append({
        "role": "user",
        "content": user_content if (image_base64 or file_context) else current_message
    })

    response = generate_chat_completion(
        messages=messages,
        temperature=0.4,
        max_tokens=1000
    )

    return response.choices[0].message.content.strip()

def generate_chat_title(first_message: str):
    """Generate a concise 2-3 word title for a chat session."""
    try:
        response = generate_chat_completion(
            messages=[
                {"role": "system", "content": "Generate a concise 2-3 word title for a chat based on the user message. No quotes, no periods."},
                {"role": "user", "content": first_message}
            ],
            temperature=0.5,
            max_tokens=10
        )
        return response.choices[0].message.content.strip().replace('"', '')
    except:
        return first_message[:20] + "..."