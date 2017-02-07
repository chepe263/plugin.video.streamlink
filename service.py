import SocketServer
import re
import shutil
import threading

import requests
import xbmc

from SimpleHTTPServer import SimpleHTTPRequestHandler
from urlparse import urljoin
from addon import store_stream_item, plugin
from streamlink.stream import HLSStream


class ProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):

        match = re.match(r'^/([a-z0-9]+).*', self.path)

        if not match:
            self.send_error(404, "Stream not found")
        else:
            stream_cache_id = match.group(1)

            session = streamlink.Streamlink()
            stream = None
            stream_item = store_stream_item(stream_cache_id)
            if stream_item:
                url = stream_item.get('url')
                quality = stream_item.get('quality')

                streams = session.streams(url)
                stream = streams.get(quality)

            if not stream:
                self.send_error(404, "Stream not found")
            elif isinstance(stream, HLSStream):

                res = requests.get(stream.url)

                self.send_response(res.status_code, res.reason)
                self.send_header("content-type", res.headers.get('content-type', 'text'))
                self.end_headers()

                for line in res.text.splitlines(False):
                    if line and not line.startswith('#'):
                        self.wfile.write(urljoin(stream.url, line) + '\n')
                    else:
                        self.wfile.write(line + '\n')
            else:
                fh = None
                try:
                    fh = stream.open()
                    shutil.copyfileobj(fh, self.wfile)
                finally:
                    if fh:
                        fh.close()


if __name__ == "__main__":

    http_port = plugin.get_setting('listen_port', int)
    server = SocketServer.TCPServer(('', http_port), ProxyHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    monitor = xbmc.Monitor()

    # XBMC loop
    while not monitor.waitForAbort(10):
        pass

    server.shutdown()
    server_thread.join()
