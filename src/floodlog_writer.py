#!/usr/local/bin/python3

import redis
import pickle


def write_log_strings():
    rs = redis.Redis("localhost")
    while True:
        key_junk, spickle = rs.blpop("nfslogstrings", 0)
        log_string = pickle.loads(spickle)
        f = open("floodwebserver_log.txt", "a+")
        f.write(log_string + "\n")
        f.close()


if __name__ == "__main__":
    write_log_strings()
