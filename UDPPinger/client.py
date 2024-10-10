#send 10 pings to the server
#wait up to one second for a reply
    #if no reply, assume lost packet (set timeout value on a datagram socket)

#send the ping message using UDP
#collect and print the response message from the server, if any
#calculate and print the RTT in seconds of each packet if the server responds
#otherwise, log and print "Request timed out"

#client message should be one line like:
#Ping <sequence_number> <time>
#sequence number is 1, 2, 3, ..., 10
#time is the time (in floating-point seconds) when the client sends the message

#server message looks like:
#Reply <sequence_number> <client_time> <server_time> <md5_hash>

from socket import socket, AF_INET, SOCK_DGRAM
import time
import sys

def ping(host: str, port: int) -> list[tuple[int, str, float|int]]:
    resps = []
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    clientSocket.settimeout(1)
    for seq in range(1,11):
        try:
            c_time = time.time()
            message = f"Ping {seq} {c_time}"
            clientSocket.sendto(message.encode(), (host, port))
            print(message)

            server_reply = clientSocket.recvfrom(1024)[0].decode().strip()
            rtt = time.time() - c_time
            resps.append((seq, server_reply, rtt))
            print(f"{rtt=}")
        except TimeoutError:
            message = "Request timed out"
            resps.append((seq, message, 0))
            print(message)
        except KeyboardInterrupt:
            clientSocket.close()
            sys.exit()
        except Exception as e:
            print(e)

        print()

    clientSocket.close()
    return resps

if __name__ == '__main__':
    resps = ping('127.0.0.1', 12000)

