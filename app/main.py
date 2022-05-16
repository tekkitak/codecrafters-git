from ast import arg, parse
from dataclasses import dataclass
from hashlib import sha1
import sys
import os
import zlib
import argparse as ap
import time
from math import floor

def Parser():
    parser = ap.ArgumentParser(description="PyGit")
    parser.add_argument("-d", "--debug", action="store_true", help="Debug mode")

    subparsers = parser.add_subparsers(title="Command", required=1, metavar="command", dest="cmd")

    cat_file_parser = subparsers.add_parser("cat-file", help="Prints the contents of a blob object")
    cat_file_parser.add_argument("-p", dest="SHA", required=True,type=str, help="Object to print")

    commit_tree_parser = subparsers.add_parser("commit-tree", help="Creates a commit object")
    commit_tree_parser.add_argument("tree", metavar="commit-tree",  type=str, help="Tree SHA")
    commit_tree_parser.add_argument("-m", dest="msg", metavar="<MESSAGE>", required=True, type=str, help="Message")
    commit_tree_parser.add_argument("-p", metavar="<COMMIT_SHA>",type=str, help="Parent commit", dest="parents", nargs="*")

    debug_sha_parser = subparsers.add_parser("debug-sha", help="Prints data from SHA(s)")
    debug_sha_parser.add_argument("SHA", metavar="SHA", type=str, help="SHA to print", nargs="+")

    ls_tree_parser = subparsers.add_parser("ls-tree", help="Prints the contents of a tree object")
    ls_tree_parser.add_argument("--name-only", action='store_true', required=True, help="Only print the names of the objects")
    ls_tree_parser.add_argument("SHA", metavar="<TREE SHA>", type=str, help="Tree SHA")

    init_parser = subparsers.add_parser("init", help="Initializes a new git repository")

    hash_object_parser = subparsers.add_parser("hash-object", help="Hashes a file")
    hash_object_parser.add_argument("-w", action='store_true', help="Write the object into the object store")
    hash_object_parser.add_argument("file", metavar="<FILE>", type=open, help="File to hash")

    write_tree_parser = subparsers.add_parser("write-tree", help="Creates a tree object")

    return parser

def ReadZlib(filepath):
    with open(filepath, "rb") as compressed:
        data = compressed.read()
        d = zlib.decompressobj()
        return d.decompress(data)
    
def GetHash(data, hash_ret="hex"):
    if type(data) != str:
        data = data.decode("utf-8")
    header = f"blob {len(data.encode('utf-8'))}\0{data}"
    if hash_ret == "hex":
        return sha1(header.encode()).hexdigest()
    elif hash_ret == "bin":
        return sha1(header.encode()).digest()
    else:
        raise ValueError("Invalid hash_ret value")

def CreateTree(path):
    tdata = b""
    file_list = os.listdir(path)
    file_list.sort()
    for file in file_list:
        if file == ".git": 
            continue
        elif os.path.isdir(os.path.join(path, file)):
            tdata += b"40000 "
            tdata += os.path.basename(os.path.join(path, file)).encode()
            tdata += b"\0"
            tdata += CreateTree(os.path.join(path, file))
        elif os.path.isfile(os.path.join(path, file)):
            if file == "your_git.sh": tdata += b"100755 "
            else:
                tdata += b"100644 "
            tdata += os.path.basename(os.path.join(path, file)).encode()
            tdata += b"\0"
            tdata += GetHash(open(os.path.join(path, file), "r").read(), "bin")
        elif os.path.islink(os.path.join(path, file)):
            tdata += b"12000 "
            tdata += os.path.basename(os.path.join(path, file)).encode()
            tdata += b"\0"
            tdata += b"kok"
        else:
            print(f"Unknown file type: {file}")
            RuntimeError("Unknown file type")
    tdata = tdata.rstrip(b"\0")
    tdata = b'tree ' + str(len(tdata)).encode() + b'\0' + tdata

    hash = sha1(tdata).hexdigest()
    if not os.path.exists(".git/objects/" + hash[:2]):
        os.mkdir(".git/objects/" + hash[:2])
    with open(".git/objects/" + hash[:2] + "/" + hash[2:], "wb") as f:
        f.write(zlib.compress(tdata))
    return sha1(tdata).digest()

