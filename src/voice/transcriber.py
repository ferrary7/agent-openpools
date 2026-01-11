import os
import asyncio
from typing import Callable
from dotenv import load_dotenv
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingParameters,
    StreamingEvents,
    BeginEvent,
    TurnEvent,
    TerminationEvent,
    StreamingError,
)

load_dotenv()

class RealTimeTranscriber:
    def __init__(self, on_data_callback: Callable[[str], None], loop=None):
        print("🛠️  Transcriber Initialized (V3 API)")
        self.on_data_callback = on_data_callback
        self.client = None
        self._is_connected = False
        self.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        # Buffer to accumulate audio chunks (Twilio sends 20ms, AAI needs 50ms+)
        self.audio_buffer = bytearray()
        self.buffer_size = 480  # 60ms at 8000 Hz, mulaw = 8000 * 0.06 = 480 bytes
        # Store the event loop for callbacks
        self.loop = loop or asyncio.get_event_loop()
        
    def on_begin(self, client, event: BeginEvent):
        print(f"✅ AssemblyAI Session Opened: {event.id}")
        self._is_connected = True

    def on_turn(self, client, event: TurnEvent):
        if not event.transcript:
            return
        
        if event.end_of_turn:
            print(f"🎤 [Final] {event.transcript}")
            if self.on_data_callback and self.loop:
                # Schedule the callback in the FastAPI event loop
                asyncio.run_coroutine_threadsafe(
                    self.on_data_callback(event.transcript), 
                    self.loop
                )
        else:
            print(f"🎤 [Partial] {event.transcript}", end="\r")

    def on_error(self, client, error: StreamingError):
        print(f"❌ AssemblyAI Error: {error}")

    def on_terminated(self, client, event: TerminationEvent):
        print(f"🔒 AssemblyAI Session Closed ({event.audio_duration_seconds}s processed)")
        self._is_connected = False

    def start(self):
        print("🔗 Connecting to AssemblyAI V3...")
        self.client = StreamingClient(
            StreamingClientOptions(
                api_key=self.api_key,
                api_host="streaming.assemblyai.com"
            )
        )
        
        # Register event handlers
        self.client.on(StreamingEvents.Begin, self.on_begin)
        self.client.on(StreamingEvents.Turn, self.on_turn)
        self.client.on(StreamingEvents.Error, self.on_error)
        self.client.on(StreamingEvents.Termination, self.on_terminated)
        
        # Connect with streaming parameters optimized for complete sentences
        self.client.connect(
            StreamingParameters(
                sample_rate=8000,
                encoding="pcm_mulaw",
                format_turns=True,
                # Increase silence thresholds to wait for complete sentences
                min_end_of_turn_silence_when_confident=1500,  # 1.5s silence before finalizing
                max_turn_silence=3000,  # Max 3s silence within a turn
                end_of_turn_confidence_threshold=0.8,  # Higher confidence needed
                vad_threshold=0.3  # Voice activity detection threshold
            )
        )

    def stream(self, audio_data: bytes):
        if self.client and self._is_connected:
            # Add to buffer
            self.audio_buffer.extend(audio_data)
            
            # Send when we have enough data (60ms chunks)
            while len(self.audio_buffer) >= self.buffer_size:
                chunk = bytes(self.audio_buffer[:self.buffer_size])
                self.client.stream(chunk)
                self.audio_buffer = self.audio_buffer[self.buffer_size:]

    def close(self):
        if self.client:
            print("Closing AssemblyAI connection...")
            self.client.disconnect(terminate=True)
            self.client = None
