import os
import json
from urllib.parse import urljoin
from flask import Flask, Response, request
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "SonyLIV & FanCode 720p Filtered Proxy Server is Running!"

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
    return handle_stream(target_url, headers, is_fancode=False)

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
    return handle_stream(target_url, headers, is_fancode=True)

def handle_stream(target_url, headers, is_fancode):
    try:
        base_endpoint = '/fancode?url=' if is_fancode else '/proxy?url='
        
        if '.m3u' in target_url or '.m3u8' in target_url:
            res = requests.get(target_url, headers=headers, timeout=15)
            content = res.text
            base_proxy_url = request.host_url.rstrip('/') + base_endpoint
            
            lines = content.splitlines()
            new_lines = []
            skip_next = False
            is_master = any('#EXT-X-STREAM-INF' in line for line in lines)
            
            for line in lines:
                line_str = line.strip()
                if is_master:
                    if line_str.startswith('#EXT-X-STREAM-INF:'):
                        # 720p বা 1280x720 ফিল্টার করার শর্ত
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

        elif '.json' in target_url:
            res = requests.get(target_url, headers=headers, timeout=15)
            try:
                data = res.json()
                base_proxy_url = request.host_url.rstrip('/') + base_endpoint
                
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
                response = Response(res.text, content_type='application/json', status=200)
                response.headers["Access-Control-Allow-Origin"] = "*"
                return response

        req = requests.get(target_url, headers=headers, stream=True, timeout=15)
        response = Response(
            req.iter_content(chunk_size=1024), 
            content_type=req.headers.get('content-type', 'video/mp2t'),
            status=req.status_code
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
