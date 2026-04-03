"""
audio_handler.py
----------------
Manages all audio-related operations: loading, playback preview, and trimming.

Playback is handled by pygame.mixer, which runs independently of the Tkinter
event loop. Trimming and fade effects are applied through pydub before the
audio is handed off to the video exporter.
"""

import io
import threading
import time

import pygame
from pydub import AudioSegment


def format_time(seconds: float) -> str:
    """
    Convert a duration in seconds to a human-readable MM:SS.ss string.

    Parameters
    ----------
    seconds : float
        Duration in seconds.

    Returns
    -------
    str
        Formatted string, e.g. "01:34.50".
    """
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


class AudioHandler:
    """
    Handles audio loading, in-app playback, and segment processing.

    Uses pygame.mixer for playback and pydub for audio manipulation.
    Only the mixer subsystem is initialised to avoid conflicts with Tkinter.

    Attributes
    ----------
    audio_segment : AudioSegment or None
        The currently loaded audio held in memory.
    duration : float
        Total duration of the loaded audio in seconds.
    is_playing : bool
        True while a preview playback is active.
    """

    def __init__(self):
        # Only initialise the mixer, not the full pygame display system,
        # to avoid conflicts with Tkinter's own event loop.
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.audio_segment = None
        self.duration = 0.0
        self.is_playing = False

        self._stop_event = threading.Event()
        self._playback_thread = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, path: str) -> float:
        """
        Load an audio file from disk and return its duration in seconds.

        Supports any format that pydub/ffmpeg can decode (MP3, WAV, OGG,
        FLAC, M4A, AAC, etc.).

        Parameters
        ----------
        path : str
            Path to the audio file.

        Returns
        -------
        float
            Duration of the audio in seconds.

        Raises
        ------
        Exception
            Propagates any exception raised by pydub (missing codec, corrupt
            file, unsupported format, etc.).
        """
        self.stop()
        self.audio_segment = AudioSegment.from_file(path)
        self.duration = len(self.audio_segment) / 1000.0
        return self.duration

    def play_preview(self, start: float, end: float) -> None:
        """
        Play the audio between start and end seconds through the default
        audio output. Stops any current playback before starting.

        Parameters
        ----------
        start : float
            Start position in seconds.
        end : float
            End position in seconds.
        """
        if self.audio_segment is None:
            return

        self.stop()
        self._stop_event.clear()

        # Slice and render to an in-memory WAV buffer so pygame can play it
        # without writing a temp file to disk.
        slice_ms = self.audio_segment[int(start * 1000): int(end * 1000)]
        buffer = io.BytesIO()
        slice_ms.export(buffer, format="wav")
        buffer.seek(0)

        pygame.mixer.music.load(buffer)
        pygame.mixer.music.play()
        self.is_playing = True

        clip_duration = end - start
        self._playback_thread = threading.Thread(
            target=self._watch_playback,
            args=(clip_duration,),
            daemon=True,
        )
        self._playback_thread.start()

    def stop(self) -> None:
        """Stop any active playback immediately."""
        self._stop_event.set()
        pygame.mixer.music.stop()
        self.is_playing = False

    def build_trimmed_segment(
        self,
        start: float,
        end: float,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> AudioSegment:
        """
        Return a processed AudioSegment ready for export.

        Parameters
        ----------
        start : float
            Trim start in seconds.
        end : float
            Trim end in seconds.
        fade_in : float
            Fade-in duration in seconds. Pass 0 to skip.
        fade_out : float
            Fade-out duration in seconds. Pass 0 to skip.

        Returns
        -------
        AudioSegment
            The trimmed and optionally faded audio segment.

        Raises
        ------
        RuntimeError
            If no audio has been loaded yet.
        """
        if self.audio_segment is None:
            raise RuntimeError("No audio loaded. Call load() first.")

        segment = self.audio_segment[int(start * 1000): int(end * 1000)]

        if fade_in > 0:
            segment = segment.fade_in(int(fade_in * 1000))
        if fade_out > 0:
            segment = segment.fade_out(int(fade_out * 1000))

        return segment

    def cleanup(self) -> None:
        """Release all resources. Call this before the application exits."""
        self.stop()
        pygame.mixer.quit()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _watch_playback(self, duration: float) -> None:
        """
        Background thread that flips is_playing to False after the clip has
        finished playing, or immediately when stop() is called.
        """
        deadline = time.time() + duration
        while time.time() < deadline:
            if self._stop_event.is_set():
                return
            time.sleep(0.05)
        self.is_playing = False
