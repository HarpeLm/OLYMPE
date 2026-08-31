from voice.stt._helpers import *


class AudioRecorder:
    """Enregistreur audio avec buffer circulaire."""

    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.recording = False

    def callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Warning] {status}", file=sys.stderr)
        self.audio_queue.put(indata.copy())

    def start(self):
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self.callback,
            blocksize=int(self.sample_rate * 0.1),
        )
        self.stream.start()

    def stop(self):
        self.recording = False
        if hasattr(self, "stream"):
            self.stream.stop()
            self.stream.close()

    def get_audio(self, duration_seconds):
        """Récupère l'audio accumulé pour une durée donnée."""
        num_frames = int(duration_seconds * self.sample_rate)
        audio_chunks = []
        frames_collected = 0

        while frames_collected < num_frames:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                audio_chunks.append(chunk)
                frames_collected += len(chunk)
            except queue.Empty:
                if not self.recording:
                    break

        if not audio_chunks:
            return None

        audio = np.concatenate(audio_chunks, axis=0)
        if len(audio) > num_frames:
            audio = audio[:num_frames]

        return audio.squeeze()
