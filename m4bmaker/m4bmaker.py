import json
import shutil
import subprocess as sp
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from m4bmaker.exceptions import LoggedFileError, LoggedValueError
from m4bmaker.logger import logger_factory
from m4bmaker.types import TrackData


class M4BMaker:
    MODES = Enum("Mode", ["json", "single", "chapter"])
    AUDIO_BITRATES = Enum("AudioBitrate", ["64k", "128k"])
    ILLEGAL_CHARS = r"""<>"|?*'"""
    INPUT_TYPES = [".mp3", ".m4a"]
    OUTPUT_TYPE = ".m4b"

    def __init__(
        self,
        json_path: Path = Path.cwd() / "audiobook.json",
        mode: Literal["json", "single", "chapter"] = "json",
        output_bitrate: Literal["64k", "128k"] = "64k",
        log_path: Path = Path.cwd() / "m4bmaker.log",
    ):
        self.lg = logger_factory(log_path=log_path)
        self.lg.info("Initializing AudioBook class.")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise LoggedFileError("ffmpeg/ffprobe not found.", self.lg)

        try:
            self.json_path = Path(json_path)
            with open(self.json_path, "r", encoding="utf8") as f:
                self._raw_data = json.load(f)
            self.mode = self.MODES[mode.lower()]
            self.output_bitrate = self.AUDIO_BITRATES[output_bitrate.lower()].name
        except FileNotFoundError as exc:
            raise LoggedFileError(f"JSON file not found: {json_path}", self.lg) from exc
        except json.JSONDecodeError as exc:
            raise LoggedValueError(f"Invalid JSON file: {json_path}", self.lg) from exc
        except KeyError as exc:
            raise LoggedValueError(f"Invalid mode or bitrate: {exc}", self.lg) from exc

        self.lg.info(f"Selected mode: {self.mode.name}")
        self.lg.info(f"Selected output bitrate: {self.output_bitrate}")
        self.lg.debug(f"Loaded JSON data:\n{json.dumps(self._raw_data, indent=2)}")

        self._validate_book_path()
        self._validate_book_metadata()
        self._validate_book_cover()

        self.output_path = self.path / "output"
        self.tracks = {
            self.MODES.json: self._prep_tracks_json_mode,
            self.MODES.single: self._prep_tracks_single_mode,
            self.MODES.chapter: self._prep_tracks_chapter_mode,
        }[self.mode]()
        self._validate_tracks()

        self._prep_temp_files()

        self.lg.info("Data validation & preparation complete.")
        self.lg.debug(f"Processed data:\n{json.dumps(self.to_dict(), indent=2)}")

    def _cleaner(self, string: str) -> str:
        cleaned = string.translate(str.maketrans("", "", self.ILLEGAL_CHARS))
        if not cleaned:
            raise LoggedValueError(f"String is empty after cleaning: {string}", self.lg)
        return cleaned

    def _validate_book_path(self) -> None:
        self.lg.debug("Validating book path.")
        path = self._raw_data["path"]
        if any(char in path for char in self.ILLEGAL_CHARS):
            raise LoggedValueError(f"Book path has illegal characters: {path}", self.lg)
        if not Path(path).resolve().is_dir():
            raise LoggedFileError(f"Book path not found: {path}", self.lg)
        self.path = Path(path).resolve()

    def _validate_book_metadata(self) -> None:
        self.lg.debug("Validating book metadata.")
        self.title = self._raw_data.get("title", "").strip() or self.path.name.strip()
        self.author = self._raw_data.get("author", "").strip()
        self.narrator = self._raw_data.get("narrator", "").strip()
        self.genre = self._raw_data.get("genre", "").strip()
        self.year = self._raw_data.get("year", "").strip()
        self.disc = self._raw_data.get("disc", "").strip()
        if self.disc and "/" not in self.disc:
            if self._raw_data.get("total_discs", "").strip():
                self.disc += f"/{self._raw_data.get('total_discs', '').strip()}"

    def _validate_book_cover(self) -> None:
        self.lg.debug("Validating book cover.")
        self.cover = ""
        if not self._raw_data["cover"]:
            self.lg.debug("No cover image provided.")
            return
        cover = (self.path / self._raw_data["cover"]).resolve()
        if not (cover).is_file():
            raise LoggedFileError(f"Book cover not found: {cover}", self.lg)
        if cover.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
            raise LoggedFileError(f"Bad book cover type: {cover.suffix}", self.lg)
        self.cover = cover

    def _validate_tracks(self) -> None:
        self.lg.debug("Validating tracks.")
        input_formats = set()
        if not self.tracks:
            raise LoggedFileError("Book metadata as no tracks.", self.lg)
        for track in self.tracks:
            if not track["chapters"]:
                raise LoggedFileError(
                    f"Track has no chapters: {track['title']}", self.lg
                )
            for chapter in track["chapters"]:
                if not chapter["files"]:
                    raise LoggedFileError(
                        f"Chapter has no files: {chapter['title']}", self.lg
                    )
                for file in chapter["files"]:
                    input_formats.add(file.suffix.lower())
        if len(input_formats) > 1:
            raise LoggedFileError(
                f"Multiple input file formats found: {input_formats}", self.lg
            )
        self._input_format = input_formats.pop()
        self.lg.debug(f"Will create {len(self.tracks)} track(s).")

    def _prep_tracks_single_mode(self) -> list[TrackData]:
        # combine all input files into a single file
        self.lg.debug("Preparing tracks in single mode, ignoring track data in JSON.")
        files = [p for p in self.path.iterdir() if p.suffix.lower() in self.INPUT_TYPES]
        track = {
            "file": self.output_path / f"{self._cleaner(self.title)}{self.OUTPUT_TYPE}",
            "title": self.title,
            "track_no": "1/1",
            "chapters": [
                {"title": f"Chapter {i + 1}", "files": [file]}
                for i, file in enumerate(sorted(files))
            ],
        }
        return [track]

    def _prep_tracks_chapter_mode(self) -> list[TrackData]:
        # each input file is a chapter
        self.lg.debug("Preparing tracks in chapter mode, ignoring track data in JSON.")
        files = [p for p in self.path.iterdir() if p.suffix.lower() in self.INPUT_TYPES]
        return [
            {
                "file": self.output_path
                / f"{self._cleaner(file.stem)}{self.OUTPUT_TYPE}",
                "title": file.stem,
                "track_no": f"{i + 1}/{len(files)}",
                "chapters": [{"title": file.stem, "files": [file]}],
            }
            for i, file in enumerate(sorted(files))
        ]

    def _prep_tracks_json_mode(self) -> list[TrackData]:
        # create tracks and chapters based on json
        self.lg.debug("Preparing tracks in JSON mode.")
        for tr, track in enumerate(self._raw_data["tracks"]):
            default_title = f"{self.title} {tr + 1}"
            track_file = track.get("file", "") or f"{default_title}{self.OUTPUT_TYPE}"
            if not track_file.endswith(self.OUTPUT_TYPE):
                raise LoggedValueError(f"Invalid track format: {track_file}", self.lg)
            track["file"] = self.output_path / self._cleaner(track_file)
            track["title"] = track.get("title", "") or f"{self.title} {tr + 1}"
            track["track_no"] = f"{tr + 1}/{len(self._raw_data['tracks'])}"

            for ch, chapter in enumerate(track["chapters"]):
                chapter["title"] = chapter.get("title", "") or f"Chapter {ch + 1}"
                for f, file in enumerate(chapter["files"]):
                    file_path = (self.path / file).resolve()
                    if not file_path.is_file():
                        raise LoggedFileError(
                            f"Input file not found: {file_path}", self.lg
                        )
                    if file_path.suffix.lower() not in self.INPUT_TYPES:
                        raise LoggedFileError(
                            f"Invalid input file format: {file_path}", self.lg
                        )
                    chapter["files"][f] = file_path
        return self._raw_data["tracks"]

    def _prep_temp_files(self):
        self.lg.debug("Preparing temporary files.")
        self.output_path.mkdir(parents=True, exist_ok=True)
        for tr, track in enumerate(self.tracks):
            input_list_path = self.output_path / f"track_{tr + 1}_files.txt"
            with open(input_list_path, "w", encoding="utf-8") as f:
                for chapter in track["chapters"]:
                    for file in chapter["files"]:
                        file = str(file).replace("'", "'\\''")
                        f.write(f"file '{file}'\n")
            track["temp_files"] = track.get("temp_files", {})
            track["temp_files"]["input_list"] = input_list_path
        self._prep_chapter_data_files()
        self.lg.debug(f"{len(self.tracks) * 2} text files created: {self.output_path}")

    def _prep_chapter_data_files(self):
        self.lg.debug("Preparing chapter data files.")
        for tr, track in enumerate(self.tracks):
            start_time = 0
            chapter_data = ""
            for chapter in track["chapters"]:
                duration = 0
                for file in chapter["files"]:
                    cmd = [
                        "ffprobe", "-i", file, "-loglevel", "quiet", "-hide_banner",
                        "-show_entries", "format=duration", "-of", "csv=p=0",
                    ]  # fmt: skip
                    duration += float(self._run_ff(cmd))

                chapter_data += f"[CHAPTER]\nTIMEBASE=1/1\nSTART={int(start_time)}\n"
                chapter_data += f"END={int(start_time) + int(duration)}\n"
                chapter_data += f"title={chapter['title']}\n"
                start_time += duration

            chapter_data_file = self.output_path / f"track_{tr + 1}_chapters.txt"
            with open(chapter_data_file, "w", encoding="utf-8") as f:
                f.write(";FFMETADATA1\n")
                f.write(f"title={track['title']}\n")
                f.write(f"artist={self.author}\n")
                f.write(f"album_artist={self.author}\n")
                f.write(f"composer={self.narrator}\n")
                f.write(f"album={self.title}\n")
                f.write(f"genre={self.genre}\n")
                f.write(f"track={track['track_no']}\n")
                f.write(f"disc={self.disc}\n")
                f.write(f"date={self.year}\n")
                f.write(chapter_data)

            track["temp_files"]["chapter_data"] = chapter_data_file
            track["duration"] = datetime.fromtimestamp(start_time).strftime("%H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "output_path": str(self.output_path),
            "title": self.title,
            "author": self.author,
            "narrator": self.narrator,
            "genre": self.genre,
            "year": self.year,
            "disc": self.disc,
            "tracks": [
                {
                    "file": str(track["file"]),
                    "title": track["title"],
                    "track_no": track["track_no"],
                    "duration": track["duration"],
                    "chapters": [
                        {
                            "title": chapter["title"],
                            "files": [str(file) for file in chapter["files"]],
                        }
                        for chapter in track["chapters"]
                    ],
                    "temp_files": {k: str(v) for k, v in track["temp_files"].items()},
                }
                for track in self.tracks
            ],
        }

    def _run_ff(self, cmd: list[str]) -> None:
        cmd_type = cmd[0]
        self.lg.info(f"Running {cmd_type} command: {cmd}")
        temp_files_remove = False
        try:
            process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
            stdout, stderr = process.communicate()

            if stdout:
                self.lg.debug(f"{cmd_type} stdout: {stdout.strip()}")
            if stderr:
                self.lg.error(f"{cmd_type} stderr: {stderr.strip()}")
            if process.returncode != 0:
                raise sp.CalledProcessError(process.returncode, cmd, stderr)
            return stdout.strip()
        except sp.CalledProcessError as exc:
            temp_files_remove = True
            raise LoggedFileError(f"{cmd_type} command failed: {exc}", self.lg) from exc
        finally:
            if temp_files_remove:
                self.remove_temp_files()

    def remove_temp_files(self) -> None:
        self.lg.info("Removing temporary files.")
        for track in self.tracks:
            for temp_file in track["temp_files"].values():
                Path(temp_file).unlink(missing_ok=True)
                self.lg.debug(f"Temporary file removed: {temp_file}")

    def convert(self) -> None:
        self.lg.debug("Started converting files.")
        common_args = ["-loglevel", "info", "-hide_banner", "-y", "-stats"]
        codec_args = ["-c" if self._input_format == ".mp3" else "-c:v", "copy"]
        # if input files are mp3, we just copy all streams to the output file which is
        # faster. If input files are m4a, we need to re-encode the audio stream to aac.
        # Arg "-c:v" is used for video streams, used here because of the cover image.
        cover_args = []
        if self.cover:
            cover_args = [
                "-i", self.cover, "-metadata:s:v", "title=Cover",
                "-metadata:s:v", "comment=Cover (front)", "-map", "1"
            ]  # fmt: skip

        for track in self.tracks:
            self.lg.info(f"Processing {track['track_no']}: {track['title']}")
            track_file = track["file"]
            temp_file = track_file.with_stem(track_file.stem + "_t").with_suffix(".mp3")
            track["temp_files"]["temp"] = temp_file

            cmd1 = [  # Step 1: Concatenate input files into a single mp3 and add cover
                "ffmpeg", "-f", "concat", "-safe", "0", 
                "-i", track["temp_files"]["input_list"], *cover_args, "-map", "0:a",
                *codec_args, *common_args, track["temp_files"]["temp"],
            ]  # fmt: skip
            cmd2 = [  # Step 2: Convert mp3 to m4b and add metadata
                "ffmpeg", "-i", track["temp_files"]["temp"],
                "-i", track["temp_files"]["chapter_data"],
                "-map_metadata", "1", "-c", "copy", "-c:a", "aac", "-b:a",
                self.output_bitrate, *common_args, track["file"],
            ]  # fmt: skip
            self.lg.debug(f"Step 1: Concatenating input files: {temp_file}")
            self._run_ff(cmd1)
            self.lg.debug(f"Step 2: Converting to m4b: {track_file}")
            self._run_ff(cmd2)
            self.lg.info(f"Track {track['track_no']} converted successfully.")

        self.remove_temp_files()
        self.lg.info(f"All done! Get your new audiobook from: {self.output_path}")
