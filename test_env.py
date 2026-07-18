# test_env.py
import pysrt
from deep_translator import GoogleTranslator
import edge_tts
from pydub import AudioSegment

print("✓ All libraries imported successfully!")
print(f"Testing translator (Urdu to Malayalam):")
try:
    translated = GoogleTranslator(source='ur', target='ml').translate("ہیلو")
    print(f"Result: {translated}")
except Exception as e:
    print(f"Translation failed: {e}")