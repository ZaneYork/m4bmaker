from pathlib import Path
from typing import TypedDict


class ChapterData(TypedDict):
    title: str
    files: list[Path]


class TempFilesData(TypedDict):
    chapter_data: Path
    input_list: Path
    temp: Path


class TrackData(TypedDict):
    file: Path
    title: str
    track_no: str
    chapters: list[ChapterData]
    temp_files: TempFilesData
    duration: int
