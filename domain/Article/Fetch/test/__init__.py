import logging
import http.client

http.client.HTTPConnection.debugLevel = 1

logging.basicConfig()
reqlog = logging.getLogger("requests.packages.urllib3")
reqlog.setLevel(logging.DEBUG)
reqlog.propagate = True
