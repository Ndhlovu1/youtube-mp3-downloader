import os
import tempfile
import re
from django.http import FileResponse
from django.shortcuts import render
from urllib.parse import urlparse, parse_qs
from .forms import YouTubeDownloadForm
import yt_dlp

def clean_youtube_url(url):
    """Normalize YouTube links to standard format"""
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return f"https://www.youtube.com/watch?v={qs['v'][0]}"
    if parsed.hostname == "youtu.be":
        return f"https://www.youtube.com/watch?v={parsed.path.lstrip('/')}"
    return url

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '_', filename)
    return filename.strip()

def download_view(request):
    form = YouTubeDownloadForm(request.POST or None)
    
    if request.method == "POST" and form.is_valid():
        try:
            url = clean_youtube_url(form.cleaned_data["url"])
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # yt-dlp configuration for audio download
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'quiet': False,  # Set to False to see progress
                    'no_warnings': False,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
                
                print(f"Downloading from: {url}")
                print(f"Using temp directory: {temp_dir}")
                
                # Download the audio
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_title = info.get('title', 'youtube_audio')
                    print(f"Video title: {video_title}")
                
                # Find the downloaded MP3 file
                mp3_files = []
                for file in os.listdir(temp_dir):
                    if file.endswith('.mp3'):
                        mp3_files.append(file)
                        print(f"Found MP3 file: {file}")
                
                if not mp3_files:
                    error_msg = "No MP3 file was created. Check if FFmpeg is installed."
                    print(error_msg)
                    return render(request, "downloader/index.html", {
                        "form": form,
                        "error": error_msg
                    })
                
                mp3_file_path = os.path.join(temp_dir, mp3_files[0])
                print(f"MP3 file path: {mp3_file_path}")
                
                # Check if file exists and has content
                if not os.path.exists(mp3_file_path):
                    error_msg = "MP3 file was not created properly."
                    print(error_msg)
                    return render(request, "downloader/index.html", {
                        "form": form,
                        "error": error_msg
                    })
                
                file_size = os.path.getsize(mp3_file_path)
                print(f"File size: {file_size} bytes")
                
                if file_size == 0:
                    error_msg = "MP3 file is empty. Conversion may have failed."
                    print(error_msg)
                    return render(request, "downloader/index.html", {
                        "form": form,
                        "error": error_msg
                    })
                
                # Sanitize filename for download
                safe_filename = sanitize_filename(video_title)
                print(f"Safe filename: {safe_filename}")
                
                # Serve the file as download
                response = FileResponse(
                    open(mp3_file_path, 'rb'),
                    as_attachment=True,
                    filename=f"{safe_filename}.mp3",
                    content_type='audio/mpeg'
                )
                
                print("Sending file response...")
                return response
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            return render(request, "downloader/index.html", {
                "form": form,
                "error": error_msg
            })
    
    return render(request, "downloader/index.html", {"form": form})