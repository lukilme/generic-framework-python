import unittest
import logging
import logging.config
logging.basicConfig(level=logging.DEBUG)


logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': 'app.log',
        },
    },
    'formatters': {
        'detailed': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
})

def square(x):
    return x ** 2

class TestSquare(unittest.TestCase):
    def test_square_of_2(self):
        print()
        logging.debug('Esta é uma mensagem de debug')
        logging.info('Informação importante')
        logging.warning('Aviso: algo pode estar errado')
        logging.error('Erro ocorreu')
        logging.critical('Erro crítico')
        logging.debug('Esta é uma mensagem de debug')
        resultado = square(2)
        esperado = 4
        self.assertEqual(resultado, esperado)

    def test_square_of_3(self):
        resultado = square(3)
        esperado = 9
        self.assertEqual(resultado, esperado)

if __name__ == '__main__':
    unittest.main()
