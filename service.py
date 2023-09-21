import time
from NewCli import Cli


def service(bag: Cli.Bag):
    i = -1
    while True:
        if bag['status']:
            i += 1
            bag.print(i)
        time.sleep(1)


def pause_start(bag: Cli.Bag, status: bool):
    bag['status'] = status


cli = Cli()
cli.config(start_on_interactive=True)
cli.add_service(target=service)
cli.add_keybind('ctrl+s', target=pause_start, args=True)
cli.add_keybind('ctrl+p', target=pause_start, args=False)
cli.add_keybind('ctrl+q', target=cli.quit)
cli.run()
