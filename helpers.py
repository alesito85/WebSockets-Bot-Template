import asyncio
import logging


formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
loop = asyncio.get_event_loop()


class Logger:
    logger = logging.getLogger('log')
    fh = logging.FileHandler('chainrift_ws_base_Bot.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.info('Creating an instance of Logger')

    @classmethod
    def info(cls, *args):
        cls.logger.info(' | '.join(map(str, args)))

    @classmethod
    def debug(cls, *args):
        cls.logger.debug(' | '.join(map(str, args)))

    @classmethod
    def exception(cls, *args):
        cls.logger.exception(' | '.join(map(str, args)))




