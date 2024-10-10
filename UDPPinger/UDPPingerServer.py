import random
from socket import socket, AF_INET, SOCK_DGRAM
import time
import hashlib
import sys

def serve(port: int) -> None:
    # Create a UDP socket
    # Notice the use of SOCK_DGRAM for UDP packets
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    # Assign IP address and port number to socket
    serverSocket.bind(('', port))
    while True:
        try:
            # Generate random number in the range of 0 to 10
            rand = random.randint(0, 10)

            # Receive the client packet along with the address it is coming from
            message, address = serverSocket.recvfrom(1024)
            s_time = time.time()

            # If rand is less is than 4, we consider the packet lost and do not respond
            if rand < 4:
                continue

            #splits received message into seq and c_time
            m = message.decode().split()
            seq = m[1]
            c_time = m[2]
            h = hashlib.md5('seq:{0},c_time:{1},s_time:{2},key:{3}'.format(seq, c_time, str(s_time), 'randomkey').encode()).hexdigest()
            print(m)
            resp = 'Reply {0} {1} {2} {3}\n'.format(seq, c_time, str(s_time), h)

            # Otherwise, the server responds
            serverSocket.sendto(resp.encode(), address)
        except KeyboardInterrupt:
            serverSocket.close()
            sys.exit()

if __name__ == '__main__':
    serve(12000)

