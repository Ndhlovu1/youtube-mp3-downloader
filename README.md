# 🎶 Django YouTube MP3 Downloader

A simple Django app that lets users paste a YouTube link and download the audio as an MP3, with progress tracking and a download button.

Built using:
- [Django](https://www.djangoproject.com/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [pipenv](https://pipenv.pypa.io/)

---

## 🚀 Features
- Paste a YouTube link and download as MP3
- Real-time progress updates (download % + ETA + speed)
- Cleaned/sanitized filenames
- Download file served directly via Django
- Temporary in-memory progress storage (use Redis or DB in production)
- No Viruses or harmful links and ADs
---

## 🛠️ Setup Instructions

### 1. Clone the repository
```bash
git https://github.com/Ndhlovu1/youtube-mp3-downloader.git
cd youtube-mp3-downloader-main
```

### 2. Install pipenv (if not installed)

```bash
pip install pipenv
```

### 3. Create and activate virtual environment

```bash
pipenv shell
```

### 4. Install dependencies

```bash
pipenv install django yt-dlp or
```

### 5. Run database migrations

```bash
pipenv run python manage.py migrate
```

### 6. Start the development server

```bash
pipenv run python manage.py runserver
```

### 7. Open in your browser and go to 

```cpp
http://127.0.0.1:8000/
```

**Paste a YouTube link, click Download, and watch the progress bar update until your MP3 is ready.**

## ⚡ Notes

1. This project currently stores progress in memory (download_progress dict). 

2. Large files are read into memory; in production, consider writing to disk and streaming.

## 🙌 Credits

**Author:** [Ndhlovu1](https://github.com/Ndhlovu1)



