import os
import json
from urllib.parse import urljoin
from flask import Flask, Response, request
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Optimized Live Stream Proxy Server is Running!"

# সোনিলাইভ প্রক্সি রুট
@app.route('/proxy')
def proxy_sonyliv():
    target_url = request.args.get('url')
    if not target_url:
        return "URL is required", 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.sonyliv.com/'
    }
    return proxy_handler(target_url, headers, '/proxy?url=')

# ফ্যানকোড প্রক্সি রুট
@app.route('/fancode')
def proxy_fancode():
    target_url = request.args.get('url')
    if not target_url:
        return "URL is required", 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.fancode.com/',
        'Origin': 'https://www.fancode.com'
    }
    return proxy_handler(target_url, headers, '/fancode?url=')

def proxy_handler(target_url, headers, base_route):
    try:
        # লিংকে পাইপ (|) বা অতিরিক্ত অংশ থাকলে তা রিমুভ করে শুধু মূল URL নেওয়া
        if '|' in target_url:
            target_url = target_url.split('|')[0]

        res = requests.get(target_url, headers=headers, stream=True, allow_redirects=True, timeout=15)
        content_type = res.headers.get('content-type', '')

        # ১. যদি ফাইলটি .m3u বা .m3u8 প্লেলিস্ট হয় (720p ফিল্টারসহ)
        if '.m3u' in target_url or '.m3u8' in target_url or 'mpegurl' in content_type:
            content = res.text
            base_proxy_url = request.host_url.rstrip('/') + base_route
            
            lines = content.splitlines()
            new_lines = []
            skip_next = False
            is_master = any('#EXT-X-STREAM-INF' in line for line in lines)
            
            for line in lines:
                line_str = line.strip()
                if is_master:
                    if line_str.startswith('#EXT-X-STREAM-INF:'):
                        if '1280x720' in line_str or '720p' in line_str or '720' in line_str:
                            skip_next = False
                            new_lines.append(line_str)
                        else:
                            skip_next = True
                        continue
                    elif skip_next:
                        skip_next = False
                        continue
                
                if line_str and not line_str.startswith('#'):
                    if not line_str.startswith('http'):
                        line_str = urljoin(target_url, line_str)
                    if 'proxy?url=' not in line_str and 'fancode?url=' not in line_str:
                        line_str = base_proxy_url + line_str
                new_lines.append(line_str)
            
            updated_playlist = '\n'.join(new_lines)
            response = Response(updated_playlist, content_type='application/vnd.apple.mpegurl', status=200)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response

        # ২. যদি ফাইলটি .json প্লেলিস্ট হয়
        elif '.json' in target_url or 'application/json' in content_type:
            try:
                data = res.json()
                base_proxy_url = request.host_url.rstrip('/') + base_route
                
                def update_json_urls(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k in ['url', 'link', 'stream', 'stream_url'] and isinstance(v, str) and v.startswith('http'):
                                if 'proxy?url=' not in v and 'fancode?url=' not in v:
                                    obj[k] = base_proxy_url + v
                            else:
                                update_json_urls(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            update_json_urls(item)
                    return obj

                updated_data = update_json_urls(data)
                response = Response(json.dumps(updated_data), content_type='application/json', status=200)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Access-Control-Allow-Origin"] = "*"
                return response
            except Exception:
                pass

        # ৩. ভিডিওর ছোট টুকরো (.ts, .m4s ইত্যাদি) স্মুথলি স্ট্রিম করার জন্য
        response = Response(
            res.iter_content(chunk_size=8192), 
            content_type=content_type or 'video/mp2t',
            status=res.status_code
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
