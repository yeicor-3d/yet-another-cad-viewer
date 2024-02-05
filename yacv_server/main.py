from os import system

if __name__ == '__main__':
    # Just a reminder that a hot-reloading server can be started with the following command:
    # Need to disable auto-start to avoid conflicts with the hot-reloading server
    system('YACV_DISABLE_SERVER=true aiohttp-devtools runserver server.py --port 32323')
