# M4BMaker

`M4BMaker` is a Python tool for creating `.m4b` audiobooks from audio tracks usinf [ffmpeg](https://www.ffmpeg.org/). It supports organizing tracks and chapters, adding metadata, and embedding cover images.

## Features

- 3 modes of file generation:
  - **json**: Uses a JSON config file to define the audiobook's structure. Allows for granular control tracks and chapters.
  - **single**: Combines all input files as chapters of a single audiobook track.
  - **chapter**: Treats each input file as a separate track.
- 2 different output bitrates: 64k (default) and 128k.
- metadata and cover images.
- `.mp3` and `.m4a` input formats.
- zero dependencies (except, of course, for `ffmpeg`)
- works on all platforms (tested only on Windows)

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/pmsoltani/m4bmaker.git
   cd m4bmaker
   ```

2. Install `ffmpeg` and make sure both `ffmpeg` and `ffprobe` are available in your system's PATH.

## Usage

### JSON Configuration

`M4BMaker` uses a JSON configuration file to define the audiobook's structure, metadata, and input files. Below is an example configuration:

```json
{
  "path": "~/path/to/your/audio/files",
  "title": "Audiobook Title",
  "author": "Author",
  "narrator": "Narrator",
  "genre": "Audiobook",
  "disc": "1",
  "total_discs": "1",
  "year": "2025",
  "cover": "cover.jpg",
  "tracks": [
    {
      "title": "Track 1",
      "file": "01 Track 1.m4b",
      "chapters": [
        {
          "title": "Chapter 1",
          "files": [
            "file1.mp3",
            "file2.mp3"
          ]
        },
        {
          "title": "Chapter 2",
          "files": [
            "file3.mp3"
          ]
        }
      ]
    }
  ]
}
```

This assumes that all the audio files and the `cover.jpg` file are located in the same folder. The final book will have one `.m4b` file named `01 Track 1.m4b`. The track title would be `Track 1`. It will have two chapters inside, where `Chapter 1` is the concatenation/conversion of two `file1.mp3` & `file2.mp3` files and `Chapter 2` is the converted `file3.mp3` file.

### Running the Tool

To create an audiobook, first create a config JSON file using the above template and then instantiate the `M4BMaker` class and call its `convert` method:

```python
from pathlib import Path

from m4bmaker.m4bmaker import M4BMaker

m4b = M4BMaker(
    json_path=Path.home() / "m4bmaker.json",
    mode="json",  # Options: "json", "single", "chapter"
    output_bitrate="64k"  # Options: "64k", "128k"
    log_path=Path.home() / "m4bmaker.log",  # See detailed logs here.
)
m4b.convert()
```

Note that the JSON file is necessary regardless of the operation `mode`, as `M4BMaker` will use it to locate the audio files and transfer metadata. The `tracks` part of the JSON file will only be used in the `json` mode (`single` and `chapter` modes) will ignore it.

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## Acknowledgments

- [FFmpeg](https://ffmpeg.org/) for audio processing.
- Python's standard library for handling file paths, JSON, and subprocesses.
