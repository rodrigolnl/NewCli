import time

from NewCli import Cli


def teste(bag):
    bag[1] = 'rodrigo'
    bag.print(bag[1])
    time.sleep(5)


def imprimir(bag, nome, sobrenome):
    bag.print(nome + ' ' + sobrenome)


def startup(bag, text):
    bag.print(text)


def startup2():
    print('testando')


cli = Cli()
cli.add_keybind('ctrl+p+o', target=teste)
cli.add_command('teste', target=teste, group='print')
cli.add_command('teste', target=teste, group='print')
# cli.add_command('imprimir', target=imprimir)
# cli.add_command('_', target=startup, args='teste', run_on_startup=True)
cli.add_command('_', target=startup2, run_on_startup=True)
cli.config(start_on_console=True)
cli.run()
