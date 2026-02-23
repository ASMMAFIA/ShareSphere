import os
import re
import shutil
import urllib.parse
import argparse
import traceback
from jinja2 import Environment, FileSystemLoader
from http.server import HTTPServer, BaseHTTPRequestHandler, HTTPStatus
from pathlib import Path
from utils import *

OS = os.name
PROGRAM_NAME = 'ShareSphere'
WINDOWS = OS == 'nt'
UNIX_LIKE = OS == 'posix'
SOURCE_FILE_PATH = Path(__file__).resolve().parent
CURRENT_PATH = os.getcwd()
USERNAME = os.getlogin()
DEFAULT_FOLDER = f"/home/{USERNAME}/Downloads" if UNIX_LIKE else fr'C:\Users\{USERNAME}\Downloads'
READ_BUFFER = 4096 # bytes
TEMPLATES_FOLDER = 'templates'
STATIC_FOLDER = 'static'
DOWNLOAD_URL = 'download'
filename_re = re.compile(rb'filename="([^"]+)"')

class HTTPRequestHandler(BaseHTTPRequestHandler):
    share_path = DEFAULT_FOLDER

    def do_POST(self):
        if self.path.lower() != '/upload':
            do_GET()
            return
        content_length = int(self.headers['Content-Length'])
        boundary = self.headers['boundary']
        body = self.rfile.read(content_length)
        filename = filename_re.search(body)
        if filename is None:
          do_GET()
          return
        end_of_form_header = body.find(b'\r\n\r\n')
        file_obj = body[end_of_form_header+4:]
        
        with open(os.path.join(HTTPRequestHandler.share_path, filename.group(1).decode()), 'wb') as f:
          f.write(file_obj)

        self.do_GET()

    def do_GET(self):
        self.path = self.path[1:] if self.path.startswith('/') else self.path
        if self.path.startswith('static'):
            try:
                with open(self.path, 'rb') as f:
                    self.send_response(HTTPStatus.OK)
                    self.end_headers()
                    shutil.copyfileobj(f, self.wfile)
            except:
                self.send_error(HTTPStatus.NOT_FOUND)
            return
        elif self.path.startswith('download'):
          download_path = os.path.join(self.share_path, urllib.parse.unquote(self.path.split('download/')[1]))
          self.send_response(HTTPStatus.OK)
          self.send_header('Content-Disposition: attachment;', self.wfile)
          self.end_headers()
          with open(download_path, 'rb') as f:
              shutil.copyfileobj(f, self.wfile)
          return


        jinja_env = Environment(loader = FileSystemLoader(TEMPLATES_FOLDER), auto_reload=True)
        DOWNLOAD_URL_LEN = len(DOWNLOAD_URL)
        self.filename = self.path[DOWNLOAD_URL_LEN:] if self.path.startswith(DOWNLOAD_URL) else self.path
        match self.path.lower():
            case '':
                self.filename = 'index.html'
            case 'upload':
                self.filename = 'upload.html'
            case 'aboutus':
                self.filename = 'about.html'
            case 'source':
                self.filename = 'sourcecode.html'

        template = jinja_env.get_template(self.filename)
        template = template.render(files=fetch_files(self.share_path))
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(template.encode())
        return

        try:
            with open(self.filename, 'rb') as f:
                self.send_response(HTTPStatus.OK)
                self.end_headers()
                shutil.copyfileobj(f, self.wfile)
        except:
            print(self.filename)
            traceback.print_exc()
            self.send_error(HTTPStatus.NOT_FOUND)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME)
    parser.add_argument('-d', '--directory', action='store', default=DEFAULT_FOLDER)
    args = parser.parse_args()
    share_path = args.directory
    HTTPRequestHandler.share_path = share_path
    httpd = HTTPServer(('0.0.0.0', 8899), HTTPRequestHandler)
    httpd.serve_forever()