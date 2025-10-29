import os

def main():
    # run an instance of server.py and client.py to test their interaction
    os.system("start cmd /k python server.py")
    num_of_clients = 2

    for i in range(num_of_clients):
        os.system("start cmd /k python client.py")

if __name__ == "__main__":
    main()