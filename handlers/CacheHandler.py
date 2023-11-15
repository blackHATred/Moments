from pymemcache.client import base

try:
    from config import memcached_server
except ModuleNotFoundError:
    from config_example import memcached_server

# memcache клиент
mc = base.Client(server=memcached_server)
