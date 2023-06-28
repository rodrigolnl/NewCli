import time

from NewCli import Cli


def teste(bag):
    bag[1] = 'rodrigo'
    bag.print(bag[1])
    time.sleep(5)


def imprimir(bag, nome, sobrenome):
    bag.print(nome + ' ' + sobrenome)


def a(bag):
    bag.print('Would you like to continue? Y or N')
    response: str = bag.input()
    if response.lower() == 'y':
        bag.print('continuing...')
    if response.lower() == 'n':
        bag.print('canceled')


def startup2():
    print('iniciando')

def startup(bag):
    i = 0
    while True:
        bag.print(i)
        i += 1
        time.sleep(5)


print(a.__code__.ar)
cli = Cli()
cli.add_keybind('ctrl+p+o', target=teste)
cli.add_command('teste', target=teste, group='print')
# cli.add_command('imprimir', target=imprimir)
# cli.add_command('_', target=startup, args='teste', run_on_startup=True)
cli.add_command('_', target=startup2, run_on_startup=True)
cli.add_keybind('a', target=a)
cli.add_command('_', target=startup, run_on_startup=True)
cli.config(start_on_console=True)
cli.run()
