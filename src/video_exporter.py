"""
video_exporter.py
-----------------
Combines a static image and a processed audio segment into an MP4 video file
using MoviePy and pydub.

The exported video contains a single still frame for the full duration of the
audio clip. Resolution can optionally be scaled to a standard preset.
"""

import os
import tempfile
from typing import Callable, Optional

from moviepy.editor import AudioFileClip, ImageClip
from pydub import AudioSegment


# Maps user-facing quality labels to (width, height) output resolutions.
# "Original" keeps the image at its natural size.
QUALITY_PRESETS = {
    "Original": None,
    "1080p": (1920, 1080),
    "720p": (1280, 720),
}


class VideoExporter:
    """
    Builds an MP4 video from a still image and an AudioSegment.

    This class is stateless. All parameters are passed directly to export().
    It is safe to call export() from a background thread.
    """

    def export(
        self,
        image_path: str,
        audio_segment: AudioSegment,
        output_path: str,
        quality: str = "Original",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Render and write the final MP4 file.

        The audio segment is written to a temporary WAV file so that MoviePy
        can attach it to the image clip. WAV is used because it is lossless
        and requires no additional codec lookup by ffmpeg.

        Parameters
        ----------
        image_path : str
            Path to the source image (JPEG, PNG, BMP, WEBP, etc.).
        audio_segment : AudioSegment
            Pre-processed audio (already trimmed and faded by AudioHandler).
        output_path : str
            Destination path for the MP4 file.
        quality : str
            One of "Original", "1080p", or "720p".
        progress_callback : callable, optional
            Called with a float in [0, 1] as the export progresses.
            Runs in the exporter thread - schedule UI updates with after().

        Raises
        ------
        ValueError
            If quality is not a recognised preset key.
        FileNotFoundError
            If image_path does not exist.
        """
        if quality not in QUALITY_PRESETS:
            raise ValueError(
                f"Unknown quality preset '{quality}'. "
                f"Valid options: {list(QUALITY_PRESETS)}"
            )

        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        duration = len(audio_segment) / 1000.0

        if progress_callback:
            progress_callback(0.05)

        # Write processed audio to a temporary WAV file.
        tmp_fd, tmp_audio_path = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)

        try:
            audio_segment.export(tmp_audio_path, format="wav")

            if progress_callback:
                progress_callback(0.20)

            image_clip = ImageClip(image_path).set_duration(duration)

            target_size = QUALITY_PRESETS[quality]
            if target_size is not None:
                image_clip = image_clip.resize(target_size)

            audio_clip = AudioFileClip(tmp_audio_path)
            video = image_clip.set_audio(audio_clip)

            if progress_callback:
                progress_callback(0.30)

            # logger=None suppresses MoviePy's stdout progress bar so it does
            # not interfere with the GUI.
            video.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )

            audio_clip.close()
            image_clip.close()

        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

        if progress_callback:
            progress_callback(1.0)
