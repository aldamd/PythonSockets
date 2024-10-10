from socket import socket, AF_INET, SOCK_STREAM
from sys import exit as sysexit

def webServer(port: int=6789) -> None:
    with socket(AF_INET, SOCK_STREAM) as serverSocket:

        serverSocket.bind(("", port)) #anyone can connect
        serverSocket.listen() #listen to a request from the server

        while True:
            print("Ready to serve...")
            connectionSocket, _ = serverSocket.accept()
            try:
                message = connectionSocket.recv(1024)
                filename = message.split()[1]
                with open(filename[1:]) as r:
                    outputdata = r.read()

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

    sysexit()

if __name__ == "__main__":
    webServer(6789)
