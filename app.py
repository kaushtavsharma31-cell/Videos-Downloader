from flask import Flask, request, render_template, jsonify, send_file
import os
import tempfile
import threading
import requests
import json
import re
from datetime import datetime
import yt_dlp
import instaloader
from werkzeug.utils import secure_filename
import zipfile
import mimetypes
import socket


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this'

# Create downloads directory if it doesn't exist
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

class UniversalDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_quality_format(self, quality):
        """Map quality selector to yt-dlp format selection"""
        if quality == 'audio':
            return 'bestaudio/best'
        elif quality == '360p':
            return 'bestvideo[height<=360]+bestaudio/best[height<=360]'
        elif quality == '480p':
            return 'bestvideo[height<=480]+bestaudio/best[height<=480]'
        elif quality == '720p':
            return 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        else:
            return 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        
    def detect_platform(self, url):
        """Detect the platform from URL"""
        url = url.lower()
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url:
            return 'instagram'
        elif 'facebook.com' in url or 'fb.watch' in url:
            return 'facebook'
        elif 'twitter.com' in url or 'x.com' in url:
            return 'twitter'
        elif 'tiktok.com' in url:
            return 'tiktok'
        elif 'pinterest.com' in url:
            return 'pinterest'
        elif 'linkedin.com' in url:
            return 'linkedin'
        elif 'snapchat.com' in url:
            return 'snapchat'
        elif 'reddit.com' in url:
            return 'reddit'
        elif 'twitch.tv' in url:
            return 'twitch'
        else:
            return 'unknown'
    
    def create_safe_filename(self, filename, max_length=100):
        """Create a safe filename"""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip()
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename
    
    def download_youtube_content(self, url, path, quality='1080p'):
        """Download YouTube videos, shorts, playlists"""
        try:
            fmt = self.get_quality_format(quality)

            ydl_opts = {
                'outtmpl': os.path.join(path, '%(uploader)s - %(title)s.%(ext)s'),
                'format': fmt,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    return {'status': 'error', 'message': 'Could not extract YouTube video info (video may be private or unavailable)'}
                
                if 'entries' in info:  # Playlist
                    titles = [entry.get('title', 'Unknown') for entry in info['entries'] if entry]
                    return {
                        'status': 'success',
                        'message': f'Downloaded {len(titles)} videos from playlist',
                        'titles': titles[:5],  # Show first 5 titles
                        'type': 'playlist'
                    }
                else:  # Single video
                    return {
                        'status': 'success',
                        'message': 'YouTube content downloaded successfully!',
                        'title': info.get('title', 'Unknown'),
                        'uploader': info.get('uploader', 'Unknown'),
                        'type': 'video'
                    }
        except Exception as e:
            return {'status': 'error', 'message': f'YouTube error: {str(e)}'}
    
    def download_instagram_content(self, url, path):
        """Download Instagram posts, reels, stories, IGTV"""
        # Try yt-dlp first as it is often faster and works without login for videos
        try:
            ydl_opts = {
                'outtmpl': os.path.join(path, 'Instagram_%(uploader)s_%(title)s.%(ext)s'),
                'format': 'best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'status': 'success',
                    'message': 'Instagram video downloaded successfully!',
                    'title': info.get('title', 'Instagram Video'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'type': 'video'
                }
        except Exception as ydl_err:
            # Fallback to instaloader
            try:
                loader = instaloader.Instaloader(
                    dirname_pattern=path,
                    filename_pattern='{profile}_{mediaid}_{date_utc}',
                    download_videos=True,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=True,
                    compress_json=False
                )
                
                # Handle different Instagram URL types
                if '/stories/' in url:
                    # Story URL
                    username = self.extract_instagram_username(url)
                    if username:
                        profile = instaloader.Profile.from_username(loader.context, username)
                        for story in loader.get_stories([profile.userid]):
                            for item in story.get_items():
                                loader.download_storyitem(item, target=username)
                        return {
                            'status': 'success',
                            'message': f'Instagram stories downloaded for {username}',
                            'type': 'stories'
                        }
                elif '/reel/' in url or '/p/' in url or '/tv/' in url:
                    # Post, Reel, or IGTV
                    shortcode = self.extract_instagram_shortcode(url)
                    post = instaloader.Post.from_shortcode(loader.context, shortcode)
                    
                    loader.download_post(post, target=post.owner_username)
                    
                    content_type = 'reel' if post.is_video else 'post'
                    if post.typename == 'GraphSidecar':
                        content_type = 'carousel'
                    
                    return {
                        'status': 'success',
                        'message': f'Instagram {content_type} downloaded successfully!',
                        'username': post.owner_username,
                        'caption': post.caption[:100] + '...' if post.caption and len(post.caption) > 100 else post.caption,
                        'type': content_type
                    }
                else:
                    # Profile URL - download recent posts
                    username = self.extract_instagram_username(url)
                    profile = instaloader.Profile.from_username(loader.context, username)
                    
                    count = 0
                    for post in profile.get_posts():
                        if count >= 10:  # Limit to 10 recent posts
                            break
                        loader.download_post(post, target=username)
                        count += 1
                    
                    return {
                        'status': 'success',
                        'message': f'Downloaded {count} recent posts from {username}',
                        'type': 'profile'
                    }
                    
            except Exception as instaloader_err:
                return {'status': 'error', 'message': f'Instagram error: {str(ydl_err)} | {str(instaloader_err)}'}
    
    def download_tiktok_content(self, url, path, quality='1080p'):
        """Download TikTok videos"""
        try:
            fmt = self.get_quality_format(quality)

            ydl_opts = {
                'outtmpl': os.path.join(path, 'TikTok_%(uploader)s_%(title)s.%(ext)s'),
                'format': fmt,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {'status': 'error', 'message': 'TikTok video is unavailable or private'}
                return {
                    'status': 'success',
                    'message': 'TikTok video downloaded successfully!',
                    'title': info.get('title', 'TikTok Video'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'type': 'video'
                }
        except Exception as e:
            return {'status': 'error', 'message': f'TikTok error: {str(e)}'}
    
    def download_twitter_content(self, url, path, quality='1080p'):
        """Download Twitter/X videos, images, threads"""
        try:
            fmt = self.get_quality_format(quality)

            ydl_opts = {
                'outtmpl': os.path.join(path, 'Twitter_%(uploader)s_%(title)s.%(ext)s'),
                'format': fmt,
                'writesubtitles': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {'status': 'error', 'message': 'Twitter content is unavailable or private'}
                return {
                    'status': 'success',
                    'message': 'Twitter content downloaded successfully!',
                    'title': info.get('title', 'Twitter Content'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'type': 'tweet'
                }
        except Exception as e:
            return {'status': 'error', 'message': f'Twitter error: {str(e)}'}
    
    def download_facebook_content(self, url, path, quality='1080p'):
        """Download Facebook videos, posts"""
        try:
            fmt = self.get_quality_format(quality)

            ydl_opts = {
                'outtmpl': os.path.join(path, 'Facebook_%(title)s.%(ext)s'),
                'format': fmt,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {'status': 'error', 'message': 'Facebook content is unavailable or private'}
                return {
                    'status': 'success',
                    'message': 'Facebook content downloaded successfully!',
                    'title': info.get('title', 'Facebook Content'),
                    'type': 'video'
                }
        except Exception as e:
            return {'status': 'error', 'message': f'Facebook error: {str(e)}'}
    
    def download_reddit_content(self, url, path, quality='1080p'):
        """Download Reddit videos, images, gifs"""
        try:
            fmt = self.get_quality_format(quality)

            ydl_opts = {
                'outtmpl': os.path.join(path, 'Reddit_%(title)s.%(ext)s'),
                'format': fmt,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {'status': 'error', 'message': 'Reddit video is unavailable or private'}
                return {
                    'status': 'success',
                    'message': 'Reddit content downloaded successfully!',
                    'title': info.get('title', 'Reddit Post'),
                    'type': 'post'
                }
        except Exception as e:
            return {'status': 'error', 'message': f'Reddit error: {str(e)}'}
    
    def download_generic_content(self, url, path, quality='1080p'):
        """Download from any supported platform using yt-dlp"""
        try:
            fmt = self.get_quality_format(quality)

            ydl_opts = {
                'outtmpl': os.path.join(path, '%(extractor)s_%(title)s.%(ext)s'),
                'format': fmt,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {'status': 'error', 'message': 'Content is unavailable or private'}
                return {
                    'status': 'success',
                    'message': 'Content downloaded successfully!',
                    'title': info.get('title', 'Unknown'),
                    'extractor': info.get('extractor', 'Unknown'),
                    'type': 'media'
                }
        except Exception as e:
            return {'status': 'error', 'message': f'Download error: {str(e)}'}
    
    def extract_instagram_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        patterns = [
            r'/p/([^/?]+)',
            r'/reel/([^/?]+)',
            r'/tv/([^/?]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def extract_instagram_username(self, url):
        """Extract username from Instagram URL"""
        match = re.search(r'instagram\.com/([^/?]+)', url)
        if match:
            return match.group(1)
        return None
    
    def download_content(self, url, custom_path=None, quality='1080p'):
        """Main download function"""
        path = custom_path or DOWNLOAD_DIR
        platform = self.detect_platform(url)
        
        # Create timestamped folder for this download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_folder = os.path.join(path, f"{platform}_{timestamp}")
        os.makedirs(download_folder, exist_ok=True)
        
        try:
            if platform == 'youtube':
                result = self.download_youtube_content(url, download_folder, quality=quality)
            elif platform == 'instagram':
                result = self.download_instagram_content(url, download_folder)
            elif platform == 'tiktok':
                result = self.download_tiktok_content(url, download_folder, quality=quality)
            elif platform == 'twitter':
                result = self.download_twitter_content(url, download_folder, quality=quality)
            elif platform == 'facebook':
                result = self.download_facebook_content(url, download_folder, quality=quality)
            elif platform == 'reddit':
                result = self.download_reddit_content(url, download_folder, quality=quality)
            else:
                # Try generic download for other platforms
                result = self.download_generic_content(url, download_folder, quality=quality)
                
            # Scan for downloaded files
            if result.get('status') == 'success':
                downloaded_files = []
                for root, dirs, files in os.walk(download_folder):
                    for file in files:
                        if not file.endswith(('.json', '.txt', '.info.json', '.temp')):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, DOWNLOAD_DIR)
                            downloaded_files.append({
                                'name': file,
                                'path': rel_path.replace('\\', '/'),
                                'size': os.path.getsize(file_path)
                            })
                result['files'] = downloaded_files
                
                # Check if there are any downloaded images we can use as local thumbnail
                images = [f for f in downloaded_files if f['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                if images:
                    result['thumbnail_local'] = f"/download-file/{images[0]['path']}"
            return result
                
        except Exception as e:
            return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}

# Initialize downloader
downloader = UniversalDownloader()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/about-us')
def about_us():
    """About Us page"""
    return render_template('about_us.html')

@app.route('/contact-us')
def contact_us():
    """Contact Us page"""
    return render_template('contact_us.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy_policy.html')

@app.route('/terms-conditions')
def terms_conditions():
    """Terms & Conditions page"""
    return render_template('terms_conditions.html')

@app.route('/download', methods=['POST'])
def download():
    """Handle download requests"""
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        quality = data.get('quality', '1080p').strip()
        
        if not url:
            return jsonify({'status': 'error', 'message': 'URL is required'})
        
        # Detect platform automatically
        platform = downloader.detect_platform(url)
        
        # Start download
        result = downloader.download_content(url, quality=quality)
        result['platform'] = platform
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'})

@app.route('/bulk-download', methods=['POST'])
def bulk_download():
    """Handle bulk download requests"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'status': 'error', 'message': 'URLs list is required'})
        
        results = []
        for url in urls:
            if url.strip():
                result = downloader.download_content(url.strip())
                result['url'] = url
                results.append(result)
        
        return jsonify({
            'status': 'success',
            'message': f'Processed {len(results)} URLs',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Bulk download error: {str(e)}'})

@app.route('/downloads')
def list_downloads():
    """List downloaded files and folders"""
    try:
        items = []
        if os.path.exists(DOWNLOAD_DIR):
            for item in os.listdir(DOWNLOAD_DIR):
                item_path = os.path.join(DOWNLOAD_DIR, item)
                if os.path.isfile(item_path):
                    items.append({
                        'name': item,
                        'type': 'file',
                        'size': os.path.getsize(item_path),
                        'path': item
                    })
                elif os.path.isdir(item_path):
                    # Scan files inside this folder
                    media_files = []
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            if not file.endswith(('.json', '.txt', '.info.json', '.temp')):
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, DOWNLOAD_DIR)
                                media_files.append({
                                    'name': file,
                                    'path': rel_path.replace('\\', '/'),
                                    'size': os.path.getsize(file_path)
                                })
                    items.append({
                        'name': item,
                        'type': 'folder',
                        'files': media_files,
                        'file_count': len(media_files)
                    })
        
        # Sort items: newest first
        items.sort(key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x['name'])), reverse=True)
        
        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download-file/<path:filename>')
def download_file(filename):
    """Download a specific file"""
    try:
        # Prevent path traversal
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid file path'}), 400
            
        file_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, filename))
        if not file_path.startswith(os.path.abspath(DOWNLOAD_DIR)):
            return jsonify({'error': 'Access denied'}), 403
            
        if os.path.exists(file_path) and os.path.isfile(file_path):
            base_name = os.path.basename(file_path)
            # Guess the mimetype so that mobile galleries can index it correctly
            mimetype, _ = mimetypes.guess_type(file_path)
            if not mimetype:
                mimetype = 'application/octet-stream'
            # Send file with proper mimetype
            return send_file(file_path, as_attachment=True, download_name=base_name, mimetype=mimetype)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-folder/<foldername>')
def download_folder(foldername):
    """Download a folder as ZIP"""
    try:
        safe_foldername = secure_filename(foldername)
        folder_path = os.path.join(DOWNLOAD_DIR, safe_foldername)
        
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Create a temporary ZIP file
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_zip.close()
            
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
            
            return send_file(temp_zip.name, as_attachment=True, download_name=f'{safe_foldername}.zip')
        else:
            return jsonify({'error': 'Folder not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/supported-platforms')
def supported_platforms():
    """List supported platforms"""
    platforms = {
        'video_platforms': [
            'YouTube (videos, shorts, playlists)',
            'TikTok',
            'Twitter/X',
            'Facebook',
            'Instagram (Reels, IGTV)',
            'Reddit',
            'Twitch',
            'Vimeo',
            'Dailymotion'
        ],
        'social_platforms': [
            'Instagram (Posts, Stories, Reels, IGTV)',
            'Twitter/X (Tweets, Threads)',
            'Facebook (Posts, Videos)',
            'Reddit (Posts, Images, Videos)',
            'LinkedIn (Posts)',
            'Pinterest (Pins)'
        ],
        'features': [
            'Auto-platform detection',
            'Bulk downloads',
            'Stories download',
            'Playlist support',
            'High quality downloads',
            'Metadata preservation',
            'Subtitle downloads'
        ]
    }
    return jsonify(platforms)

@app.route('/clear-downloads', methods=['POST'])
def clear_downloads():
    """Clear all downloaded files"""
    try:
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
            os.makedirs(DOWNLOAD_DIR)
        return jsonify({'status': 'success', 'message': 'Downloads cleared successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error clearing downloads: {str(e)}'})

@app.route('/get-ip')
def get_ip():
    """Get local IP address of the server for mobile testing"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return jsonify({'ip': ip, 'port': 5000, 'url': f"http://{ip}:5000"})
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return jsonify({'ip': ip, 'port': 5000, 'url': f"http://{ip}:5000"})
        except Exception as e:
            return jsonify({'error': str(e)})

@app.route('/robots.txt')
def serve_robots():
    """Serve robots.txt from the public folder"""
    public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
    robots_path = os.path.join(public_dir, 'robots.txt')
    if os.path.exists(robots_path):
        return send_file(robots_path, mimetype='text/plain')
    return "User-agent: *\nAllow: /", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def serve_sitemap():
    """Serve sitemap.xml from the public folder"""
    public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
    sitemap_path = os.path.join(public_dir, 'sitemap.xml')
    if os.path.exists(sitemap_path):
        return send_file(sitemap_path, mimetype='application/xml')
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>", 404, {'Content-Type': 'application/xml'}

@app.route('/favicon.ico')
def serve_favicon_ico():
    """Serve favicon.ico from the public folder"""
    public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
    ico_path = os.path.join(public_dir, 'favicon.ico')
    if os.path.exists(ico_path):
        return send_file(ico_path, mimetype='image/x-icon')
    return "", 404

@app.route('/favicon.png')
def serve_favicon_png():
    """Serve favicon.png from the public folder"""
    public_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
    png_path = os.path.join(public_dir, 'favicon.png')
    if os.path.exists(png_path):
        return send_file(png_path, mimetype='image/png')
    return "", 404

if __name__ == '__main__':
    print("=" * 60)
    print("UNIVERSAL SOCIAL MEDIA DOWNLOADER")
    print("=" * 60)
    print("Starting server...")
    print("Supported platforms: YouTube, Instagram, TikTok, Twitter/X, Facebook, Reddit, and more!")
    print("Features: Stories, Reels, Posts, Videos, Bulk downloads")
    print("Server running on: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)