def main():
    parser = Parser()
    args = parser.parse_args()
    if args.debug: print(args)
    
    if args.cmd == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/master\n")
        print("Initialized git directory")

    elif args.cmd == "debug-sha":
        for sha in args.SHA:
            filepath = f".git/objects/{sha[:2]}/{sha[2:]}"
            if not os.path.exists(filepath):
                print(f"Object '{sha}' does not exist")
                RuntimeError(f"Object '{sha}' does not exist")
            else:
                print(f"Object '{sha}' exists")
                data = ReadZlib(filepath)
                print(f"Hash: {sha1(data).hexdigest()}\nData: {data}", "\n\n")

    elif args.cmd == "cat-file":
        filepath = f".git/objects/{args.SHA[:2]}/{args.SHA[2:]}"
        if not os.path.exists(filepath):
            print(f"Object '{args.SHA}' does not exist")
            RuntimeError(f"Object '{args.SHA}' does not exist")
        else:
            decompressed = ReadZlib(filepath)
            parts = decompressed.split(b"\x00")
            blob_type = parts[0].split(b" ")[0]
            if blob_type == b"tree":
                data = [str(item)[2:-1] for item in decompressed.split(b"\x00")[1].split(b" ")]
                next_blob = ''.join(format(x, '02x') for x in decompressed.split(b"\x00")[2])
                print(f"{data[0]} blob {next_blob}\t{data[1]}")        
            elif blob_type == b"blob":
                print(decompressed.split(b"\x00")[1].decode("utf-8"), end="")
            else:
                print(f"Unknown blob type '{blob_type.decode('utf-8')}'")
                RuntimeError(f"Unknown blob type '{blob_type.decode('utf-8')}'")

    elif args.cmd == "commit-tree":
        if not os.path.exists(f".git/objects/{args.tree[:2]}/{args.tree[2:]}"): 
            print(f"Object '{args.tree}' does not exist")
            RuntimeError(f"Object '{args.tree}' does not exist")
        tdata = b"tree " + args.tree.encode() + b"\n"
        if args.parents:
            for parent in args.parents:
                if not os.path.exists(f".git/refs/{parent}"):
                    print(f"Object '{parent}' does not exist")
                    RuntimeError(f"Object '{parent}' does not exist")
                tdata += f"parent {parent}\n".encode()
        tdata += b"author penis <penis@balls.kok> "+ str(floor(time.time())).encode() + b" +0200\n"
        tdata += b"committer penis <penis@balls.kok> "+ str(floor(time.time())).encode() + b" +0200\n\n"
        tdata = b"commit " + str(len(tdata)).encode() + b'\0' + tdata
        hash = sha1(tdata).hexdigest()
        if not os.path.exists(".git/objects/" + hash[:2]):
            os.mkdir(".git/objects/" + hash[:2])
        with open(".git/objects/" + hash[:2] + "/" + hash[2:], "wb") as f:
            f.write(zlib.compress(tdata))
        print(hash)


    elif args.cmd == "ls-tree":
        if sys.argv[2] == "--name-only" and len(sys.argv) > 2:
            filepath = f".git/objects/{args.SHA[:2]}/{args.SHA[2:]}"
            if not os.path.exists(filepath):
                print(f"Object '{args.SHA}' does not exist")
                RuntimeError(f"Object '{args.SHA}' does not exist")
            else:
                decompressed = ReadZlib(filepath)
                parts = decompressed.split(b"\x00")
                blob_type = parts[0].split(b" ")[0]
                if blob_type != b"tree":
                    print(f"Object '{args.SHA}' is not a tree")
                    RuntimeError(f"Object '{args.SHA}' is not a tree")

                data = decompressed.split(b"\x00", 1)[1]
                parsed = []
                while True:
                    try:
                        split = data.index(b"\0")
                    except ValueError:
                        break
                    tmp = data[:split].split(b" ")
                    tmp.append(''.join(format(x, '02x') for x in data[split:split+20]))
                    parsed.append(tmp)
                    data = data[split+21:]
                for row in parsed: print(row[1].decode(), end="\n")
        else:
            print(f"Paramater flag '{sys.argv[2]}' doesnt exist for '{args.cmd}'")
            RuntimeError(f"Paramater flag '{sys.argv[2]}' doesnt exist for '{args.cmd}'")

    elif args.cmd == "write-tree":
        print(''.join(format(x, '02x') for x in CreateTree(".")))            

    elif args.cmd == "hash-object":
        if sys.argv[2][0] == "-" and len(sys.argv) > 2:
            if sys.argv[2][1:] == "w":
                hash = GetHash(open(sys.argv[3], "rb").read())
                print(hash)
                if not os.path.exists(f".git/objects/{hash[:2]}"):
                    os.mkdir(f".git/objects/{hash[:2]}")
    
                with open(sys.argv[3], "r") as file:
                    data = file.read()
                    with open(f".git/objects/{hash[:2]}/{hash[2:]}", "wb") as new:
                        new.write(zlib.compress(f"blob {len(data.encode('utf-8'))}\0{data}".encode()))
            else:
                print(f"Paramaeter flag '{sys.argv[2]}' doesnt exist for 'hash-object'")
                RuntimeError(f"Paramater flag '{sys.argv[2]}' doesnt exist for 'hash-object'")
        else:
            print(GetHash(open(sys.argv[2], "r").read()))
    else:
        raise RuntimeError(f"Unknown command '{args.cmd}'")


if __name__ == "__main__":
    main()
