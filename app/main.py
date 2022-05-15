from distutils.command.build import build
import sys
import os
import zlib

def ReadZlib(filepath):
    with open(filepath, "rb") as compressed:
        data = compressed.read()
        d = zlib.decompressobj()
        return d.decompress(data)
    
def main():
    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/master\n")
        print("Initialized git directory")

    elif command == "cat-file":
        if sys.argv[2] == "-p" and len(sys.argv) > 2:
            filepath = f".git/objects/{sys.argv[3][:2]}/{sys.argv[3][2:]}"
            print("file: ", filepath, "\n")
            if not os.path.exists(filepath):
                print(f"Blob '{sys.argv[3]}' does not exist")
                RuntimeError(f"Blob '{sys.argv[3]}' does not exist")
            else:
                decompressed = ReadZlib(filepath)
                parts = decompressed.split(b"\x00")
                blob_type = parts[0].split(b" ")[0]
                if blob_type == b"tree":
                    data = [str(item)[2:-1] for item in decompressed.split(b"\x00")[1].split(b" ")]
                    next_blob = ''.join(format(x, '02x') for x in decompressed.split(b"\x00")[2])
                    print(f"{data[0]} blob {next_blob}\t{data[1]}")        
                elif blob_type == b"blob":
                    print(decompressed.split(b"\x00")[1].decode("utf-8"))

        else: 
            RuntimeError(f"Paramater flag '{sys.argv[2]}' doesnt exist for '{command}'")

    else:
        raise RuntimeError(f"Unknown command '{command}'")


if __name__ == "__main__":
    main()
