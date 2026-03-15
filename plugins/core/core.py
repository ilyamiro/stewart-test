import logging

log = logging.getLogger(__name__)


def test_plugin(payload):
    print("TEST EVENT BUT IN PLUGINS")
    payload.data["key2"] = "прикольчик"

api.bus.add_event("app.start", 49, test_plugin, "event_blabla")

# # The 'api' variable is injected automatically by manager.py
#
# def identify_speaker_hook(event: Event):
#     """Priority 80: Modifies the event data but does not cancпередавай привет бабушке от меняel it."""
#     print("[Diarization Plugin] Analyzing audio data...")
#
#     # Simulating speaker identification
#     if event.data.get("audio_source") == "main_microphone":
#         event.data["speaker_name"] = "ilyamiro"
#         print("[Diarization Plugin] Speaker identified as ilyamiro. Passing data down.")
#     else:
#         print("[Diarization Plugin] Unknown speaker. Canceling event.")
#         event.handled = True  # STT will not run!
#
# def process_stt_hook(event: Event):
#     """Priority 50: The 'normal' hook that relies on the modified data."""
#     speaker = event.data.get("speaker_name", "Unknown")
#     print(f"[STT Plugin] Processing speech for: {speaker}")
#
#     # Emitting the final parsed text
#     api.bus.emit(Event(name="text.parsed", data={"text": "Turn on the lights", "speaker": speaker}, source="core/stt"))
#
# def setup():
#     # Because we updated EventBus, we now pass a plugin_id string ("core/diarization", "core/stt")
#
#     # Hook 1: The Modifier (High Priority)
#     api.bus.hook("audio.recorded", priority=80, plugin_id="core/diarization", callback=identify_speaker_hook)
#
#     # Hook 2: The Consumer (Lower Priority)
#     api.bus.hook("audio.recorded", priority=50, plugin_id="core/stt", callback=process_stt_hook)
#
#     log.info("Pipeline plugins registered.")
#
# setup()
#
# # You can test this by adding this to your app.process() method:
# # self.api.bus.emit(Event("audio.recorded", data={"audio_source": "main_microphone"}))