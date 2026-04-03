"""
app.py
------
Main application window built with CustomTkinter.

Layout overview:
    - Header bar: application title
    - Left panel: image loading and preview
    - Right panel: audio loading, trim controls, playback, fade settings
    - Footer bar: quality selector, progress indicator, export button
"""

import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from .audio_handler import AudioHandler, format_time
from .video_exporter import QUALITY_PRESETS, VideoExporter


# Minimum gap in seconds enforced between the start and end trim points.
MIN_CLIP_DURATION = 0.5


class App(ctk.CTk):
    """
    Root window of the Image to Video Converter application.

    Responsibilities:
        - Render and manage all UI widgets.
        - Coordinate between AudioHandler (playback/trimming) and
          VideoExporter (rendering).
        - Run the export in a background thread so the UI stays responsive.
    """

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Image to Video Converter")
        self.geometry("1140x740")
        self.minsize(960, 640)

        self.image_path = None
        self.audio_path = None
        self.audio_duration = 0.0
        self._exporting = False

        self.audio_handler = AudioHandler()
        self.video_exporter = VideoExporter()

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._build_header()
        self._build_image_panel()
        self._build_audio_panel()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, height=52, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="Image to Video Converter",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            header,
            text="Combine a still image with an audio track and export as MP4",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray55"),
        ).pack(side="left", padx=4)

    def _build_image_panel(self):
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, padx=(12, 6), pady=10, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Image",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        self.image_preview = ctk.CTkLabel(
            panel,
            text="No image loaded.\nClick the button below to select one.",
            fg_color=("gray82", "gray18"),
            corner_radius=8,
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray55"),
        )
        self.image_preview.grid(row=1, column=0, padx=16, pady=6, sticky="nsew")

        self.image_filename_label = ctk.CTkLabel(
            panel,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        )
        self.image_filename_label.grid(row=2, column=0, padx=16, pady=(0, 4))

        ctk.CTkButton(
            panel,
            text="Load Image",
            command=self._load_image,
            height=36,
        ).grid(row=3, column=0, padx=16, pady=(4, 16), sticky="ew")

    def _build_audio_panel(self):
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=1, padx=(6, 12), pady=10, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Audio",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        self.audio_info_label = ctk.CTkLabel(
            panel,
            text="No audio loaded.",
            text_color=("gray45", "gray55"),
            font=ctk.CTkFont(size=12),
            wraplength=380,
            justify="left",
        )
        self.audio_info_label.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="w")

        ctk.CTkButton(
            panel,
            text="Load Audio",
            command=self._load_audio,
            height=36,
        ).grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkFrame(panel, height=1, fg_color=("gray75", "gray30")).grid(
            row=3, column=0, padx=16, sticky="ew"
        )

        self._build_trim_section(panel, start_row=4)

        ctk.CTkFrame(panel, height=1, fg_color=("gray75", "gray30")).grid(
            row=8, column=0, padx=16, pady=(8, 0), sticky="ew"
        )

        self._build_playback_section(panel, start_row=9)

        ctk.CTkFrame(panel, height=1, fg_color=("gray75", "gray30")).grid(
            row=11, column=0, padx=16, pady=(8, 0), sticky="ew"
        )

        self._build_fade_section(panel, start_row=12)

    def _build_trim_section(self, parent, start_row):
        ctk.CTkLabel(
            parent,
            text="Trim",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=start_row, column=0, padx=16, pady=(12, 4), sticky="w")

        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.grid(row=start_row + 1, column=0, padx=16, pady=0, sticky="ew")
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(inner, text="Start", width=38, anchor="w").grid(
            row=0, column=0, padx=(0, 8), pady=(4, 0)
        )
        self.start_slider = ctk.CTkSlider(
            inner,
            from_=0,
            to=100,
            command=self._on_start_changed,
            state="disabled",
        )
        self.start_slider.set(0)
        self.start_slider.grid(row=0, column=1, sticky="ew", pady=(4, 0))
        self.start_time_label = ctk.CTkLabel(inner, text="00:00.00", width=72, anchor="e")
        self.start_time_label.grid(row=0, column=2, padx=(8, 0), pady=(4, 0))

        ctk.CTkLabel(inner, text="End", width=38, anchor="w").grid(
            row=1, column=0, padx=(0, 8), pady=(8, 0)
        )
        self.end_slider = ctk.CTkSlider(
            inner,
            from_=0,
            to=100,
            command=self._on_end_changed,
            state="disabled",
        )
        self.end_slider.set(100)
        self.end_slider.grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self.end_time_label = ctk.CTkLabel(inner, text="00:00.00", width=72, anchor="e")
        self.end_time_label.grid(row=1, column=2, padx=(8, 0), pady=(8, 0))

        self.clip_duration_label = ctk.CTkLabel(
            parent,
            text="Clip duration: --",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        )
        self.clip_duration_label.grid(
            row=start_row + 2, column=0, padx=16, pady=(6, 4), sticky="w"
        )

    def _build_playback_section(self, parent, start_row):
        ctk.CTkLabel(
            parent,
            text="Preview",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=start_row, column=0, padx=16, pady=(12, 6), sticky="w")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.grid(row=start_row + 1, column=0, padx=16, pady=(0, 8), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.play_button = ctk.CTkButton(
            btn_row,
            text="Play",
            command=self._toggle_playback,
            state="disabled",
            height=34,
        )
        self.play_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        ctk.CTkButton(
            btn_row,
            text="Stop",
            command=self._stop_playback,
            height=34,
            fg_color=("gray60", "gray35"),
            hover_color=("gray45", "gray25"),
        ).grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def _build_fade_section(self, parent, start_row):
        ctk.CTkLabel(
            parent,
            text="Fade Effects",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=start_row, column=0, padx=16, pady=(12, 6), sticky="w")

        fade_row = ctk.CTkFrame(parent, fg_color="transparent")
        fade_row.grid(
            row=start_row + 1, column=0, padx=16, pady=(0, 4), sticky="ew"
        )

        ctk.CTkLabel(fade_row, text="Fade in (s)").grid(
            row=0, column=0, padx=(0, 8), sticky="w"
        )
        self.fade_in_entry = ctk.CTkEntry(fade_row, width=70, placeholder_text="0")
        self.fade_in_entry.grid(row=0, column=1, padx=(0, 20))

        ctk.CTkLabel(fade_row, text="Fade out (s)").grid(
            row=0, column=2, padx=(0, 8), sticky="w"
        )
        self.fade_out_entry = ctk.CTkEntry(fade_row, width=70, placeholder_text="0")
        self.fade_out_entry.grid(row=0, column=3)

        ctk.CTkLabel(
            parent,
            text="Leave blank or 0 to disable. Values are clamped to half the clip length.",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=start_row + 2, column=0, padx=16, pady=(2, 14), sticky="w")

    def _build_footer(self):
        footer = ctk.CTkFrame(self, corner_radius=0, height=64)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(footer, text="Output quality:").grid(
            row=0, column=0, padx=(16, 6)
        )
        self.quality_var = ctk.StringVar(value="Original")
        ctk.CTkOptionMenu(
            footer,
            variable=self.quality_var,
            values=list(QUALITY_PRESETS.keys()),
            width=110,
        ).grid(row=0, column=1, padx=(0, 16))

        progress_frame = ctk.CTkFrame(footer, fg_color="transparent")
        progress_frame.grid(row=0, column=2, sticky="ew", padx=8)
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=14)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        )
        self.progress_label.grid(row=1, column=0)

        self.export_button = ctk.CTkButton(
            footer,
            text="Export MP4",
            command=self._start_export,
            width=130,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.export_button.grid(row=0, column=3, padx=16)

    # ------------------------------------------------------------------
    # Image callbacks
    # ------------------------------------------------------------------

    def _load_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp")
            ],
        )
        if not path:
            return

        self.image_path = path
        img = Image.open(path)

        preview_img = img.copy()
        preview_img.thumbnail((460, 360))
        ctk_img = ctk.CTkImage(
            light_image=preview_img,
            dark_image=preview_img,
            size=preview_img.size,
        )

        self.image_preview.configure(image=ctk_img, text="")
        # Store reference to prevent garbage collection.
        self.image_preview._ctk_image_ref = ctk_img

        w, h = img.size
        self.image_filename_label.configure(
            text=f"{os.path.basename(path)}  ({w} x {h} px)"
        )

    # ------------------------------------------------------------------
    # Audio callbacks
    # ------------------------------------------------------------------

    def _load_audio(self):
        path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.wma")
            ],
        )
        if not path:
            return

        self.audio_path = path

        try:
            duration = self.audio_handler.load(path)
        except Exception as exc:
            messagebox.showerror(
                "Audio Load Error",
                f"Could not load the audio file.\n\n{exc}",
            )
            return

        self.audio_duration = duration
        self.audio_info_label.configure(
            text=f"{os.path.basename(path)}\nTotal duration: {format_time(duration)}"
        )

        self.start_slider.configure(state="normal", to=duration)
        self.end_slider.configure(state="normal", to=duration)
        self.start_slider.set(0)
        self.end_slider.set(duration)

        self.start_time_label.configure(text=format_time(0))
        self.end_time_label.configure(text=format_time(duration))
        self._refresh_duration_label()
        self.play_button.configure(state="normal")

    def _on_start_changed(self, value):
        """
        Enforce that the start point stays at least MIN_CLIP_DURATION seconds
        before the current end point.
        """
        end = self.end_slider.get()
        if value > end - MIN_CLIP_DURATION:
            value = max(0.0, end - MIN_CLIP_DURATION)
            self.start_slider.set(value)

        self.start_time_label.configure(text=format_time(value))
        self._refresh_duration_label()

    def _on_end_changed(self, value):
        """
        Enforce that the end point stays at least MIN_CLIP_DURATION seconds
        after the current start point.
        """
        start = self.start_slider.get()
        if value < start + MIN_CLIP_DURATION:
            value = min(self.audio_duration, start + MIN_CLIP_DURATION)
            self.end_slider.set(value)

        self.end_time_label.configure(text=format_time(value))
        self._refresh_duration_label()

    def _refresh_duration_label(self):
        clip_len = self.end_slider.get() - self.start_slider.get()
        self.clip_duration_label.configure(
            text=f"Clip duration: {format_time(clip_len)}"
        )

    # ------------------------------------------------------------------
    # Playback callbacks
    # ------------------------------------------------------------------

    def _toggle_playback(self):
        if self.audio_handler.is_playing:
            self._stop_playback()
        else:
            self.audio_handler.play_preview(
                self.start_slider.get(), self.end_slider.get()
            )
            self.play_button.configure(text="Pause")
            self._poll_playback_state()

    def _stop_playback(self):
        self.audio_handler.stop()
        self.play_button.configure(text="Play")

    def _poll_playback_state(self):
        """
        Check every 200 ms whether playback has ended naturally. When it has,
        reset the button label. This avoids blocking the Tkinter event loop.
        """
        if self.audio_handler.is_playing:
            self.after(200, self._poll_playback_state)
        else:
            self.play_button.configure(text="Play")

    # ------------------------------------------------------------------
    # Export callbacks
    # ------------------------------------------------------------------

    def _start_export(self):
        if self._exporting:
            return

        if not self.image_path:
            messagebox.showwarning("Missing Image", "Please load an image before exporting.")
            return

        if not self.audio_path:
            messagebox.showwarning("Missing Audio", "Please load an audio file before exporting.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
        )
        if not output_path:
            return

        start = self.start_slider.get()
        end = self.end_slider.get()

        fade_in = self._read_fade_value(self.fade_in_entry, "Fade in")
        fade_out = self._read_fade_value(self.fade_out_entry, "Fade out")
        if fade_in is None or fade_out is None:
            return

        # Clamp fade values so they cannot exceed half the clip length.
        max_fade = (end - start) / 2
        fade_in = min(fade_in, max_fade)
        fade_out = min(fade_out, max_fade)

        self._exporting = True
        self.export_button.configure(state="disabled", text="Exporting...")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Preparing...")

        self.audio_handler.stop()

        # Build the processed audio on the main thread (fast operation) before
        # the background thread takes over.
        audio_segment = self.audio_handler.build_trimmed_segment(
            start, end, fade_in=fade_in, fade_out=fade_out
        )

        def run():
            try:
                self.video_exporter.export(
                    image_path=self.image_path,
                    audio_segment=audio_segment,
                    output_path=output_path,
                    quality=self.quality_var.get(),
                    progress_callback=self._on_progress,
                )
                self.after(0, self._on_export_success, output_path)
            except Exception as exc:
                self.after(0, self._on_export_failure, str(exc))

        threading.Thread(target=run, daemon=True).start()

    def _on_progress(self, value):
        """
        Receives progress updates from the exporter thread and schedules
        UI changes on the main thread via after().
        """
        pct = int(value * 100)
        self.after(0, lambda v=value, p=pct: (
            self.progress_bar.set(v),
            self.progress_label.configure(text=f"{p}%"),
        ))

    def _on_export_success(self, output_path):
        self._exporting = False
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="Done")
        self.export_button.configure(state="normal", text="Export MP4")
        messagebox.showinfo(
            "Export Complete",
            f"Video saved successfully:\n{output_path}",
        )

    def _on_export_failure(self, error):
        self._exporting = False
        self.export_button.configure(state="normal", text="Export MP4")
        self.progress_label.configure(text="Failed")
        messagebox.showerror(
            "Export Failed",
            f"An error occurred during export:\n\n{error}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_fade_value(self, entry, label):
        """
        Parse a fade duration from a CTkEntry widget.

        Returns the float value on success, or None if the input is invalid.
        An error dialog is shown to the user before returning None.
        """
        raw = entry.get().strip()
        if raw in ("", "0"):
            return 0.0
        try:
            value = float(raw)
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                f"{label} must be a number (e.g. 1.5). Got: '{raw}'",
            )
            return None
        if value < 0:
            messagebox.showerror("Invalid Input", f"{label} cannot be negative.")
            return None
        return value

    def on_closing(self):
        """
        Clean up audio resources before the window is destroyed to prevent
        pygame from raising an error on exit.
        """
        self.audio_handler.cleanup()
        self.destroy()
