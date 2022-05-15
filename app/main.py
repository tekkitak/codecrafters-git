from dataclasses import dataclass
from hashlib import sha1
from string import hexdigits
import sys
import os
import zlib


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
    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/master\n")
        print("Initialized git directory")

    elif command == "debug-sha":
        if len(sys.argv) > 1:
            for sha in sys.argv[2:]:
                filepath = f".git/objects/{sha[:2]}/{sha[2:]}"
                if not os.path.exists(filepath):
                    print(f"Object '{sha}' does not exist")
                    RuntimeError(f"Object '{sha}' does not exist")
                else:
                    print(f"Object '{sha}' exists")
                    data = ReadZlib(filepath)
                    print(f"Hash: {sha1(data).hexdigest()}\nData: {data}", "\n\n")

    elif command == "cat-file":
        if sys.argv[2] == "-p" and len(sys.argv) > 2:
            filepath = f".git/objects/{sys.argv[3][:2]}/{sys.argv[3][2:]}"
            if not os.path.exists(filepath):
                print(f"Object '{sys.argv[3]}' does not exist")
                RuntimeError(f"Object '{sys.argv[3]}' does not exist")
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

        else: 
            RuntimeError(f"Paramater flag '{sys.argv[2]}' doesnt exist for '{command}'")
    
    elif command == "ls-tree":
        if sys.argv[2] == "--name-only" and len(sys.argv) > 2:
            filepath = f".git/objects/{sys.argv[3][:2]}/{sys.argv[3][2:]}"
            if not os.path.exists(filepath):
                print(f"Object '{sys.argv[3]}' does not exist")
                RuntimeError(f"Object '{sys.argv[3]}' does not exist")
            else:
                decompressed = ReadZlib(filepath)
                parts = decompressed.split(b"\x00")
                blob_type = parts[0].split(b" ")[0]
                if blob_type != b"tree":
                    print(f"Object '{sys.argv[3]}' is not a tree")
                    RuntimeError(f"Object '{sys.argv[3]}' is not a tree")

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
            print(f"Paramater flag '{sys.argv[2]}' doesnt exist for '{command}'")
            RuntimeError(f"Paramater flag '{sys.argv[2]}' doesnt exist for '{command}'")

    elif command == "write-tree":
        print(''.join(format(x, '02x') for x in CreateTree(".")))            

    elif command == "hash-object":
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
        raise RuntimeError(f"Unknown command '{command}'")


if __name__ == "__main__":
    main()
