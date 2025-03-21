import logging
import colorlog

class Logger:
    def __init__(self, name: str, level=logging.DEBUG):
        self.logger = colorlog.getLogger(name)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            handler = colorlog.StreamHandler()
            
            formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(levelname)s:%(name)s:%(message)s',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'bold_red',
                }
            )
            
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)