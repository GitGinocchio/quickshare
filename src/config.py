import configparser

config = configparser.ConfigParser(allow_no_value=True)

config.read('./src/config/config.cfg')