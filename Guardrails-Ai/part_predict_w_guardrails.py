import re
import json
import time
import random
from guardrails import Guard, OnFailAction
# from guardrails.hub import GuardrailsPII, ToxicLanguage, RegexMatch
from pydantic import BaseModel, Field
from typing import List, Dict
from dotenv import load_dotenv
import os
load_dotenv()
OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')
from openai import OpenAI

from guardrails import Guard, OnFailAction
from guardrails.hub.registry import load_validator
from pydantic import BaseModel, Field

# Load validators from Hub Registry
GuardrailsPII = load_validator("guardrails/guardrails-pii")
ToxicLanguage = load_validator("guardrails/guardrails-toxic-language")
RegexMatch = load_validator("guardrails/guardrails-regex-match")


client = OpenAI(api_key=OPENAI_API_KEY)

# ====== 1. DEFINE OUTPUT SCHEMA ======
# class PartResponse(BaseModel):
#     part_number: str = Field(description="Predicted part number for the appliance")
#     reason: str = Field(description="Why this part is likely required")
#     confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
class PartResponse(BaseModel):
    # Add only 'Yes' or 'No' as valid responses
    valid_prompt: str = Field(description="Indicates if the prompt is valid", regex="^(yes|no)$")
    causes: List[Dict[str, List[str]]] = Field(description="List of causes and their required parts")

# ====== 2. DEFINE INPUT GUARD ======
input_guard = Guard().use_many(
    GuardrailsPII(
        entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "IN_AADHAAR"],
        on_fail=OnFailAction.EXCEPTION,
    ),
    RegexMatch(
        regex=r"(fuck|shit|bitch|bypass|ignore all|jailbreak|sudo|rm -rf)",
        on_fail=OnFailAction.EXCEPTION,
    ),
    RegexMatch(
        regex=r"(appliance|problem|fault|error)",
        on_fail=OnFailAction.EXCEPTION,
    ),
)


def validate_user_prompt(prompt: str):
    """Validate user input; retry after cleanup if fails."""
    for attempt in range(2):
        try:
            input_guard.validate(prompt)
            print("✅ Input validation passed.")
            return prompt
        except Exception as e:
            print(f"🚫 Input validation failed: {e}")
            if attempt == 0:
                # Try sanitizing prompt
                print("🧹 Attempting to clean prompt and retry...")
                prompt = re.sub(
                    r"(fuck|shit|bitch|bypass|ignore all|jailbreak|sudo|rm -rf)",
                    "[REDACTED]",
                    prompt,
                    flags=re.IGNORECASE,
                )
                prompt = re.sub(r"\b\d{10}\b", "[PHONE]", prompt)
            else:
                raise Exception("🚫 Prompt invalid after auto-correction.")
    return prompt


# ====== 3. DEFINE OUTPUT GUARD ======
output_guard = Guard(PartResponse).use_many(
    ToxicLanguage(
        threshold=0.3, validation_method="sentence", on_fail=OnFailAction.EXCEPTION
    ),
    GuardrailsPII(
        entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "IN_AADHAAR"],
        on_fail=OnFailAction.EXCEPTION,
    ),
)


def validate_llm_response(response: str):
    """Validate and parse LLM output with retries."""
    for attempt in range(2):
        try:
            parsed = output_guard.parse(response)
            print("✅ Output validation passed.")
            return parsed
        except Exception as e:
            print(f"🚫 Output validation failed: {e}")
            if attempt == 0:
                print("🔁 Asking LLM to reformat response correctly...")
                response = auto_correct_output(response)
            else:
                raise Exception("🚫 LLM output invalid after correction.")
    return response


# ====== 4. MOCK LLM CALL ======
def mock_call_llm(prompt: str) -> str:
    """Simulate an LLM call. Replace with OpenAI or other API."""
    print("🤖 Sending prompt to LLM...")
    time.sleep(1)
    # 20% chance to return bad data to simulate failures
    if random.random() < 0.2:
        return "Here's the part: 123-XYZ, contact me at email@example.com"
    return json.dumps(
        {
            "part_number": "123-XYZ",
            "reason": "Based on the fault code and noise pattern, this motor is likely defective.",
            "confidence": 0.91,
        }
    )

def call_llm(prompt: str, model="gpt-4o-mini") -> str:
    response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a Home Appliances Technician and have a deep understanding of appliance issues and repairs. You are task is to confirm whether the problem is related to give appliance or not. If its not then return JSON response with 'No Valid Problem', otherwise identifying the different causes for the given appliance issue and the parts required to repair it as per its cause. Please provide a detailed response in json format as give below "\
            "{{'valid_problem': 'yes', 'causes': [{{'cause': 'cause_1', 'required_parts': ['part_1', 'part_2']}}, {{'cause': 'cause_2', 'required_parts': ['part_3']}}]}}. If the problem is not related to the appliance, return {{'valid_problem': 'no'}}."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3
)

# ------------------------------
# Print the generated structured JSON
# ------------------------------
generated_output = response.choices[0].message.content
print(generated_output)


# ====== 5. AUTO-CORRECTION FOR OUTPUT ======
def auto_correct_output(bad_output: str) -> str:
    """Fix formatting issues — e.g., extract JSON or sanitize text."""
    # Try to extract JSON substring if model wrapped it in text
    match = re.search(r"\{.*\}", bad_output, re.DOTALL)
    if match:
        return match.group(0)
    # If no JSON found, generate a fallback JSON
    return json.dumps(
        {
            "part_number": "UNKNOWN",
            "reason": "Auto-corrected due to invalid format.",
            "confidence": 0.5,
        }
    )


# ====== 6. MAIN PIPELINE ======
def run_pipeline():
    prompt = input("Enter appliance problem: ")

    # Step 1 — Input Guard
    clean_prompt = validate_user_prompt(prompt)

    # Step 2 — LLM Call
    response = call_llm(clean_prompt)
    print("🔹 Raw LLM output:", response)

    # Step 3 — Output Guard & Retry
    parsed = validate_llm_response(response)

    print("\n🔸 Final structured response:")
    print(parsed)


if __name__ == "__main__":
    run_pipeline()
