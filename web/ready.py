"""ready.py

A script to check if a server is ready and listening on a given port.

Examples
--------
To check if PostgreSQL is ready at the address ``example.com'':

    $ python ready.py example.com 5432

"""

from socket import socket
import argparse
from time import sleep
import sys


def server_ready(address, port):
    """Checks to see if the server is running.

    Arguments
    ---------
    address : str
        The address or hostname to connect to.
    port : int
        The port number to use.

    Returns
    -------
    bool
        Whether the connection succeeded.

    """
    s = socket()
    try:
        s.connect((address, port))
    except Exception as err:
        print('Connection failed: {}'.format(err))
        return False
    else:
        return True


def main():
    parser = argparse.ArgumentParser(description='Checks to see if a server is accepting connections on a given port')
    parser.add_argument('--num_tries', '-n', help='Number of times to try connecting', type=int, default=10)
    parser.add_argument('address', help='Address to connect to')
    parser.add_argument('port', help='Port to connect to', type=int)
    args = parser.parse_args()

    for i in range(args.num_tries):
        if server_ready(args.address, args.port):
            return
        else:
            sleep(1)
    else:
        print('The server was not ready!')
        sys.exit(1)


if __name__ == '__main__':
    main()
