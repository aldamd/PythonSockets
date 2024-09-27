from socket import *
import sys

def webServer(port=6789):
    serverSocket = socket(AF_INET, SOCK_STREAM)

    serverSocket.bind(("", port)) #anyone can connect
    serverSocket.listen() #listen to a request from the server

    while True:
        print("Ready to serve...")
        connectionSocket, addr = serverSocket.accept()
        try:
            message = connectionSocket.recv(1024)
            filename = message.split()[1]
            f = open(filename[1:])
            outputdata = f.read()

            #Send one HTTP header line into socket
            connectionSocket.send("HTTP/1.0 200 OK\r\n\r\n".encode())

            for i in range(len(outputdata)):
                connectionSocket.send(outputdata[i].encode())

            connectionSocket.close()
        except IOError:
            #Send response message for file not found
            connectionSocket.send("HTTP/1.0 404 Not Found\r\n\r\n".encode())

            #Close client socket
            connectionSocket.close()
        except KeyboardInterrupt:
            break

    serverSocket.close()
    sys.exit()

if __name__ == "__main__":
    webServer(6789)
