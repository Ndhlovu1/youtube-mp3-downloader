import os
import tempfile
import re
import json
import uuid
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from urllib.parse import urlparse, parse_qs
from .forms import YouTubeDownloadForm
import yt_dlp
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# In-memory storage for progress (use Redis in production)
download_progress = {}

def clean_youtube_url(url):
    """Normalize YouTube links to standard format"""
    parsed = urlparse(url)
    # Handle standard YouTube URLs
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return f"https://www.youtube.com/watch?v={qs['v'][0]}"
    # Handle youtu.be short URLs
    if parsed.hostname == "youtu.be":
        return f"https://www.youtube.com/watch?v={parsed.path.lstrip('/')}"
    # Return as-is if not recognized
    return url

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    filename = re.sub(r'[^\w\s-]', '', filename)  # Remove unwanted chars
    filename = re.sub(r'[-\s]+', '_', filename)   # Replace spaces/hyphens with underscores
    return filename.strip()

def download_view(request):
    # Instantiate the form, bind POST data if available
    form = YouTubeDownloadForm(request.POST or None)
    
    if request.method == "POST" and form.is_valid():
        try:
            url = clean_youtube_url(form.cleaned_data["url"])
            task_id = str(uuid.uuid4())  # Unique ID for this download
            
            # Store initial progress for this task
            download_progress[task_id] = {
                'status': 'starting',
                'progress': 0,
                'message': 'Initializing download...',
                'url': url
            }
            
            # Render page with progress bar and task ID
            return render(request, "downloader/index.html", {
                "form": form,
                "task_id": task_id,
                "show_progress": True
            })
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            # Render page with error message
            return render(request, "downloader/index.html", {
                "form": form,
                "error": error_msg
            })
    
    # Render initial page with form
    return render(request, "downloader/index.html", {"form": form})

@csrf_exempt
def start_download(request):
    # API endpoint to start the download process
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            url = data.get('url')
            task_id = data.get('task_id')
            
            if not url or not task_id:
                return JsonResponse({'error': 'Missing parameters'}, status=400)
            
            # Update progress to show download is starting
            download_progress[task_id] = {
                'status': 'downloading',
                'progress': 10,
                'message': 'Preparing download...'
            }
            
            # Create temporary directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                # yt-dlp configuration with progress hooks
                def progress_hook(d):
                    # Update progress during download
                    if d['status'] == 'downloading':
                        percent = d.get('_percent_str', '0%').replace('%', '')
                        try:
                            progress = float(percent)
                            download_progress[task_id] = {
                                'status': 'downloading',
                                'progress': progress,
                                'message': f'Downloading: {d.get("_percent_str", "0%")}',
                                'speed': d.get('_speed_str', ''),
                                'eta': d.get('_eta_str', '')
                            }
                        except:
                            pass
                    # Update progress when finished downloading
                    elif d['status'] == 'finished':
                        download_progress[task_id] = {
                            'status': 'converting',
                            'progress': 90,
                            'message': 'Converting to MP3...'
                        }
                
                # yt-dlp options for audio extraction
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'quiet': False,
                    'no_warnings': False,
                    'progress_hooks': [progress_hook],
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
                
                # Download the audio using yt-dlp
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_title = info.get('title', 'youtube_audio')
                
                # Find the downloaded MP3 file in temp directory
                mp3_files = [f for f in os.listdir(temp_dir) if f.endswith('.mp3')]
                
                if not mp3_files:
                    # Error if no MP3 file was created
                    download_progress[task_id] = {
                        'status': 'error',
                        'progress': 100,
                        'message': 'No MP3 file was created'
                    }
                    return JsonResponse({'status': 'error', 'message': 'No MP3 file created'})
                
                mp3_file_path = os.path.join(temp_dir, mp3_files[0])
                
                # Read file content into memory
                with open(mp3_file_path, 'rb') as f:
                    file_content = f.read()
                
                # Store file content and metadata in progress (for small files only)
                download_progress[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Download completed!',
                    'file_content': file_content.decode('latin-1'),  # Store as string
                    'filename': f"{sanitize_filename(video_title)}.mp3",
                    'file_size': len(file_content)
                }
                
                # Respond with completed status
                return JsonResponse({'status': 'completed'})
                
        except Exception as e:
            # Update progress with error message
            if task_id in download_progress:
                download_progress[task_id] = {
                    'status': 'error',
                    'progress': 100,
                    'message': f'Error: {str(e)}'
                }
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    # Invalid request method
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_progress(request, task_id):
    """API endpoint to get download progress"""
    # Get progress info for the given task
    progress = download_progress.get(task_id, {
        'status': 'unknown',
        'progress': 0,
        'message': 'Task not found'
    })
    
    # Don't send file content in progress updates
    response_data = {k: v for k, v in progress.items() if k != 'file_content'}
    return JsonResponse(response_data)

def download_file(request, task_id):
    """Serve the downloaded file"""
    # Get progress info for the given task
    progress = download_progress.get(task_id)
    
    # Check if file is ready to be downloaded
    if not progress or progress['status'] != 'completed':
        return JsonResponse({'error': 'File not ready or not found'}, status=404)
    
    # Convert stored string back to bytes
    file_content = progress['file_content'].encode('latin-1')
    filename = progress['filename']
    
    # Create HTTP response for file download
    response = HttpResponse(file_content, content_type='audio/mpeg')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Clean up progress storage for this task
    if task_id in download_progress:
        del download_progress[task_id]
    
    return response