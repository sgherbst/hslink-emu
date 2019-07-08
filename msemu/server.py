SERVER_PORT = 57937

def get_client():
    import xmlrpc.client
    return xmlrpc.client.ServerProxy(f'http://localhost:{SERVER_PORT}')

def main():
    # modified from https://docs.python.org/3.7/library/xmlrpc.server.html?highlight=xmlrpc

    print('Launching Vivado TCL server...')

    import pexpect
    from xmlrpc.server import SimpleXMLRPCServer
    from xmlrpc.server import SimpleXMLRPCRequestHandler

    # Restrict to a particular path.
    class RequestHandler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)

    # Instantiate TCL evaluator
    child = pexpect.spawn('vivado -nolog -nojournal -notrace -mode tcl')
    child.expect('Vivado% ')

    # Create server
    with SimpleXMLRPCServer(('localhost', SERVER_PORT),
                            requestHandler=RequestHandler) as server:
        server.register_introspection_functions()

        def sendline(line):
            child.sendline(line)
            child.expect('Vivado% ')
            return child.before

        server.register_function(sendline)

        print(f'Server ready on port {SERVER_PORT}.')
        server.serve_forever()

if __name__ == '__main__':
    main()