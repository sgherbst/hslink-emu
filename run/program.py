from msemu.server import get_client

def main():
    s = get_client()
    print(s.sendline('source program.tcl'), end='')

if __name__ == '__main__':
    main()