from pymemcache.client import base

from config import memcached_server

# memcache клиент
mc = base.Client(server=memcached_server)
