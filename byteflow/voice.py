"""
Offline voice support for the ByteFlow desktop companion.

- Speech-to-text: Vosk (https://alphacephei.com/vosk/) - fully offline,
  needs a one-time model download.
- Text-to-speech: pyttsx3 - uses your OS's built-in voices (SAPI5 on
  Windows, NSSpeechSynthesizer on macOS, espeak on Linux) - also fully
  offline, no model download needed.

Both are optional extras (pip install byteflow[voice]) so the rest of
ByteFlow has no dependency on them. Everything in this module fails
with a clear, actionable message if the libraries or model aren't
present - never a raw traceback.

Two ways to use voice input:
  - Listener: push-to-talk - you click to start, click to stop, then it
    transcribes what was recorded. Full control over when the mic is on.
  - ConversationListener: continuous/hands-free - once started, it keeps
    listening and automatically detects when you start and stop talking,
    firing a callback per utterance with no manual start/stop per phrase.
    You still explicitly start/stop the whole session.

Both require an explicit start() - no background microphone access
happens until you call it.
"""

import json
import os


DEFAULT_VOSK_MODEL_DIR = os.path.join(
    os.path.expanduser("~"), ".byteflow", "vosk-model"
)


class VoiceError(Exception):
    pass


def tts_available():
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        return False


def stt_available():
    try:
        import vosk  # noqa: F401
        import sounddevice  # noqa: F401
        return True
    except ImportError:
        return False


def vosk_model_present(model_dir=DEFAULT_VOSK_MODEL_DIR):
    return os.path.isdir(model_dir) and bool(os.listdir(model_dir))


class Speaker:
    """
    Text-to-speech, offline, via pyttsx3 (your OS's built-in voices).

    A new pyttsx3 engine is created per call to speak() rather than
    reused - some platforms' SAPI5/NSSpeechSynthesizer backends behave
    oddly with a long-lived engine instance across many calls from a
    background thread, and recreating it is cheap.
    """

    def __init__(self, rate=175, volume=1.0):
        if not tts_available():
            raise VoiceError(
                "Text-to-speech requires 'pyttsx3'. Install it with: "
                "pip install pyttsx3 (or: pip install byteflow[voice])"
            )
        self.rate = rate
        self.volume = volume

    def speak(self, text):
        """Speak `text` aloud. Blocks until speech finishes - call this
        from a background thread if you don't want the GUI to freeze."""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)
        engine.say(text)
        engine.runAndWait()
        engine.stop()


class Listener:
    """
    Push-to-talk speech-to-text, offline, via Vosk.

    Usage:
        listener = Listener()
        listener.start_recording()
        # ... user speaks ...
        text = listener.stop_recording()  # blocks briefly while transcribing

    Requires a downloaded Vosk model. See download instructions in
    byteflow/voice.py's MODEL_DOWNLOAD_HELP, or run:
        python -m byteflow.voice --download-model
    """

    SAMPLE_RATE = 16000

    def __init__(self, model_dir=DEFAULT_VOSK_MODEL_DIR):
        if not stt_available():
            raise VoiceError(
                "Speech-to-text requires 'vosk' and 'sounddevice'. Install with: "
                "pip install vosk sounddevice (or: pip install byteflow[voice])"
            )
        if not vosk_model_present(model_dir):
            raise VoiceError(
                f"No Vosk model found at {model_dir}. Download one from "
                "https://alphacephei.com/vosk/models (e.g. vosk-model-small-en-us-0.15), "
                f"unzip it, and place its contents at {model_dir}."
            )

        import vosk
        vosk.SetLogLevel(-1)  # quiet
        self._vosk = vosk
        self.model = vosk.Model(model_dir)
        self._frames = []
        self._stream = None

    def start_recording(self):
        """Begin capturing microphone audio. Non-blocking."""
        import sounddevice as sd

        self._frames = []

        def callback(indata, frames, time_info, status):
            self._frames.append(bytes(indata))

        self._stream = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE, blocksize=8000,
            dtype="int16", channels=1, callback=callback,
        )
        self._stream.start()

    def stop_recording(self):
        """
        Stop capturing and transcribe what was recorded. Returns the
        transcribed text (possibly empty if nothing intelligible was
        captured). Blocks briefly while Vosk processes the audio.
        """
        if self._stream is None:
            return ""

        self._stream.stop()
        self._stream.close()
        self._stream = None

        audio_bytes = b"".join(self._frames)
        self._frames = []

        if not audio_bytes:
            return ""

        rec = self._vosk.KaldiRecognizer(self.model, self.SAMPLE_RATE)
        rec.AcceptWaveform(audio_bytes)
        result = json.loads(rec.FinalResult())
        return result.get("text", "")


