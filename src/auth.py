from .config import config

def tokenexist(): return True if config.get('secrets','ngrok-token') else False

def gettoken(): return config.get('secrets','ngrok-token')