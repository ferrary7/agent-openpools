import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect, Start
from src.voice.transcriber import RealTimeTranscriber
from src.agents.extractor import ExtractionAgent
import json
import base64
import asyncio
import os

app = FastAPI()

# Helper to manage global state (in a real app, this would be per-session)
from src.core.profile_manager import ProfileManager
profile_manager = ProfileManager()
# Ensure we have a user/funnel to work with
user_id = "user_001" 
extractor = ExtractionAgent()

# Callback to handle final transcripts
async def process_transcript(text):
    print(f"\n🗣️ Transcript: {text}")
    
    # 0. Log to file for Streamlit to read
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/transcripts.log", "a", encoding="utf-8") as f:
            f.write(f"{text}\n")
    except Exception as e:
        print(f"Error logging to file: {e}")
    
    # 1. Extract Intents/Keywords
    updates = extractor.extract(text)
    print(f"🧠 AI Extracted: {updates}")
    
    # 2. Update the Active Funnel
    if updates:
        user_data = profile_manager.get_user(user_id)
        if user_data and user_data.get('active_funnel_id'):
            funnel_id = user_data['active_funnel_id']
            profile_manager.update_funnel(user_id, funnel_id, updates)
            print(f"✅ Funnel Updated! Refresh Streamlit to see changes.")

from fastapi import Request

@app.get("/")
async def root():
    import os
    aai_key = os.getenv("ASSEMBLYAI_API_KEY")
    return {
        "status": "Voice Server Online", 
        "version": "1.4.4-TRACKING-TEST", 
        "aai_key_found": bool(aai_key),
        "user_id": user_id,
        "endpoints": ["/voice", "/stream"]
    }

@app.post("/voice")
async def voice_webhook(request: Request):
    print("\n" + "!"*40)
    print("WEBHOOK HIT: /voice")
    
    host = request.headers.get("host")
    response = VoiceResponse()
    
    # 1. Start the Stream (runs in parallel with Dial)
    protocol = "wss" if "ngrok-free.app" in host else "ws"
    stream_url = f"{protocol}://{host}/stream"
    print(f"Generated Stream URL: {stream_url}")
    
    # Use Start instead of Connect to allow parallel Dial
    start = Start()
    start.stream(url=stream_url, track="outbound_track")  # Only capture your voice
    response.append(start)
    
    # 2. Provide feedback
    response.say("Connecting you now.")
    
    # 3. BRIDGE THE CALL (this will now work in parallel with the stream)
    response.dial("+919156906939", callerId="+17655080999") 
    
    print(f"TwiML Response:\n{response}")
    print("!"*40 + "\n")
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    print("\n" + "*"*40)
    print("WS: Incoming connection request...")
    await websocket.accept()
    print("WS: Connected and Accepted!")
    print("*"*40 + "\n")
    
    transcriber = RealTimeTranscriber(
        on_data_callback=process_transcript,
        loop=asyncio.get_event_loop()
    )
    transcriber.start()

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data['event'] == 'start':
                print(f"🎬 WS: Stream starting (SID: {data['start']['streamSid']})")
            elif data['event'] == 'media':
                media_payload = data['media']['payload']
                audio_data = base64.b64decode(media_payload)
                # print(".", end="", flush=True) 
                transcriber.stream(audio_data)
            elif data['event'] == 'stop':
                print("🛑 WS: Stream stopped by Twilio")
                break
            elif data['event'] == 'mark':
                print("📍 WS: Custom Mark Received")
    except Exception as e:
        print(f"❌ WS: Error: {e}")
    finally:
        print("🏁 WS: Closing...")
        transcriber.close()
        try:
            await websocket.close()
        except:
            pass
        print("🏁 WS: Handler Finished")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
