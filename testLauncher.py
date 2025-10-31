import os, subprocess

def main():
    # run an instance of server.py and client.py to test their interaction
    num_of_clients = 2

    if os.name == 'nt':  # for Windows
        os.system("start cmd /k python server.py")

        for i in range(num_of_clients):
            os.system("start cmd /k python client.py")
    else:  # for macOS and Linux
        subprocess.Popen(["python3", "server.py"])
        for i in range(num_of_clients):
            subprocess.run(["python3", "client.py"])


if __name__ == "__main__":
    main()