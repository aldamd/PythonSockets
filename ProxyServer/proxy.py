from socket import *
import sys
import os
import shutil
import select

cacheDir = os.path.join(os.path.dirname(__file__), 'cache')

# For WINDOWS: can't keyboard interrupt while the program is in a blocking call
# Workaround is to timeout a blocking call every timeLeft seconds so the program can
# respond to any SIGINT or SIGKILL signals
# Shouldn't be a problem on Mac or Linux
# Additional note for WINDOWS: select.select() only works on sockets, so waitable should be a socket
def wait_interruptible(waitable, timeLeft):
    while True:
        ready = select.select([waitable], [], [], timeLeft)
        if len(ready[0]) > 0:
            return

# interruptible versions of accept(), recv(), readline(), read()
def interruptible_accept(socket):
    wait_interruptible(socket, 5)
    return socket.accept()

def interruptible_recv(socket, nbytes):
    wait_interruptible(socket, 5)
    return socket.recv(nbytes)

def interruptible_readline(fileObj):
    wait_interruptible(fileObj, 5)
    return fileObj.readline()

def interruptible_read(fileObj, nbytes=-1):
    wait_interruptible(fileObj, 5)
    return fileObj.read(nbytes)

# Read an HTTP message from a socket file object and parse it
# sockf: Socket file object to read from
# Returns: (headline: str, [(header: str, header_value: str)])
def parse_http_headers(sockf):
    # Read the first line from the HTTP message
    # This will either be the Request Line (request) or the Status Line (response)
    headline = interruptible_readline(sockf).decode().strip()

    # Set up list for headers
    content_length = 0
    headers = []
    while True:
        # Read a line at a time
        header = interruptible_readline(sockf).decode()
        # If it's the empty line '\r\n', it's the end of the header section
        if len(header.rstrip('\r\n')) == 0:
            break

        # Partition header by colon
        headerPartitions = header.partition(':')

        # Skip if there's no colon
        if headerPartitions[1] == '':
            continue

        header_name = headerPartitions[0].strip()
        header_value = headerPartitions[2].strip()
        headers.append((header_name, header_value))

        if header_name.lower() == 'content-length':
            content_length = int(header_value)

    body = None
    if content_length > 0:
        body = sockf.read(content_length)

    return headline, headers, body

# Forward a server response to the client and save to cache
# sockf: Socket file object connected to server
# fileCachePath: Path to cache file
# clisockf: Socket file object connected to client
def forward_and_cache_response(sockf, fileCachePath, clisockf):
    cachef = None

    # Create the intermediate directories to the cache file
    if fileCachePath is not None:
        os.makedirs(os.path.dirname(fileCachePath), exist_ok=True)
        # Open/create cache file
        cachef = open(fileCachePath, 'w+b')

    try:
        # Read response from server
        statusLine, headers, body = parse_http_headers(sockf)
        # Filter out the Connection header from the server
        headers = [h for h in headers if h[0] != 'Connection']
        # Replace with our own Connection header
        # We will close all connections after sending the response.
        # This is an inefficient,  single-threaded proxy!
        headers.append(('Connection', 'close'))

        #Create list of writable objects (client socket and potentially cache)
        objs = [clisockf]
        if cachef:
            objs.append(cachef)

        #Write headers (and potentially body) to writable objects 
        for obj in objs:
            obj.write(statusLine.encode())
            obj.write(b"\r\n")
            for header, value in headers:
                obj.write(f"{header}: {value}\r\n".encode())
            obj.write(b"\r\n")
            if body:
                obj.write(body)
        
        #Forward and cache the response
        while True:
            chunk = sockf.read(1024)
            if not chunk:
                break
            clisockf.write(chunk)
            if cachef:
                cachef.write(chunk)
    except Exception as e:
        print(e)
    finally:
        if cachef is not None:
            cachef.close()

# Forward a client request to a server
# sockf: Socket file object connected to server
# requestUri: The request URI to request from the server
# hostn: The Host header value to include in the forwarded request
# origRequestLine: The Request Line from the original client request
# origHeaders: The HTTP headers from the original client request
def forward_request(sockf, requestUri, hostn, origRequestLine, origHeaders, body=None):
    # Filter out the original Host header and replace it with our own
    headers = [h for h in origHeaders if h[0] != 'Host']
    headers.append(('Host', hostn))
  
    # Send request to the server
    sockf.write(f"{origRequestLine.split()[0]} {requestUri} HTTP/1.1\r\n".encode())
    for header, value in headers:
        sockf.write(f"{header}: {value}\r\n".encode())
    sockf.write(b"\r\n")
    if body:
        sockf.write(body)
    sockf.flush()

def proxyServer(port):
    if os.path.isdir(cacheDir):
        shutil.rmtree(cacheDir)
    # Create a server socket, bind it to a port and start listening
    tcpSerSock = socket(AF_INET, SOCK_STREAM)
    tcpSerSock.bind(("0.0.0.0", port))
    tcpSerSock.listen()

    tcpCliSock = None
    try:
        while 1:
            # Start receiving data from the client
            print('Ready to serve...')
            tcpCliSock, addr = interruptible_accept(tcpSerSock)

            print('Received a connection from:', addr)
            cliSock_f = tcpCliSock.makefile('rwb', 0)

            # Read and parse request from client
            requestLine, requestHeaders, body = parse_http_headers(cliSock_f)
            print(requestLine)

            if len(requestLine) == 0:
                continue

            # Extract the request URI from the given message
            requestUri = requestLine.split()[1]

            # if a scheme is included, split off the scheme, otherwise split off a leading slash
            uri_parts = requestUri.partition('http://')
            if uri_parts[1] == '':
                filename = requestUri.partition('/')[2]
            else:
                filename = uri_parts[2]

            print(f'filename: {filename}')

            if len(filename) > 0:
                # Compute the path to the cache file from the request URI
                fileCachePath = os.path.join("cache", filename.strip("/"))
                if os.path.exists(fileCachePath):
                    cached = True
                else:
                    cached = False
                
                print(f'fileCachePath: {fileCachePath}')

                # Check whether the file exists in the cache
                if fileCachePath is not None and cached and requestLine.split()[0] == "GET":
                    # Read response from cache and transmit to client
                    with open(fileCachePath, "rb") as r:
                        contents = r.readlines()
                    for line in contents:
                        cliSock_f.write(line)
                    print('Read from cache')
                else:
                    # Create a socket on the ProxyServer
                    c = socket(AF_INET, SOCK_STREAM)
                    hostn = filename.partition('/')[0]
                    print(f'hostn: {hostn}')

                    try:
                        # Connect to the socket
                        port = 80
                        if ":" in hostn:
                            hostn, port = hostn.split(":")
                            port = int(port)
                        c.connect((hostn, port))
                        print(f"Connected to webserver {hostn}")

                        # Create a temporary file on this socket and ask port 80 for the file requested by the client
                        fileobj = c.makefile('rwb', 0)
                        print("Forwarding Request...")
                        forward_request(fileobj, f'/{filename.partition("/")[2]}', hostn, requestLine, requestHeaders, body)

                        # Read the response from the server, cache, and forward it to client
                        print("Forwarding Response...")
                        forward_and_cache_response(fileobj, fileCachePath, cliSock_f)
                    except Exception as e:
                        print(e)
                    finally:
                        c.close()
            tcpCliSock.close()
    except KeyboardInterrupt:
        pass

    # Close the server socket and client socket
    tcpSerSock.close()
    if tcpCliSock:
        tcpCliSock.close()
    sys.exit()

if __name__ == "__main__":
    proxyServer(8888)