class ConversationListener:
    """
    Continuous, hands-free speech-to-text: starts listening once and keeps
    running, automatically detecting when you start and stop talking
    (no click to start/stop each utterance, unlike Listener above).

    Uses Vosk's own utterance segmentation: feed it a continuous audio
    stream, and its recognizer reports a "final" result the moment it
    detects a pause after speech (this is just how a streaming speech
    recognizer naturally works - it isn't separate VAD logic bolted on,
    it's the same mechanism Vosk uses internally for streaming results).

    Usage:
        conv = ConversationListener(on_utterance=lambda text: print(text))
        conv.start()   # begins listening; on_utterance fires automatically
        ...
        conv.stop()    # stops listening entirely

    on_utterance is called from a background thread - if you're updating
    a GUI from it, marshal back to the main thread yourself (see how
    run_companion() does this with root.after()).
    """

    SAMPLE_RATE = 16000
    # minimum recognized text length to count as a real utterance - this
    # filters out the empty/noise results Vosk occasionally emits on
    # silence or background sound, which would otherwise trigger empty
    # round-trips to the agent for nothing
    MIN_UTTERANCE_CHARS = 2

    def __init__(self, on_utterance, model_dir=DEFAULT_VOSK_MODEL_DIR,
                 on_partial=None, on_listening_change=None):
        """
        on_utterance(text): called with the final transcribed text each
            time Vosk detects you've finished speaking a phrase.
        on_partial(text): optional - called repeatedly with in-progress
            (not yet finalized) transcription, useful for showing live
            "you're saying..." feedback before the utterance completes.
        on_listening_change(is_listening: bool): optional - called when
            actively capturing speech vs. waiting in silence, useful for
            a visual "hearing you" indicator distinct from "mic is on".
        """
        if not stt_available():
            raise VoiceError(
                "Speech-to-text requires 'vosk' and 'sounddevice'. Install with: "
                "pip install vosk sounddevice (or: pip install byteflow[voice])"
            )
        if not vosk_model_present(model_dir):
            raise VoiceError(
                f"No Vosk model found at {model_dir}. Download one from "
                "https://alphacephei.com/vosk/models (e.g. vosk-model-small-en-us-0.15), "
                f"unzip it, and place its contents at {model_dir}."
            )

        import vosk
        vosk.SetLogLevel(-1)
        self._vosk = vosk
        self.model = vosk.Model(model_dir)
        self.on_utterance = on_utterance
        self.on_partial = on_partial
        self.on_listening_change = on_listening_change

        self._stream = None
        self._recognizer = None
        self._running = False
        self._was_speaking = False

    @property
    def running(self):
        return self._running

    def start(self):
        """Begin continuous listening. Non-blocking - runs via the audio
        callback thread that sounddevice manages internally."""
        if self._running:
            return

        import sounddevice as sd
        import json as _json

        self._recognizer = self._vosk.KaldiRecognizer(self.model, self.SAMPLE_RATE)
        self._running = True
        self._was_speaking = False

        def callback(indata, frames, time_info, status):
            if not self._running:
                return

            data = bytes(indata)
            is_final = self._recognizer.AcceptWaveform(data)

            if is_final:
                result = _json.loads(self._recognizer.Result())
                text = result.get("text", "").strip()
                if self._was_speaking:
                    self._was_speaking = False
                    if self.on_listening_change:
                        self.on_listening_change(False)
                if len(text) >= self.MIN_UTTERANCE_CHARS:
                    self.on_utterance(text)
            else:
                partial = _json.loads(self._recognizer.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    if not self._was_speaking:
                        self._was_speaking = True
                        if self.on_listening_change:
                            self.on_listening_change(True)
                    if self.on_partial:
                        self.on_partial(partial_text)

        self._stream = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE, blocksize=4000,
            dtype="int16", channels=1, callback=callback,
        )
        self._stream.start()

    def stop(self):
        """Stop listening entirely. Safe to call even if not running."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._recognizer = None


MODEL_DOWNLOAD_HELP = f"""
To use voice input, download a Vosk speech model (one-time, fully offline after this):

  1. Go to https://alphacephei.com/vosk/models
  2. Download a small English model, e.g. vosk-model-small-en-us-0.15.zip (~40MB)
  3. Unzip it
  4. Move/rename the unzipped folder's CONTENTS into:
     {DEFAULT_VOSK_MODEL_DIR}

After that, voice input in `byteflow companion` will work automatically.
"""


if __name__ == "__main__":
    print(MODEL_DOWNLOAD_HELP)
