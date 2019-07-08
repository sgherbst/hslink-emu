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
    child = pexpect.spawnu('vivado -nolog -nojournal -notrace -mode tcl')
    child.expect('Vivado% ')

    # Create server
    with SimpleXMLRPCServer(('localhost', SERVER_PORT),
                            requestHandler=RequestHandler,
                            allow_none=True) as server:
        server.register_introspection_functions()

        def sendline(line):
            child.sendline(line)
            child.expect('Vivado% ')
            return child.before

        def set_vio(name, value):
            sendline(f'set_property OUTPUT_VALUE {value} ${name}')
            sendline(f'commit_hw_vio ${name}')

        def get_vio(name):
            before = sendline(f'get_property INPUT_VALUE ${name}')
            before = before.splitlines()[-1] # get last line
            before = before.strip() # strip off whitespace
            return before

        def pulse_reset():
            sendline('pulse_reset $rst')

        def refresh_hw_vio(name):
            sendline(f'refresh_hw_vio ${name}')

        server.register_function(sendline)
        server.register_function(set_vio)
        server.register_function(get_vio)
        server.register_function(pulse_reset)
        server.register_function(refresh_hw_vio)

        print(f'Server ready on port {SERVER_PORT}.')
        server.serve_forever()

if __name__ == '__main__':
    main()