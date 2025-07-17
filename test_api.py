import google.generativeai as genai
import os

# IMPORTANT: You must set your API key as an environment variable for this script.
# Open your terminal and run this command before running the script:
# set GOOGLE_API_KEY="YOUR_API_KEY_HERE"
# (Replace with your actual key)

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("ERROR: GOOGLE_API_KEY environment variable not set.")
    print("Please run 'set GOOGLE_API_KEY=\"your_key_here\"' in your terminal first.")
    exit()

print("Successfully configured API key. Fetching available models...\n")

# Find all models that support the 'generateContent' method
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Model found: {m.name}")

print("\n---")
print("Recommendation: Choose one of the model names from the list above and use it in your google_api_validator.py file.")
print("The most likely correct name for your task is the one containing 'gemini' and 'pro'.") 